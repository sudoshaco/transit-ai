"""Community: Kommentare + Votes pro Verbindung, Nutzerprofil, Karma-Bestenliste."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_user, current_user_optional
from app.db.models import AuditLog, ConnectionComment, ConnectionVote, User
from app.db.session import get_session
from app.security.client_ip import client_ip, user_agent

router = APIRouter(tags=["community"])

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
BODY_MAX = 140
BIO_MAX = 280
COMMENT_DAILY_LIMIT = 10
VOTE_DAILY_LIMIT = 200
USERNAME_CHANGE_COOLDOWN_DAYS = 30

RESERVED_EXACT = {
    "admin", "administrator", "support", "moderator", "mod", "mentor",
    "inspirator", "staff", "team", "root", "owner", "system", "official",
    "help", "helpdesk", "service", "kontakt", "contact", "info", "security",
    "transit", "transitai", "transit_ai", "bahn", "db", "deutschebahn",
    "null", "undefined", "user", "api", "www", "mail", "noreply",
}
RESERVED_SUBSTRINGS = (
    "nigg", "nger", "neger", "kanak", "schwuchtel", "hitler", "nazi", "ss88",
    "1488", "heil", "juden", "zigeuner", "retard", "fag", "faggot", "tranny",
    "kike", "chink", "spic", "pedo", "rape", "rapist", "fuck", "cunt",
    "bitch", "fotze", "hure", "nutte", "wichser", "isis", "terror",
)

def _username_forbidden(h: str) -> str | None:
    low = h.lower()
    if low in RESERVED_EXACT:
        return "Dieser Name ist reserviert."
    for bad in RESERVED_SUBSTRINGS:
        if bad in low:
            return "Dieser Name ist nicht erlaubt."
    return None

_BIO_FORBID_RE = re.compile(r"(https?://|www\.|<|>|javascript:|data:|\{\{|\}\}|onerror|onclick)", re.I)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------- Schemas ----------
class UsernameIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)


class BioIn(BaseModel):
    bio: str = Field(default="", max_length=BIO_MAX)


class CommentIn(BaseModel):
    line: str = Field(..., min_length=1, max_length=40)
    from_id: str = Field(..., min_length=1, max_length=40)
    from_name: str = Field(..., min_length=1, max_length=120)
    to_id: str = Field(..., min_length=1, max_length=40)
    to_name: str = Field(..., min_length=1, max_length=120)
    hhmm: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    weekday: int = Field(..., ge=0, le=6)
    body: str = Field(..., min_length=1, max_length=BODY_MAX)


class VoteIn(BaseModel):
    value: int = Field(..., ge=-1, le=1)


class CommentOut(BaseModel):
    id: str
    body: str
    score: int
    upvotes: int
    downvotes: int
    created_at: str
    author: str
    author_karma: int
    my_vote: int | None = None


class ProfileOut(BaseModel):
    username: str
    karma: int
    joined: str
    comment_count: int
    bio: str | None = None
    recent_comments: list[CommentOut]


class LeaderboardRow(BaseModel):
    username: str
    karma: int
    comment_count: int


# ---------- Helpers ----------
def _fp_hash(line: str, from_id: str, to_id: str, hhmm: str, weekday: int) -> str:
    raw = f"{line.lower().strip()}|{from_id}|{to_id}|{hhmm}|{weekday}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _require_username(user: User) -> None:
    if not user.username:
        raise HTTPException(status_code=428, detail="Bitte zuerst Username festlegen.")


async def _recompute_karma(db: AsyncSession, user_id) -> None:
    total = await db.scalar(
        select(func.coalesce(func.sum(ConnectionComment.score), 0))
        .where(ConnectionComment.author_id == user_id)
        .where(ConnectionComment.hidden.is_(False))
    )
    await db.execute(update(User).where(User.id == user_id).values(karma=int(total or 0)))


# ---------- Username ----------
@router.post("/username", status_code=204)
async def set_username(
    payload: UsernameIn,
    request: Request,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    handle = payload.username.lower().strip()
    if not USERNAME_RE.match(handle):
        raise HTTPException(status_code=422, detail="3–20 Zeichen, a-z 0-9 _ erlaubt.")
    forbid = _username_forbidden(handle)
    if forbid:
        raise HTTPException(status_code=422, detail=forbid)

    # Cooldown bei Änderung (nicht bei initialem Setzen)
    if user.username and user.username != handle:
        if user.username_changed_at:
            next_change = user.username_changed_at + timedelta(days=USERNAME_CHANGE_COOLDOWN_DAYS)
            if datetime.now(timezone.utc) < next_change:
                raise HTTPException(
                    status_code=429,
                    detail=f"Username kann erst am {next_change.date().isoformat()} wieder geändert werden.",
                )
    if user.username == handle:
        return

    taken = await db.scalar(select(User).where(User.username == handle).where(User.id != user.id))
    if taken:
        raise HTTPException(status_code=409, detail="Username bereits vergeben.")

    is_change = bool(user.username)
    user.username = handle
    if is_change:
        user.username_changed_at = datetime.now(timezone.utc)
    await db.commit()
    db.add(AuditLog(user_id=user.id, event="username_changed" if is_change else "username_set",
                    ip=client_ip(request), user_agent=user_agent(request),
                    meta={"handle": handle}))
    await db.commit()


# ---------- Bio ----------
@router.post("/bio", status_code=204)
async def set_bio(
    payload: BioIn,
    request: Request,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    raw = (payload.bio or "").strip()
    raw = _CONTROL_RE.sub("", raw)
    if len(raw) > BIO_MAX:
        raise HTTPException(status_code=422, detail=f"Max. {BIO_MAX} Zeichen.")
    if raw and _BIO_FORBID_RE.search(raw):
        raise HTTPException(status_code=422, detail="HTML, Links oder Scripts sind in der Bio nicht erlaubt.")
    user.bio = raw or None
    await db.commit()
    db.add(AuditLog(user_id=user.id, event="bio_update",
                    ip=client_ip(request), user_agent=user_agent(request),
                    meta={"len": len(raw)}))
    await db.commit()


# ---------- Comments ----------
@router.get("/comments")
async def list_comments(
    line: str, from_id: str, to_id: str, hhmm: str, weekday: int,
    db: AsyncSession = Depends(get_session),
    user: User | None = Depends(current_user_optional),
):
    fp = _fp_hash(line, from_id, to_id, hhmm, weekday)
    q = (
        select(ConnectionComment, User.username, User.karma)
        .join(User, User.id == ConnectionComment.author_id)
        .where(ConnectionComment.fp_hash == fp)
        .where(ConnectionComment.hidden.is_(False))
        .order_by(ConnectionComment.score.desc(), ConnectionComment.created_at.desc())
        .limit(50)
    )
    rows = (await db.execute(q)).all()
    my_votes: dict = {}
    if user and rows:
        ids = [c.id for c, _, _ in rows]
        vq = await db.execute(
            select(ConnectionVote.comment_id, ConnectionVote.value)
            .where(ConnectionVote.user_id == user.id)
            .where(ConnectionVote.comment_id.in_(ids))
        )
        my_votes = {cid: v for cid, v in vq.all()}
    return {
        "fp_hash": fp,
        "comments": [
            {
                "id": str(c.id), "body": c.body, "score": c.score,
                "upvotes": c.upvotes, "downvotes": c.downvotes,
                "created_at": c.created_at.isoformat(),
                "author": uname, "author_karma": karma,
                "my_vote": my_votes.get(c.id),
            }
            for c, uname, karma in rows
        ],
    }


@router.post("/comments", status_code=201)
async def create_comment(
    payload: CommentIn,
    request: Request,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    await _require_username(user)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Leer.")
    # Simple Profanity / Injection-Guard: blocke offensichtliche URLs + Scripts
    if re.search(r"(https?://|<script|\{\{|</|onerror=)", body, re.I):
        raise HTTPException(status_code=422, detail="Unerlaubter Inhalt.")

    # Daily limit
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today = await db.scalar(
        select(func.count(ConnectionComment.id))
        .where(ConnectionComment.author_id == user.id)
        .where(ConnectionComment.created_at >= since)
    )
    if (today or 0) >= COMMENT_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail=f"Max. {COMMENT_DAILY_LIMIT} Kommentare pro Tag.")

    fp = _fp_hash(payload.line, payload.from_id, payload.to_id, payload.hhmm, payload.weekday)
    meta = {
        "line": payload.line, "from_name": payload.from_name, "to_name": payload.to_name,
        "hhmm": payload.hhmm, "weekday": payload.weekday,
    }
    # Unique (author, fp) — DB constraint fängt Dupe
    c = ConnectionComment(author_id=user.id, fp_hash=fp, fp_meta=meta, body=body)
    db.add(c)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Du hast zu dieser Verbindung schon kommentiert.")
    await db.refresh(c)
    return {"id": str(c.id), "fp_hash": fp}


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    c = await db.scalar(select(ConnectionComment).where(ConnectionComment.id == comment_id))
    if not c or c.author_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    author_id = c.author_id
    await db.execute(delete(ConnectionComment).where(ConnectionComment.id == comment_id))
    await db.commit()
    await _recompute_karma(db, author_id)
    await db.commit()


# ---------- Vote ----------
@router.post("/comments/{comment_id}/vote")
async def vote(
    comment_id: str,
    payload: VoteIn,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    await _require_username(user)
    c = await db.scalar(select(ConnectionComment).where(ConnectionComment.id == comment_id))
    if not c or c.hidden:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    if c.author_id == user.id:
        raise HTTPException(status_code=400, detail="Eigenen Kommentar nicht voten.")

    # Daily vote limit
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    votes_today = await db.scalar(
        select(func.count()).select_from(ConnectionVote)
        .where(ConnectionVote.user_id == user.id)
        .where(ConnectionVote.created_at >= since)
    )
    if (votes_today or 0) >= VOTE_DAILY_LIMIT and payload.value != 0:
        raise HTTPException(status_code=429, detail="Tages-Voting-Limit erreicht.")

    existing = await db.scalar(
        select(ConnectionVote)
        .where(ConnectionVote.user_id == user.id)
        .where(ConnectionVote.comment_id == comment_id)
    )

    # Tally diff
    if existing:
        if payload.value == 0:
            if existing.value == 1:
                c.upvotes = max(0, c.upvotes - 1)
            else:
                c.downvotes = max(0, c.downvotes - 1)
            await db.delete(existing)
        elif existing.value != payload.value:
            if payload.value == 1:
                c.upvotes += 1
                c.downvotes = max(0, c.downvotes - 1)
            else:
                c.downvotes += 1
                c.upvotes = max(0, c.upvotes - 1)
            existing.value = payload.value
    else:
        if payload.value == 0:
            return {"score": c.score, "my_vote": None}
        db.add(ConnectionVote(user_id=user.id, comment_id=comment_id, value=payload.value))
        if payload.value == 1:
            c.upvotes += 1
        else:
            c.downvotes += 1

    c.score = c.upvotes - c.downvotes
    await db.commit()
    await _recompute_karma(db, c.author_id)
    await db.commit()

    return {"score": c.score, "upvotes": c.upvotes, "downvotes": c.downvotes,
            "my_vote": payload.value if payload.value != 0 else None}


# ---------- Profiles ----------
@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=2, max_length=30),
    db: AsyncSession = Depends(get_session),
):
    pattern = f"%{q.lower().strip()}%"
    rows = (await db.execute(
        select(User.username, User.karma)
        .where(User.username.ilike(pattern))
        .where(User.username.isnot(None))
        .order_by(User.karma.desc())
        .limit(20)
    )).all()
    return {"users": [{"username": u, "karma": k} for u, k in rows]}


@router.get("/users/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_session)):
    comment_counts = (
        select(ConnectionComment.author_id, func.count(ConnectionComment.id).label("cc"))
        .where(ConnectionComment.hidden.is_(False))
        .group_by(ConnectionComment.author_id)
        .subquery()
    )
    rows = (await db.execute(
        select(User.username, User.karma, func.coalesce(comment_counts.c.cc, 0), User.created_at)
        .outerjoin(comment_counts, comment_counts.c.author_id == User.id)
        .where(User.username.isnot(None))
        .order_by(User.karma.desc(), User.created_at.asc())
        .limit(50)
    )).all()
    return {"users": [
        {"username": u, "karma": k, "comment_count": cc, "joined": ts.isoformat() if ts else None}
        for u, k, cc, ts in rows
    ]}


@router.get("/users/{username}", response_model=ProfileOut)
async def user_profile(username: str, db: AsyncSession = Depends(get_session)):
    handle = username.lower().strip()
    user = await db.scalar(select(User).where(User.username == handle))
    if not user:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden.")
    count = await db.scalar(
        select(func.count(ConnectionComment.id))
        .where(ConnectionComment.author_id == user.id)
        .where(ConnectionComment.hidden.is_(False))
    )
    recent = (await db.execute(
        select(ConnectionComment)
        .where(ConnectionComment.author_id == user.id)
        .where(ConnectionComment.hidden.is_(False))
        .order_by(ConnectionComment.created_at.desc())
        .limit(20)
    )).scalars().all()
    return ProfileOut(
        username=user.username,
        karma=user.karma,
        joined=user.created_at.isoformat(),
        comment_count=int(count or 0),
        bio=user.bio,
        recent_comments=[
            CommentOut(
                id=str(c.id), body=c.body, score=c.score,
                upvotes=c.upvotes, downvotes=c.downvotes,
                created_at=c.created_at.isoformat(),
                author=user.username, author_karma=user.karma,
            )
            for c in recent
        ],
    )
