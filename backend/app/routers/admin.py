"""Admin-Endpoints: Abuse-Export und Ban-Management (nur für is_admin)."""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_admin
from app.db.models import AbuseEvent, IpBan, AuditLog
from app.db.session import get_session
from app.security.abuse import ban_ip, get_redis, BAN_KEY_PREFIX, serialize_event
from app.core.config import settings

router = APIRouter(tags=["admin"])


class BanIn(BaseModel):
    ip: str
    reason: str
    ttl_seconds: int = settings.ABUSE_BAN_SECONDS


@router.get("/abuse/events")
async def list_abuse(
    limit: int = Query(100, le=1000),
    since_hours: int = Query(168, le=24 * 30),
    category: Optional[str] = None,
    min_severity: int = 1,
    _=Depends(current_admin),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(AbuseEvent).where(
        AbuseEvent.created_at >= datetime.now(timezone.utc) - timedelta(hours=since_hours),
        AbuseEvent.severity >= min_severity,
    ).order_by(desc(AbuseEvent.created_at)).limit(limit)
    if category:
        stmt = stmt.where(AbuseEvent.category == category)
    rows = (await db.scalars(stmt)).all()
    return [serialize_event(e) for e in rows]


@router.get("/abuse/export.csv")
async def export_abuse_csv(
    since_hours: int = Query(24 * 30, le=24 * 365),
    _=Depends(current_admin),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(AbuseEvent).where(
        AbuseEvent.created_at >= datetime.now(timezone.utc) - timedelta(hours=since_hours),
    ).order_by(desc(AbuseEvent.created_at))
    rows = (await db.scalars(stmt)).all()

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    w.writerow([
        "id", "created_at_utc", "ip", "user_id", "category", "severity",
        "action_taken", "payload_hash", "matched_rules", "route", "user_agent", "payload_excerpt",
    ])
    for e in rows:
        w.writerow([
            e.id,
            e.created_at.isoformat() if e.created_at else "",
            str(e.ip) if e.ip else "",
            str(e.user_id) if e.user_id else "",
            e.category, e.severity, e.action_taken or "",
            e.payload_hash,
            ",".join(e.matched_rules or []),
            e.route or "",
            (e.user_agent or "").replace("\n", " "),
            (e.payload_excerpt or "").replace("\n", " ").replace("\r", " ")[:2000],
        ])
    buf.seek(0)
    filename = f"abuse_export_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/bans", status_code=201)
async def create_ban(
    payload: BanIn,
    _=Depends(current_admin),
    db: AsyncSession = Depends(get_session),
):
    if payload.ttl_seconds < 60 or payload.ttl_seconds > 60 * 60 * 24 * 365 * 2:
        raise HTTPException(422, "ttl_seconds außerhalb erlaubtem Bereich")
    await ban_ip(payload.ip, payload.reason, payload.ttl_seconds, db)
    return {"ok": True}


@router.get("/bans")
async def list_bans(
    _=Depends(current_admin),
    db: AsyncSession = Depends(get_session),
):
    rows = (await db.scalars(select(IpBan).order_by(desc(IpBan.created_at)).limit(500))).all()
    return [
        {
            "ip": str(b.ip),
            "reason": b.reason,
            "expires_at": b.expires_at.isoformat() if b.expires_at else None,
            "created_at": b.created_at.isoformat(),
        }
        for b in rows
    ]


@router.delete("/bans/{ip}", status_code=204)
async def unban(
    ip: str,
    _=Depends(current_admin),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import delete
    r = await get_redis()
    await r.delete(BAN_KEY_PREFIX + ip)
    await db.execute(delete(IpBan).where(IpBan.ip == ip))
    await db.commit()
