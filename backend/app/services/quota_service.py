"""Per-User / per-IP Daily Quota via Redis."""
import time
from dataclasses import dataclass
from typing import Optional
import uuid

import redis.asyncio as aioredis
from app.core.config import settings

_r: Optional[aioredis.Redis] = None


async def _redis() -> aioredis.Redis:
    global _r
    if _r is None:
        _r = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True,
            socket_connect_timeout=5,
        )
    return _r


@dataclass
class QuotaResult:
    allowed: bool
    remaining: int
    reset_seconds: int
    message: str = ""


def _day_key() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


async def check_and_consume(user_id: Optional[uuid.UUID], ip: str) -> QuotaResult:
    r = await _redis()
    day = _day_key()
    if user_id:
        key = f"q:user:{user_id}:{day}"
        limit = settings.USER_DAILY_QUOTA_FREE
    else:
        key = f"q:anon:{ip}:{day}"
        limit = settings.ANON_DAILY_QUOTA

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60 * 60 * 26)  # Tag + 2h Puffer
    count, _ = await pipe.execute()
    count = int(count)

    if count > limit:
        # reset ca. bis UTC-Mitternacht
        now = time.gmtime()
        secs_to_midnight = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
        msg = (
            "Tägliches Limit erreicht. Bitte später erneut versuchen."
            if user_id else
            "Tägliches Limit für nicht angemeldete Nutzer erreicht. Registriere dich für mehr."
        )
        return QuotaResult(allowed=False, remaining=0, reset_seconds=secs_to_midnight, message=msg)

    return QuotaResult(allowed=True, remaining=max(0, limit - count), reset_seconds=0)
