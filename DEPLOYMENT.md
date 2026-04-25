# Transit AI — Deployment Guide

Diese Anleitung beschreibt vollständig, wie das Projekt von Null auf einen frisch aufgesetzten Linux-Server deployt wird, inklusive aller Hardening-Schritte und der öffentlichen Bereitstellung via Reverse-Proxy / Tunnel (Pangolin, Cloudflare, Caddy …).

---

## 1. Architektur-Überblick

```
   Internet
       │
       ▼
  ┌──────────────┐
  │  Pangolin    │  (Public Tunnel, your-domain.example)
  │  + Newt      │
  └──────┬───────┘
         │  HTTPS, Termination im Pangolin-Container
         ▼
  ┌──────────────┐
  │  nginx       │  (127.0.0.1:80, Hardening + CSP)
  └──────┬───────┘
         │ proxy_pass /api → backend:8000
         │ proxy_pass /    → frontend:3000
         ▼
  ┌────────────────────────────────────────┐
  │  Docker Compose (transit-network)      │
  │                                        │
  │   frontend  ── Next.js 14 (standalone) │
  │   backend   ── FastAPI + uvicorn       │
  │   db-rest   ── derhuerst/db-rest:6     │
  │   redis     ── 7-alpine (cache+stats)  │
  │   postgres  ── 16-alpine               │
  └────────────────────────────────────────┘

   LLM-Calls vom Backend gehen via Router an:
     1. Groq (api.groq.com) — Primary, ~550ms
     2. Ollama (host.docker.internal:11434) — Fallback, ~5s
```

**Komponenten**

| Service  | Image / Build               | Zweck                             |
|----------|-----------------------------|-----------------------------------|
| frontend | `frontend/Dockerfile`       | Next.js 14 standalone build       |
| backend  | `backend/Dockerfile`        | FastAPI, parse_intent + analyze_routes |
| db-rest  | `derhuerst/db-rest:6`       | Open-Source DB v6 HAFAS Wrapper    |
| redis    | `redis:7-alpine`            | LLM-Cache, Visit-Counter, Rating  |
| postgres | `postgres:16-alpine`        | Persistenz (zukünftig)            |
| nginx    | `nginx:alpine`              | Reverse Proxy, Security-Header    |

---

## 2. Voraussetzungen

- Linux-Server (getestet auf Kali 2024.x, Debian 12)
- Min. 8 GB RAM (16 GB empfohlen, mehr falls Ollama lokal genutzt wird)
- Docker Engine ≥ 24 + Docker Compose Plugin v2
- Optional: NVIDIA GPU + Treiber für Ollama-Fallback (getestet auf GTX 1070 Ti)
- Optional: Pangolin + Newt für öffentliche Bereitstellung (oder Cloudflare Tunnel, Caddy etc.)
- Ein Groq API Key (kostenlos unter https://console.groq.com)
- Ein Deutsche Bahn API Marketplace Account (kostenlos unter https://developers.deutschebahn.com) für StaDa, FaSta, RIS::Stations, Timetables

---

## 3. Erstinstallation Schritt für Schritt

### 3.1 System-Pakete

```bash
sudo apt update
sudo apt install -y curl git ca-certificates
```

### 3.2 Docker installieren

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker
docker --version
docker compose version
```

### 3.3 Projekt klonen / kopieren

```bash
git clone https://github.com/<your-user>/transit-ai.git
cd transit-ai
```

### 3.4 `.env` anlegen

```bash
cd ~/transit-ai
cp .env.example .env
chmod 600 .env
nano .env
```

Pflichtfelder:

```dotenv
# App
ENV=production
DEBUG=false

# Postgres — sicheres Passwort generieren mit `openssl rand -base64 24`
POSTGRES_DB=transitai
POSTGRES_USER=transitai
POSTGRES_PASSWORD=<sicheres-passwort>

# Redis (interner Hostname im Docker-Netz)
REDIS_URL=redis://redis:6379

# LLM
LLM_MODE=hybrid_free
GROQ_API_KEY=gsk_<dein-key>
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b

# CORS + TrustedHost — für lokalen Test reicht localhost
ALLOWED_ORIGINS=["https://your-domain.example","http://localhost","http://localhost:3000"]
TRUSTED_HOSTS=["your-domain.example","www.your-domain.example","localhost","127.0.0.1"]

# Rate Limiting
RATE_LIMIT_CALLS=30
RATE_LIMIT_PERIOD=60

# DB API Marketplace (Header-Auth, kein mTLS für StaDa/FaSta/RIS)
DB_CLIENT_ID=<deine-client-id>
DB_API_KEY=<dein-api-key>

# Visit-Counter Salt — beliebige zufällige Bytes
STATS_SALT=<openssl rand -hex 16>
```

### 3.5 DB-API Zertifikate (nur falls Timetables mit mTLS genutzt wird)

In `secrets/` müssen Cert + Key liegen. Für die aktuell genutzten APIs (StaDa, FaSta, RIS::Stations, Timetables) reicht **Header-Auth ohne mTLS**. Falls doch mTLS benötigt wird:

```bash
mkdir -p secrets
chmod 700 secrets
cp ~/Downloads/transit-ai-cert.pem secrets/
cp ~/Downloads/transit-ai-key.pem  secrets/
chmod 600 secrets/*.pem
```

### 3.6 Container bauen und starten

```bash
cd ~/transit-ai/infrastructure
docker compose pull
docker compose build
docker compose up -d
docker compose ps
```

Erwartet: alle 6 Container `Up (healthy)` oder `Up`.

### 3.7 Healthcheck

```bash
curl -s http://127.0.0.1/health
curl -s -X POST http://127.0.0.1/api/transit/route \
     -H 'Content-Type: application/json' \
     -d '{"query":"Köln nach Berlin morgen 18:00"}' | head -c 500
```

Wenn die Antwort `routes: [...]` enthält, läuft alles.

---

## 4. Öffentliche Bereitstellung via Pangolin

`nginx` lauscht **nur auf `127.0.0.1:80`**, daher ist die App nicht direkt aus dem Netz erreichbar. Pangolin (oder ein vergleichbarer Tunnel) verbindet die Domain mit diesem lokalen Port.

### 4.1 Pangolin-Resource

In der Pangolin-Web-UI:

1. Resource erstellen: `transit-ai`
2. Domain: `your-domain.example`
3. Target: `http://host.docker.internal:80` (oder die LAN-IP des Hosts, je nach Pangolin-Setup)
4. SSL: Let's Encrypt aktiv
5. Headers:
   - `X-Forwarded-For` durchreichen
   - `X-Forwarded-Proto: https` setzen
   - `X-Real-IP` durchreichen

### 4.2 Backend-seitige Header

Das Backend startet bereits mit `--proxy-headers --forwarded-allow-ips=*`, der Rate-Limiter liest in dieser Reihenfolge:
1. `X-Forwarded-For`
2. `X-Real-IP`
3. `request.client.host`

So funktioniert das Rate-Limit hinter dem Tunnel korrekt.

### 4.3 DNS

```
A    your-domain.example       → <Pangolin-Public-IP>
A    www.your-domain.example   → <Pangolin-Public-IP>
```

---

## 5. Konfigurations-Detail

### 5.1 Container-Hardening (`infrastructure/docker-compose.yml`)

Alle Services laufen mit:

- `security_opt: [no-new-privileges:true]`
- `cap_drop: [ALL]` und nur die wirklich benötigten Capabilities aktiviert
- `read_only: true` (wo möglich), Schreibpfade als `tmpfs`
- `pids_limit: 200`, `mem_limit`, `cpus`
- Non-root User (Backend: `transitai` UID 1001, Frontend: `1001:1001`, Redis: `redis` UID 999)
- nginx hat nur `NET_BIND_SERVICE`
- Port-Binding: `127.0.0.1:80:80` (kein direkter Internet-Zugriff)

### 5.2 nginx Hardening (`infrastructure/nginx/nginx.conf`)

- `server_tokens off`, `client_max_body_size 64k`
- Strenge CSP inkl. `https://*.basemaps.cartocdn.com` für Karten-Tiles
- HSTS, COOP, CORP, X-Frame-Options DENY, Permissions-Policy
- Bot-Filter (nikto, sqlmap, …)
- Method-Whitelist: nur `GET / HEAD / POST / OPTIONS`
- Block für `.php`, `.git`, `wp-admin`

### 5.3 Backend-Performance

In `backend/app/services/llm_service.py`:

- `parse_intent` Cache: Redis, 24 h TTL, Key = `sha256(today | normalized_query)`
- `analyze_routes` Cache: Redis, 5 min TTL, Key inkl. Routen-Signatur
- LLM Router (`llm/providers/router.py`): Sticky Decision für 60 s, Groq als Primary

In `llm/providers/groq_provider.py` und `ollama_provider.py`:

- Persistenter `httpx.AsyncClient` (kein TLS-Handshake je Request)
- `is_configured()` statt aktivem `has_quota()`-Ping

In `llm/prompts/intent_parser.py`:

- Aktuelles Datum + Uhrzeit + Wochentag werden in den System-Prompt injiziert, damit „heute Abend / morgen / übermorgen" mit dem korrekten Jahr aufgelöst werden.

### 5.4 DSGVO-konforme Stats

`backend/app/routers/stats.py` zählt eindeutige Besuche über einen anonymen SHA-256 Fingerprint:

```
sha256( day | (client_ip /24) | user_agent | STATS_SALT )
```

Keine Cookies, keine personenbezogenen Daten, keine externe Analytics. Counter und Rating leben im Redis (`stats:visits:*`, `stats:rating:*`).

---

## 6. Wartung & Betrieb

### 6.1 Logs

```bash
cd ~/transit-ai/infrastructure
docker compose logs -f backend
docker compose logs -f nginx
docker compose logs --tail 100
```

### 6.2 Container neu starten

```bash
docker compose restart backend
docker compose up -d --force-recreate backend
```

### 6.3 Updates ziehen und neu bauen

```bash
cd ~/transit-ai
git pull   # falls Git verwendet wird
cd infrastructure
docker compose build backend frontend
docker compose up -d backend frontend
```

### 6.4 Cache leeren (z. B. nach Prompt-Änderung)

```bash
docker compose exec redis redis-cli --scan --pattern 'llm:*' | \
  xargs -r docker compose exec -T redis redis-cli del
```

### 6.5 Performance-Test

```bash
for q in "Köln nach Berlin heute 18:00" "Hamburg nach München übermorgen 10:00"; do
  curl -s -o /dev/null -w "%{time_total}s — $q\n" \
       -X POST https://your-domain.example/api/transit/route \
       -H 'Content-Type: application/json' \
       -d "{\"query\":\"$q\"}"
done
```

Erwartet: erster Aufruf je Query ~1.8 – 3.8 s, zweiter (gecached) ~0.2 – 0.5 s.

---

## 7. Backup & Restore

### 7.1 Manuelles Backup auf USB

```bash
TS=$(date +%Y-%m-%d_%H%M)
tar --exclude='*/node_modules' \
    --exclude='*/.next' \
    --exclude='*/__pycache__' \
    --exclude='*/.venv' \
    --exclude='*/dist' \
    -czf "/mnt/usb/transit-ai-backup-${TS}.tar.gz" \
    -C ~ transit-ai
ls -lh /mnt/usb/transit-ai-backup-*.tar.gz
```

### 7.2 Restore

```bash
sudo mkdir -p ~
sudo chown "$USER:$USER" ~
tar xzf /mnt/usb/transit-ai-backup-YYYY-MM-DD_HHMM.tar.gz -C ~/
cd ~/transit-ai/infrastructure
docker compose build
docker compose up -d
```

### 7.3 Was im Backup ist und was nicht

**Im Backup:** Gesamter Source-Tree inkl. `.env` und `secrets/` (sensibel — Stick sicher aufbewahren!).

**Nicht im Backup:**
- `node_modules`, `.next`, `__pycache__`, `.venv`
- Docker-Volumes (`postgres_data`, `redis_data`) — die werden bei Bedarf separat gesichert mit:

```bash
docker run --rm \
  -v infrastructure_postgres_data:/data \
  -v /mnt/usb:/backup \
  alpine tar czf /backup/postgres-$(date +%F).tar.gz -C /data .
```

---

## 8. Troubleshooting

| Symptom | Ursache | Fix |
|---|---|---|
| `502` von nginx | Backend down | `docker compose logs backend` |
| LLM antwortet mit Vorjahr | Intent-Prompt ohne Datum | `intent_parser.py` injiziert heute — neu builden |
| `db-rest 500` für `journeys` | Departure-Datum in der Vergangenheit | Intent-Cache leeren, siehe 6.4 |
| Map-Tiles laden nicht | CSP zu strikt | `img-src` in `nginx.conf` muss `https://*.basemaps.cartocdn.com https://*.cartocdn.com` enthalten |
| Slow first request (>10 s) | TLS-Handshake + Cold Containers | normal nach `force-recreate`, danach <2 s |
| Counter erhöht sich nicht | Redis Schreibrechte | `docker compose logs redis`, prüfe `--save ""` Flag |
| Groq HTTP 401 | Abgelaufener Key | Neuen Key in `.env`, `docker compose up -d --force-recreate backend` |

---

## 9. Externe Abhängigkeiten

| Service | URL | Zweck | Kosten |
|---|---|---|---|
| Groq | https://api.groq.com | LLM Primary | Free Tier (14.400 req/Tag) |
| db-rest | https://github.com/derhuerst/db-rest | HAFAS-Wrapper, läuft self-hosted im Compose | — |
| DB API Marketplace | https://developers.deutschebahn.com | StaDa, FaSta, RIS::Stations, Timetables | Free Tier |
| Pangolin | https://github.com/fosrl/pangolin | Public Tunnel | Self-hosted |
| CARTO Basemaps | https://carto.com/basemaps | Map-Tiles | Free für Attribution |

---

## 10. Rechtliches

- Impressum: `frontend/app/impressum/page.tsx`
- Datenschutz: `frontend/app/datenschutz/page.tsx`
- Trademark-Hinweis: Die Marke „Deutsche Bahn" wird nur zur **deskriptiven Quellenangabe** im Rahmen von §23 MarkenG genannt. Werbeflächen und Slogans verzichten auf den Markennamen.
- Daten werden **nicht persistent gespeichert** — Redis hat `--save ""`, keine Cookies, kein Tracking.
