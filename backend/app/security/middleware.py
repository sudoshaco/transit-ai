"""Middleware: Ban-Check + Security-Header + optional per-user rate limit."""
import time
from collections import defaultdict
from typing import Optional

import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.security.client_ip import client_ip
from app.security.abuse import is_ip_banned


class BanCheckMiddleware(BaseHTTPMiddleware):
    """Frühester Check: ist die IP gebannt?"""

    async def dispatch(self, request: Request, call_next):
        ip = client_ip(request)
        reason = await is_ip_banned(ip)
        if reason:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Zugriff gesperrt. Wenn du glaubst das ist ein Fehler, kontaktiere den Betreiber.",
                    "code": "ip_banned",
                },
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(self), microphone=(self), camera=(), payment=(), usb=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response


class IpRateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-basierter Sliding-Window Rate-Limit pro IP."""
    def __init__(self, app, calls: int, period: int):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._redis: Optional[aioredis.Redis] = None
        self._fallback: dict[str, list[float]] = defaultdict(list)

    async def _r(self) -> Optional[aioredis.Redis]:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL, encoding="utf-8", decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # skip static/health
        if request.url.path.startswith(("/health", "/static")):
            return await call_next(request)

        ip = client_ip(request)
        now = time.time()

        r = await self._r()
        allowed = True
        if r is not None:
            key = f"rl:ip:{ip}"
            try:
                pipe = r.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.period)
                pipe.zcard(key)
                pipe.zadd(key, {f"{now}:{id(request)}": now})
                pipe.expire(key, self.period)
                _, count, _, _ = await pipe.execute()
                allowed = count < self.calls
            except Exception:
                allowed = True
        else:
            bucket = self._fallback[ip]
            bucket[:] = [t for t in bucket if t > now - self.period]
            if len(bucket) >= self.calls:
                allowed = False
            else:
                bucket.append(now)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Zu viele Anfragen. Bitte warte einen Moment.", "code": "rate_limited"},
            )
        return await call_next(request)
