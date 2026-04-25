#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/../transit-ai-data/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ENV_FILE="$PROJECT_DIR/infrastructure/.env"

mkdir -p "$BACKUP_DIR"

PG_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2-)
PG_DB=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2-)
PG_PW=$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
REDIS_PW=$(grep -E '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)

echo '=== Transit AI Backup ==='

# PostgreSQL dump (inkl. Globals nicht nötig, da nur eine DB)
echo 'Sichere PostgreSQL...'
docker compose -f "$PROJECT_DIR/infrastructure/docker-compose.yml" exec -T \
  -e PGPASSWORD="$PG_PW" postgres \
  pg_dump -U "$PG_USER" -d "$PG_DB" --clean --if-exists \
  | gzip -9 > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Redis snapshot (kopiere RDB raus)
echo 'Sichere Redis RDB...'
docker exec infrastructure-redis-1 redis-cli -a "$REDIS_PW" --no-auth-warning SAVE > /dev/null
docker cp infrastructure-redis-1:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb" 2>/dev/null || true
gzip -9 "$BACKUP_DIR/redis_$TIMESTAMP.rdb" 2>/dev/null || true

# Integritaet pruefen: Dump muss > 0 Bytes sein und 'PostgreSQL database dump' enthalten
SIZE=$(stat -c%s "$BACKUP_DIR/db_$TIMESTAMP.sql.gz")
if [ "$SIZE" -lt 500 ]; then
  echo "FEHLER: Dump zu klein ($SIZE Bytes)" >&2
  exit 1
fi
zcat "$BACKUP_DIR/db_$TIMESTAMP.sql.gz" | head -20 | grep -q 'PostgreSQL database dump' \
  || { echo 'FEHLER: Dump ohne pg_dump Header' >&2; exit 1; }

echo "Backup OK: $BACKUP_DIR/db_$TIMESTAMP.sql.gz ($SIZE Bytes)"

# Alte Backups (>30 Tage) aufraeumen
find "$BACKUP_DIR" -name 'db_*.sql.gz'    -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name 'redis_*.rdb.gz' -mtime +30 -delete 2>/dev/null || true
echo 'Fertig.'
