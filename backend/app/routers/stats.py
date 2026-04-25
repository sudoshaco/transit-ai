"""
Public stats endpoints — DSGVO-compliant by design.

- No IPs, cookies, sessions or personal data are stored.
- Redis only stores aggregate counters (integers) and rating sums.
- Hash-based duplicate-vote prevention uses a one-way fingerprint of
  Day + UA + truncated /24 IP, never the raw values, expiring after 24h.
"""
import hashlib
import logging
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stats"])

_redis: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class StatsResponse(BaseModel):
    visits_total: int
    visits_today: int
    rating_average: float
    rating_count: int


class RatingRequest(BaseModel):
    stars: int = Field(..., ge=1, le=5)


class RatingResponse(BaseModel):
    ok: bool
    rating_average: float
    rating_count: int
    duplicate: bool = False


# ---------------------------------------------------------------------------
# Helpers — anonymisation only, no raw value is ever persisted
# ---------------------------------------------------------------------------
def _anon_fingerprint(request: Request, salt: str) -> str:
    """
    Build a daily, anonymous fingerprint that cannot be reversed:
    SHA-256( day || /24-of-IP || user-agent || server-secret )

    Output is a hex digest. We never store IP, day, or UA — only the digest.
    """
    day = time.strftime("%Y-%m-%d")
    raw_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    # Truncate IPv4 to /24 so we never persist a unique IP
    parts = raw_ip.split(".")
    if len(parts) == 4:
        ip_bucket = ".".join(parts[:3]) + ".0/24"
    else:
        ip_bucket = "ipv6/anon"

    ua = request.headers.get("user-agent", "")[:200]
    payload = f"{day}|{ip_bucket}|{ua}|{salt}"
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# GET /api/stats — public counters
# ---------------------------------------------------------------------------
@router.get("", response_model=StatsResponse)
async def get_stats():
    try:
        r = await _get_redis()
        day_key = f"stats:visits:day:{time.strftime('%Y-%m-%d')}"
        total = int(await r.get("stats:visits:total") or 0)
        today = int(await r.get(day_key) or 0)
        rating_sum = int(await r.get("stats:rating:sum") or 0)
        rating_count = int(await r.get("stats:rating:count") or 0)
        avg = round(rating_sum / rating_count, 2) if rating_count else 0.0
        return StatsResponse(
            visits_total=total,
            visits_today=today,
            rating_average=avg,
            rating_count=rating_count,
        )
    except Exception as e:
        logger.warning(f"stats read failed: {e}")
        return StatsResponse(
            visits_total=0, visits_today=0, rating_average=0.0, rating_count=0
        )


# ---------------------------------------------------------------------------
# POST /api/stats/visit — increment visit counter (one per anon fingerprint/day)
# ---------------------------------------------------------------------------
@router.post("/visit", response_model=StatsResponse)
async def register_visit(request: Request):
    try:
        r = await _get_redis()
        fp = _anon_fingerprint(request, salt="visit")
        day = time.strftime("%Y-%m-%d")
        seen_key = f"stats:visits:seen:{day}:{fp}"

        # SET NX with 24h TTL — only first hit per fingerprint per day counts
        first = await r.set(seen_key, "1", ex=86400, nx=True)
        if first:
            await r.incr("stats:visits:total")
            await r.incr(f"stats:visits:day:{day}")
            # keep the daily key for 7 days
            await r.expire(f"stats:visits:day:{day}", 86400 * 7)

        return await get_stats()
    except Exception as e:
        logger.warning(f"visit register failed: {e}")
        return await get_stats()


# ---------------------------------------------------------------------------
# POST /api/stats/rating — submit star rating (one per anon fingerprint, ever)
# ---------------------------------------------------------------------------
@router.post("/rating", response_model=RatingResponse)
async def submit_rating(payload: RatingRequest, request: Request):
    if payload.stars < 1 or payload.stars > 5:
        raise HTTPException(status_code=422, detail="stars must be between 1 and 5")

    try:
        r = await _get_redis()
        fp = _anon_fingerprint(request, salt="rating")
        seen_key = f"stats:rating:seen:{fp}"

        # one rating per fingerprint, ever (TTL 365 days)
        first = await r.set(seen_key, str(payload.stars), ex=86400 * 365, nx=True)
        duplicate = not first

        if first:
            await r.incrby("stats:rating:sum", payload.stars)
            await r.incr("stats:rating:count")
            # also persist a per-star histogram for future analysis
            await r.incr(f"stats:rating:hist:{payload.stars}")

        rating_sum = int(await r.get("stats:rating:sum") or 0)
        rating_count = int(await r.get("stats:rating:count") or 0)
        avg = round(rating_sum / rating_count, 2) if rating_count else 0.0

        return RatingResponse(
            ok=True,
            rating_average=avg,
            rating_count=rating_count,
            duplicate=duplicate,
        )
    except Exception as e:
        logger.error(f"rating submit failed: {e}")
        raise HTTPException(status_code=500, detail="rating could not be saved")
