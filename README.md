> Entwickelt von **Sebastian Islamyar** — Frankfurt am Main.

# Transit AI

> **AI-gestützter ÖPNV-Navigator für Deutschland.**
> Du sagst was du willst — wir finden die beste Bahnverbindung und erklären sie.

[![Status](https://img.shields.io/badge/status-active-success)]()
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-000?logo=nextdotjs)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)]()
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)]()

---

## Was ist das?

**Transit AI** ist ein konversationeller ÖPNV-Navigator. Statt Felder auszufüllen,
schreibst du einfach was du willst — die KI versteht den Rest:

> *„Ich muss morgen um 9 in Frankfurt sein, von Köln aus."*

Das System parst deine Anfrage, fragt Echtzeit-Daten der Deutschen Bahn ab,
und liefert die beste Verbindung — inklusive natürlicher Erklärung warum
diese Route, welche Risiken (Umstiege, Pünktlichkeit), und Alternativen.

---

## Features

- **Natural-Language Routing** — frei formulierte Reisewünsche
- **Hybride LLM-Strategie** — Groq Cloud (Primary, schnell) + lokales Ollama (Fallback, privat)
- **Echtzeit-Daten** — Deutsche Bahn HAFAS via [`db-rest`](https://github.com/derhuerst/db-rest) + DB API Marketplace
- **Voice Input** *(optional)* — Whisper STT + Piper / Kokoro TTS
- **Hardened by Default** — Read-only Container, Capability-Drop, Rate-Limiting, scram-sha-256, CSRF + JWT Auth
- **Self-hostable** — komplett offline-fähig mit Ollama + lokalem db-rest

---

## Architektur

```
                        ┌─────────────┐
                        │   Reverse   │
                        │    Proxy    │  (Pangolin / Cloudflare / Caddy)
                        └──────┬──────┘
                               │ HTTPS
                               ▼
                        ┌─────────────┐
                        │    nginx    │  Hardening, CSP, Rate-Limit
                        └──┬───────┬──┘
                           │       │
              ┌────────────┘       └────────────┐
              ▼                                 ▼
       ┌─────────────┐                   ┌─────────────┐
       │  Frontend   │                   │   Backend   │
       │  Next.js 14 │                   │   FastAPI   │
       └─────────────┘                   └──────┬──────┘
                                                │
                  ┌─────────────────────────────┼─────────────────────────────┐
                  ▼                             ▼                             ▼
           ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
           │   db-rest   │              │    Redis    │              │  Postgres   │
           │   (HAFAS)   │              │ Cache+Stats │              │  Auth+Hist  │
           └─────────────┘              └─────────────┘              └─────────────┘

                              LLM-Calls (vom Backend):
                              1. Groq      — Primary  (~550ms)
                              2. Ollama    — Fallback (~5s, lokal)
```

---

## Tech Stack

| Layer        | Technologie                                          |
|--------------|------------------------------------------------------|
| Frontend     | Next.js 14 (App Router) · TypeScript · Tailwind CSS  |
| Backend      | FastAPI · Python 3.11 · Pydantic · Alembic · uvicorn |
| LLM Routing  | Groq (Primary) · Ollama (Fallback) — austauschbar    |
| Transit-API  | `db-rest` v6 (HAFAS) · DB API Marketplace            |
| Cache        | Redis 7                                              |
| Datenbank    | PostgreSQL 16 (scram-sha-256, hardened pg_hba)       |
| Reverse Proxy| nginx (CSP, Rate-Limits, Bot-Filter)                 |
| Voice        | Faster-Whisper STT · Piper / Kokoro TTS *(optional)* |
| Container    | Docker Compose (read-only, capability-dropped)       |

---

## Schnellstart

> **Voraussetzungen:** Docker Engine ≥ 24, Compose Plugin v2, ~8 GB RAM

```bash
# 1. Repo klonen
git clone https://github.com/<your-user>/transit-ai.git
cd transit-ai

# 2. .env erzeugen + Secrets generieren
cp .env.example .env
./scripts/rotate-secrets.sh

# 3. Groq API Key eintragen (kostenlos: https://console.groq.com)
$EDITOR .env   # GROQ_API_KEY=gsk_...

# 4. Stack starten
cd infrastructure
docker compose up -d --build

# 5. Frontend öffnen
open http://localhost
```

API-Docs: `http://localhost/api/docs`

---

## API

| Method | Endpoint                          | Beschreibung                      |
|--------|-----------------------------------|-----------------------------------|
| POST   | `/api/transit/route`              | Routensuche mit KI-Analyse        |
| GET    | `/api/transit/locations/search`   | Bahnhof-Autocomplete              |
| GET    | `/api/transit/departures`         | Echtzeit-Abfahrten                |
| POST   | `/api/ai/chat`                    | Konversation mit dem Assistenten  |
| GET    | `/api/ai/status`                  | LLM-Provider-Status               |
| POST   | `/api/voice/transcribe`           | Audio → Text *(optional)*         |
| POST   | `/api/voice/speak`                | Text → Audio *(optional)*         |
| GET    | `/health`                         | Healthcheck                       |

---

## Konfiguration

Alle Settings via `.env` (siehe [`.env.example`](.env.example)).
Kernvariablen:

- `LLM_MODE` — `hybrid_free` · `cloud_only` · `local_only`
- `GROQ_API_KEY` — Pflicht für Cloud-LLM
- `DB_API_KEY` / `DB_CLIENT_ID` — *optional*, schaltet zusätzliche DB-Marketplace-Endpoints frei
- `OLLAMA_MODEL` — z. B. `qwen2.5:7b`, `llama3.3:70b`

---

## Sicherheit

- **Container hardening** — `read_only`, `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, mem/cpu-Limits
- **Postgres** — `scram-sha-256`, restriktive `pg_hba.conf`, statement timeout
- **nginx** — Bot-User-Agent-Filter, URI-Exploit-Filter, Rate-Limit-Zonen pro Route
- **Auth** — JWT mit kurzer TTL + CSRF-Token, `cookie_secure` + `samesite=strict`, TOTP-2FA-fähig
- **Secrets** — `.env` chmod 600, Rotation via `scripts/rotate-secrets.sh`

Hinweise zum Public Deployment in [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Projekt-Struktur

```
transit-ai/
├── frontend/         # Next.js 14 (Standalone Build)
├── backend/          # FastAPI App
│   ├── app/
│   │   ├── routers/  # /transit, /ai, /voice, /auth, /stats
│   │   ├── services/ # Business Logic
│   │   ├── security/ # JWT, CSRF, TOTP
│   │   └── core/     # Config, Logging
│   └── migrations/   # Alembic
├── llm/              # Provider-Abstraktion (Groq, Ollama)
├── infrastructure/
│   ├── docker-compose.yml
│   ├── nginx/        # Reverse Proxy + Hardening
│   └── postgres/     # Init + pg_hba
└── scripts/          # rotate-secrets, backup, restore, setup
```

---

## Roadmap

- [ ] Multi-Modal: Bahn + ÖPNV + Bike-Sharing kombiniert
- [ ] Anbindung an Claude (Sonnet/Opus) als optionaler Premium-Provider
- [ ] Live-Disruption-Push (WebSockets) bei Verspätung der gespeicherten Verbindung
- [ ] Mehrsprachig: EN, FR, NL
- [ ] PWA / Offline-Modus

---
## Über den Entwickler

Ich bin **Sebastian Islamyar**, IT-Spezialist aus Frankfurt am Main mit Fokus auf Cybersecurity,
KI-Infrastruktur, Self-Hosted LLMs, Netzwerkadministration und automatisierte Webprojekte.

Transit AI ist ein Nebenprojekt — entstanden aus echtem Bedarf an einem datenschutzfreundlichen,
KI-gestützten Bahnauskunftssystem ohne Google-Abhängigkeit.

Weitere Projekte und Kontakt: [github.com/sudoshaco](https://github.com/sudoshaco)



## Lizenz

[MIT](LICENSE) — frei zur Nutzung, Modifikation und kommerziellen Verwendung.
Über Stars und Pull Requests freue ich mich.
