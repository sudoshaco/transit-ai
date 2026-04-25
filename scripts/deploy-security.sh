#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$ROOT"
COMPOSE=(docker compose)

echo "=== 1/6 Rotating secrets (generiert NEUE falls schwach) ==="
OLD_POSTGRES_PW=""
if grep -q '^POSTGRES_PASSWORD=' "$ROOT/.env"; then
  OLD_POSTGRES_PW=$(grep '^POSTGRES_PASSWORD=' "$ROOT/.env" | cut -d= -f2-)
fi
bash scripts/rotate-secrets.sh "$ROOT/.env"
NEW_POSTGRES_PW=$(grep '^POSTGRES_PASSWORD=' "$ROOT/.env" | cut -d= -f2-)
POSTGRES_USER_NOW=$(grep '^POSTGRES_USER=' "$ROOT/.env" | cut -d= -f2-)
POSTGRES_DB_NOW=$(grep '^POSTGRES_DB=' "$ROOT/.env" | cut -d= -f2-)
REDIS_PW=$(grep '^REDIS_PASSWORD=' "$ROOT/.env" | cut -d= -f2- || true)

cd infrastructure

echo "=== 2/6 Build backend image ==="
"${COMPOSE[@]}" build backend

echo "=== 3/6 Postgres start (keine Datenverlust) ==="
"${COMPOSE[@]}" up -d postgres
# Warte bis postgres healthy
for i in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T postgres pg_isready -U "$POSTGRES_USER_NOW" -d "$POSTGRES_DB_NOW" >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "=== 4/6 Sync Passwort in DB (ALTER USER) + SCRAM re-hash ==="
# Wenn das Passwort rotiert wurde, in der laufenden DB nachziehen.
if [ -n "$OLD_POSTGRES_PW" ] && [ "$OLD_POSTGRES_PW" != "$NEW_POSTGRES_PW" ]; then
  # Authentifiziere mit ALTEM Passwort, setze neues
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$OLD_POSTGRES_PW" postgres \
    psql -U "$POSTGRES_USER_NOW" -d "$POSTGRES_DB_NOW" \
    -c "SET password_encryption='scram-sha-256';" \
    -c "ALTER USER \"$POSTGRES_USER_NOW\" WITH PASSWORD '$NEW_POSTGRES_PW';" \
    || echo "WARN: altes Passwort stimmte nicht — falls frische DB, ok."
fi
# pg_hba.conf reload (file wurde über volume gemountet, braucht reload)
"${COMPOSE[@]}" exec -T -e PGPASSWORD="$NEW_POSTGRES_PW" postgres \
  psql -U "$POSTGRES_USER_NOW" -d "$POSTGRES_DB_NOW" -c "SELECT pg_reload_conf();" >/dev/null || true

echo "=== 5/6 Start redis + db-rest ==="
"${COMPOSE[@]}" up -d redis db-rest

echo "=== 6/6 Start backend (führt alembic upgrade head aus) ==="
"${COMPOSE[@]}" up -d --force-recreate backend
sleep 3
"${COMPOSE[@]}" up -d --force-recreate frontend nginx

echo
"${COMPOSE[@]}" ps
echo
echo "✓ Deploy fertig. Logs:  docker compose -f infrastructure/docker-compose.yml logs -f backend"
