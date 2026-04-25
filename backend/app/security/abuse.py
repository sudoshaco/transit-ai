"""Abuse-Logging, IP-Banning und Export für Behörden-Weiterleitung."""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AbuseEvent, IpBan
from app.security.content_guard import GuardResult

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None
BAN_KEY_PREFIX = "ban:ip:"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis


async def is_ip_banned(ip: str) -> Optional[str]:
    if not ip:
        return None
    r = await get_redis()
    reason = await r.get(BAN_KEY_PREFIX + ip)
    return reason


async def ban_ip(ip: str, reason: str, ttl_seconds: int, db: AsyncSession) -> None:
    if not ip:
        return
    r = await get_redis()
    await r.set(BAN_KEY_PREFIX + ip, reason, ex=ttl_seconds)
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    # Upsert in Postgres (durable record — Redis kann verloren gehen)
    existing = await db.scalar(select(IpBan).where(IpBan.ip == ip))
    if existing:
        existing.reason = reason
        existing.expires_at = expires
    else:
        db.add(IpBan(ip=ip, reason=reason, expires_at=expires))
    await db.commit()
    logger.warning(f"IP banned: {ip} — {reason} (ttl={ttl_seconds}s)")


async def record_abuse(
    db: AsyncSession,
    *,
    guard: GuardResult,
    ip: Optional[str],
    user_agent: Optional[str],
    user_id: Optional[uuid.UUID],
    route: str,
    action: str,
) -> AbuseEvent:
    event = AbuseEvent(
        user_id=user_id,
        ip=ip,
        user_agent=(user_agent or "")[:500],
        category=guard.category or "unknown",
        severity=guard.severity,
        payload_hash=guard.payload_hash,
        payload_excerpt=guard.excerpt,
        matched_rules=guard.matched_rules,
        route=route,
        action_taken=action,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Auto-Ban nach N hoher Verstöße im Zeitfenster
    if guard.severity >= 4 and ip:
        window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.ABUSE_WINDOW_SECONDS)
        count = await db.scalar(
            select(AbuseEvent.id.label("id"))  # noqa: F841
        )
        from sqlalchemy import func as _func
        count = await db.scalar(
            select(_func.count(AbuseEvent.id))
            .where(AbuseEvent.ip == ip)
            .where(AbuseEvent.severity >= 4)
            .where(AbuseEvent.created_at >= window_start)
        )
        if (count or 0) >= settings.ABUSE_BAN_THRESHOLD:
            await ban_ip(ip, f"auto:{guard.category}:{count}_violations", settings.ABUSE_BAN_SECONDS, db)

    return event


def serialize_event(e: AbuseEvent) -> dict:
    return {
        "id": e.id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "user_id": str(e.user_id) if e.user_id else None,
        "ip": str(e.ip) if e.ip else None,
        "user_agent": e.user_agent,
        "category": e.category,
        "severity": e.severity,
        "payload_hash": e.payload_hash,
        "payload_excerpt": e.payload_excerpt,
        "matched_rules": e.matched_rules,
        "route": e.route,
        "action_taken": e.action_taken,
    }
