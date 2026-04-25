#!/bin/bash
set -euo pipefail

echo "=== Ollama Modelle laden ==="

# Warte bis Ollama bereit ist
until docker exec transit-ai-ollama-1 ollama list > /dev/null 2>&1; do
    echo "Warte auf Ollama..."
    sleep 3
done

# Qwen2.5 7B laden (~4.7GB)
echo "Lade qwen2.5:7b (~4.7GB)..."
docker exec transit-ai-ollama-1 ollama pull qwen2.5:7b

echo "Modell geladen und bereit."
docker exec transit-ai-ollama-1 ollama list
