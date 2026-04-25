import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.auth.routes import router as auth_router
from app.core.config import settings
from app.routers import ai, health, stats, transit, admin, voice, community
from app.security.middleware import (
    BanCheckMiddleware, IpRateLimitMiddleware, SecurityHeadersMiddleware,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
        if settings.ENV == "production":
            raise RuntimeError(
                "JWT_SECRET muss in production gesetzt sein (mind. 32 Zeichen). "
                "In der .env ergänzen."
            )
        logger.warning("JWT_SECRET fehlt/kurz — generiere temporären Secret (NICHT für production!)")
        settings.JWT_SECRET = secrets.token_urlsafe(48)

    logger.info("Transit AI Backend starting up")
    logger.info(f"Environment: {settings.ENV}, Debug: {settings.DEBUG}")
    yield
    logger.info("Transit AI Backend shutting down")


app = FastAPI(
    title="Transit AI API",
    version="1.1.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(IpRateLimitMiddleware,
                   calls=settings.RATE_LIMIT_CALLS, period=settings.RATE_LIMIT_PERIOD)
app.add_middleware(BanCheckMiddleware)  # outermost — Banned IPs sehen nichts

app.include_router(health.router, prefix="/health")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(transit.router, prefix="/api/transit")
app.include_router(ai.router, prefix="/api/ai")
app.include_router(stats.router, prefix="/api/stats")
app.include_router(admin.router, prefix="/api/admin")
app.include_router(voice.router, prefix="/api/voice")
app.include_router(community.router, prefix="/api/community")
