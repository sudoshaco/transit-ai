#!/bin/bash
set -euo pipefail

echo "=== Transit AI Setup ==="

# Voraussetzungen prüfen
command -v docker >/dev/null || { echo "ERROR: Docker nicht installiert"; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null || { echo "ERROR: Docker Compose nicht installiert"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# Ollama data dir
mkdir -p "$PROJECT_DIR/../transit-ai-data/ollama"

# .env erstellen wenn nicht vorhanden
if [ ! -f .env ]; then
    cp .env.example .env
    echo "WARNUNG: .env erstellt — bitte Passwort anpassen!"
fi

echo "Starte Infrastruktur (Redis, Postgres, Nginx)..."
cd infrastructure
docker compose up -d redis postgres

echo "Warte auf Datenbank..."
sleep 5

echo "Baue und starte Backend..."
docker compose up -d --build backend

echo "Baue und starte Frontend..."
docker compose up -d --build frontend

echo "Starte Nginx..."
docker compose up -d nginx

echo ""
echo "=== Setup abgeschlossen ==="
echo "Frontend: http://localhost"
echo "API Docs: http://localhost/api/docs (nur im Debug-Modus)"
echo ""
echo "HINWEIS: Ollama muss separat gestartet werden:"
echo "  docker compose up -d ollama"
echo "  Dann: ./pull-models.sh"
