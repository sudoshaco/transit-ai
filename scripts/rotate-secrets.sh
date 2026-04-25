#!/usr/bin/env bash
# Generiert starke Secrets und aktualisiert .env idempotent.
# Verwendung: ./scripts/rotate-secrets.sh [/pfad/zur/.env]
set -euo pipefail

ENV_FILE="${1:-$(dirname "$0")/../.env}"
[ -f "$ENV_FILE" ] || { echo "Kein .env unter $ENV_FILE"; exit 1; }

gen() { LC_ALL=C tr -dc 'A-Za-z0-9!@#%^*_+-' </dev/urandom | head -c "${1:-48}"; echo; }

set_kv() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    # Nur ersetzen, wenn leer oder == changeme / placeholder / < 32 Zeichen
    current=$(grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2-)
    if [ -z "$current" ] || [ "$current" = "changeme" ] || [ ${#current} -lt 32 ] || [ "${3:-}" = "force" ]; then
      sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
      echo "• rotated ${key}"
    else
      echo "  kept ${key} (already strong)"
    fi
  else
    echo "${key}=${val}" >> "$ENV_FILE"
    echo "+ added ${key}"
  fi
}

set_kv POSTGRES_PASSWORD  "$(gen 48)"
set_kv REDIS_PASSWORD     "$(gen 48)"
set_kv JWT_SECRET         "$(gen 64)"
set_kv CSRF_SECRET        "$(gen 48)"

# REDIS_URL mit Passwort synchronisieren (falls Variante redis://:pw@host)
if grep -q '^REDIS_PASSWORD=' "$ENV_FILE"; then
  rp=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
  if grep -q '^REDIS_URL=' "$ENV_FILE"; then
    sed -i "s|^REDIS_URL=.*|REDIS_URL=redis://:${rp}@redis:6379|" "$ENV_FILE"
    echo "• synced REDIS_URL"
  fi
fi

# sensible Defaults für Auth
grep -q '^POSTGRES_USER='  "$ENV_FILE" || echo "POSTGRES_USER=transitai_app"  >> "$ENV_FILE"
grep -q '^POSTGRES_DB='    "$ENV_FILE" || echo "POSTGRES_DB=transitai"         >> "$ENV_FILE"
grep -q '^COOKIE_SECURE='  "$ENV_FILE" || echo "COOKIE_SECURE=true"            >> "$ENV_FILE"
grep -q '^COOKIE_SAMESITE=' "$ENV_FILE" || echo "COOKIE_SAMESITE=strict"       >> "$ENV_FILE"
grep -q '^JWT_ALG='         "$ENV_FILE" || echo "JWT_ALG=HS256"                >> "$ENV_FILE"

chmod 600 "$ENV_FILE"
echo "✓ .env gehärtet (chmod 600)"
