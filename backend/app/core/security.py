import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per IP address."""

    def __init__(self, app, calls: int = 30, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Honor X-Forwarded-For from trusted reverse proxy (nginx → backend on internal docker net only)
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        client_ip = self._client_ip(request)

        now = time.time()
        window_start = now - self.period

        # Clean old entries
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.calls:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Zu viele Anfragen. Bitte warte einen Moment."},
            )

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
