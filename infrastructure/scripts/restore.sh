#!/bin/bash
# Restore von Postgres-Dump. Usage: restore.sh <db_YYYY...sql.gz>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo 'Usage: restore.sh <backupfile.sql.gz>' >&2
  exit 2
fi
DUMP="$1"
[ -r "$DUMP" ] || { echo "Backup nicht lesbar: $DUMP" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
PG_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2-)
PG_DB=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2-)
PG_PW=$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)

read -r -p "Dump $DUMP wird in DB '$PG_DB' eingespielt. Fortfahren? [yes/NO] " ans
[ "$ans" = yes ] || { echo 'Abgebrochen.'; exit 1; }

echo 'Restore laeuft...'
zcat "$DUMP" | docker compose -f "$PROJECT_DIR/infrastructure/docker-compose.yml" exec -T \
  -e PGPASSWORD="$PG_PW" postgres psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1

echo 'Restore OK.'
