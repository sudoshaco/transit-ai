from pydantic_settings import BaseSettings
from typing import List
import json
import os


class Settings(BaseSettings):
    # App
    ENV: str = "production"
    DEBUG: bool = False
    API_URL: str = "http://localhost"

    # Postgres
    POSTGRES_DB: str = "transitai"
    POSTGRES_USER: str = "transitai_app"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # LLM
    LLM_MODE: str = "hybrid_free"
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    GROQ_API_KEY: str = ""

    # DB API Marketplace
    DB_API_KEY: str = ""
    DB_CLIENT_ID: str = ""
    DB_API_BASE: str = "https://apis.deutschebahn.com/db-api-marketplace/apis"
    DB_CERT_PATH: str = ""
    DB_KEY_PATH: str = ""

    # db-rest
    DBREST_BASE: str = "http://db-rest:3000"
    DBREST_PUBLIC: str = "https://v6.db.transport.rest"

    NOMINATIM_BASE: str = "https://nominatim.openstreetmap.org"

    # CORS
    ALLOWED_ORIGINS: str = "[\"http://localhost:3000\",\"http://localhost\"]"
    TRUSTED_HOSTS: str = "[\"localhost\",\"127.0.0.1\"]"

    # Rate Limiting
    RATE_LIMIT_CALLS: int = 30
    RATE_LIMIT_PERIOD: int = 60
    USER_DAILY_QUOTA_FREE: int = 50
    ANON_DAILY_QUOTA: int = 15

    # Auth
    JWT_SECRET: str = ""  # Pflicht in prod; wird in main.py validiert
    JWT_ALG: str = "HS256"
    JWT_ACCESS_TTL_SECONDS: int = 900           # 15 min
    JWT_REFRESH_TTL_SECONDS: int = 60 * 60 * 24 * 14  # 14 Tage
    COOKIE_DOMAIN: str = ""
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "strict"
    CSRF_SECRET: str = ""
    # Mail (Resend)
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "noreply@example.com"
    APP_BASE_URL: str = "http://localhost"

    # Redis-Passwort (separat, für direkten Client)
    REDIS_PASSWORD: str = ""


    # Abuse / Ban
    ABUSE_BAN_THRESHOLD: int = 3          # nach 3 schweren Verstößen → Ban
    ABUSE_BAN_SECONDS: int = 60 * 60 * 24 * 30  # 30 Tage
    ABUSE_WINDOW_SECONDS: int = 60 * 60 * 24    # 24h Beobachtungsfenster

    @property
    def allowed_origins_list(self) -> List[str]:
        try:
            return json.loads(self.ALLOWED_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000", "http://localhost"]

    @property
    def trusted_hosts_list(self) -> List[str]:
        try:
            return json.loads(self.TRUSTED_HOSTS)
        except (json.JSONDecodeError, TypeError):
            return ["localhost", "127.0.0.1"]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def db_mtls_available(self) -> bool:
        return bool(
            self.DB_CERT_PATH
            and self.DB_KEY_PATH
            and os.path.exists(self.DB_CERT_PATH)
            and os.path.exists(self.DB_KEY_PATH)
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
