import json
import logging
import re
import secrets as pysecrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import (
    ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE, CSRF_HEADER,
    current_user, normalize_email,
)
from app.core.config import settings
from app.db.models import AuditLog, RefreshToken, User
from app.db.session import get_session
from app.security.client_ip import client_ip, user_agent
from app.security.jwt_tokens import (
    hash_refresh, issue_access_token, issue_refresh_token,
    make_csrf_token, verify_csrf,
)
from app.security.password import hash_password, needs_rehash, verify_password
from app.security import totp as totp_mod
from app.services.mail import send_mail, verify_email_html

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

MAX_FAILED_LOGINS = 5
LOCK_DURATION_SEC = 15 * 60
MAX_TOTP_ATTEMPTS = 5
TOTP_LOCK_DURATION_SEC = 30 * 60
PW_MIN = 10
PW_MAX = 256
VERIFY_TTL_SEC = 60 * 60 * 24           # 24h
VERIFY_RESEND_COOLDOWN = 60 * 2          # 2 min
CHALLENGE_TTL_SEC = 60 * 5               # 5 min

_weak_pw = {"passwort", "password", "12345678", "qwertzui", "letmein", "hallo123"}


class RegisterIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=PW_MIN, max_length=PW_MAX)


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=PW_MAX)


class VerifyIn(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)


class ResendVerifyIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)


class ChallengeIn(BaseModel):
    challenge_id: str = Field(..., min_length=16, max_length=128)
    code: str = Field(..., min_length=4, max_length=16)


class DeleteAccountIn(BaseModel):
    password: str = Field(..., min_length=1, max_length=PW_MAX)
    confirm: str = Field(..., min_length=1, max_length=32)


class TotpSetupIn(BaseModel):
    challenge_id: str = Field(..., min_length=16, max_length=128)


class AuthOut(BaseModel):
    id: str
    email: str
    tier: str
    is_verified: bool
    is_admin: bool
    username: str | None = None
    karma: int = 0
    bio: str | None = None
    joined: str | None = None
    comment_count: int = 0


class LoginChallengeOut(BaseModel):
    challenge_id: str
    requires_totp_setup: bool
    totp_qr_data_url: str | None = None
    totp_secret: str | None = None


class TotpConfirmOut(BaseModel):
    backup_codes: list[str]


def _password_is_strong(pw: str) -> tuple[bool, str]:
    if len(pw) < PW_MIN:
        return False, f"Passwort muss mindestens {PW_MIN} Zeichen haben."
    if pw.lower() in _weak_pw:
        return False, "Dieses Passwort ist zu schwach."
    if len(set(pw)) < 5:
        return False, "Passwort enthält zu wenig verschiedene Zeichen."
    classes = sum(bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w\s]"))
    if classes < 3:
        return False, "Passwort muss Klein-, Großbuchstaben, Ziffern oder Sonderzeichen mischen."
    return True, ""


def _set_auth_cookies(response: Response, access: str, refresh: str, csrf: str):
    common = dict(
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(ACCESS_COOKIE, access, max_age=settings.JWT_ACCESS_TTL_SECONDS, **common)
    response.set_cookie(REFRESH_COOKIE, refresh, max_age=settings.JWT_REFRESH_TTL_SECONDS, **common)
    csrf_cookie = {**common, "httponly": False}
    response.set_cookie(CSRF_COOKIE, csrf, max_age=settings.JWT_REFRESH_TTL_SECONDS, **csrf_cookie)


def _clear_auth_cookies(response: Response):
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.COOKIE_DOMAIN or None)


async def _log(db: AsyncSession, *, event: str, request: Request, user_id=None, meta=None):
    db.add(AuditLog(
        user_id=user_id,
        event=event,
        ip=client_ip(request),
        user_agent=user_agent(request),
        meta=meta or {},
    ))
    await db.commit()


async def _redis() -> aioredis.Redis:
    pw = getattr(settings, "REDIS_PASSWORD", "") or None
    return aioredis.from_url(settings.REDIS_URL, password=pw, decode_responses=True)


async def _issue_session(db: AsyncSession, user: User, request: Request, response: Response) -> None:
    now = datetime.now(timezone.utc)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    user.last_login_ip = client_ip(request)
    if needs_rehash(user.password_hash):
        pass  # nur beim Passwort-Login machbar
    await db.commit()

    access, _ = issue_access_token(str(user.id), user.tier, user.is_admin)
    raw, digest, rt_exp = issue_refresh_token(str(user.id))
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=digest,
        expires_at=rt_exp,
        user_agent=user_agent(request),
        ip=client_ip(request),
    ))
    await db.commit()
    csrf = make_csrf_token(digest)
    _set_auth_cookies(response, access, raw, csrf)


async def _send_verify_mail(user: User) -> None:
    token = pysecrets.token_urlsafe(32)
    user.email_verify_token = token
    user.email_verify_expires = datetime.now(timezone.utc) + timedelta(seconds=VERIFY_TTL_SEC)
    user.email_verify_sent_at = datetime.now(timezone.utc)
    base = getattr(settings, "APP_BASE_URL", "").rstrip("/") or "http://localhost"
    link = f"{base}/auth/verify?token={token}"
    await send_mail(user.email, "Transit-AI: E-Mail bestätigen", verify_email_html(link))


@router.post("/register", status_code=201)
async def register(
    payload: RegisterIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    try:
        valid = validate_email(payload.email, check_deliverability=False)
    except EmailNotValidError as e:
        raise HTTPException(status_code=422, detail=f"E-Mail ungültig: {e}")

    ok, err = _password_is_strong(payload.password)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    email_norm = normalize_email(valid.normalized)
    existing = await db.scalar(select(User).where(User.email_normalized == email_norm))
    if existing:
        await _log(db, event="register_duplicate", request=request, meta={"email_hash": email_norm[:3]})
        # Anti-Enumeration: gleiche Response wie bei Erfolg
        return {"ok": True, "message": "Bitte prüfe dein Postfach."}

    user = User(
        email=valid.original,
        email_normalized=email_norm,
        password_hash=hash_password(payload.password),
        tier="free",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await _send_verify_mail(user)
    await db.commit()
    await _log(db, event="register", request=request, user_id=user.id)
    return {"ok": True, "message": "Bitte prüfe dein Postfach."}


@router.post("/verify-email", response_model=AuthOut)
async def verify_email(
    payload: VerifyIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = await db.scalar(select(User).where(User.email_verify_token == payload.token))
    if not user or not user.email_verify_expires:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link.")
    if user.email_verify_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link.")

    user.is_verified = True
    user.email_verify_token = None
    user.email_verify_expires = None
    await db.commit()
    await _log(db, event="email_verified", request=request, user_id=user.id)
    return AuthOut(id=str(user.id), email=user.email, tier=user.tier, is_verified=True, is_admin=user.is_admin, username=user.username, karma=user.karma, bio=user.bio)


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerifyIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    email_norm = normalize_email(payload.email)
    user = await db.scalar(select(User).where(User.email_normalized == email_norm))
    # Immer 200 — kein User-Enumeration
    if user and not user.is_verified:
        if user.email_verify_sent_at and \
           (datetime.now(timezone.utc) - user.email_verify_sent_at).total_seconds() < VERIFY_RESEND_COOLDOWN:
            return {"ok": True}
        await _send_verify_mail(user)
        await db.commit()
        await _log(db, event="verify_resend", request=request, user_id=user.id)
    return {"ok": True}


@router.post("/login")
async def login(
    payload: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> LoginChallengeOut:
    email_norm = normalize_email(payload.email)
    user = await db.scalar(select(User).where(User.email_normalized == email_norm))

    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Konto vorübergehend gesperrt.")

    pw_ok = bool(user) and verify_password(user.password_hash, payload.password)
    if not pw_ok:
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(seconds=LOCK_DURATION_SEC)
                user.failed_login_count = 0
            await db.commit()
        await _log(db, event="login_failed", request=request,
                   user_id=user.id if user else None,
                   meta={"reason": "bad_credentials"})
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto deaktiviert.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Bitte bestätige zuerst deine E-Mail.")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        await db.commit()

    # 2FA-Challenge in Redis ablegen — 5min TTL
    challenge_id = pysecrets.token_urlsafe(32)
    r = await _redis()
    try:
        if user.totp_enabled and user.totp_secret_enc:
            payload_json = json.dumps({"uid": str(user.id), "kind": "verify"})
            await r.setex(f"auth:chal:{challenge_id}", CHALLENGE_TTL_SEC, payload_json)
            return LoginChallengeOut(challenge_id=challenge_id, requires_totp_setup=False)
        # Kein TOTP — Setup erzwingen
        secret = totp_mod.new_secret()
        uri = totp_mod.provisioning_uri(secret, user.email)
        qr = totp_mod.qr_png_data_url(uri)
        payload_json = json.dumps({"uid": str(user.id), "kind": "setup", "secret": secret})
        await r.setex(f"auth:chal:{challenge_id}", CHALLENGE_TTL_SEC, payload_json)
        return LoginChallengeOut(
            challenge_id=challenge_id,
            requires_totp_setup=True,
            totp_qr_data_url=qr,
            totp_secret=secret,
        )
    finally:
        await r.aclose()


@router.post("/login/verify", response_model=AuthOut)
async def login_verify(
    payload: ChallengeIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    r = await _redis()
    try:
        chal_key = f"auth:chal:{payload.challenge_id}"
        attempts_key = f"auth:chal:attempts:{payload.challenge_id}"
        raw = await r.get(chal_key)
        if not raw:
            raise HTTPException(status_code=400, detail="Challenge abgelaufen — bitte erneut anmelden.")
        attempts = int(await r.get(attempts_key) or 0)
        if attempts >= MAX_TOTP_ATTEMPTS:
            await r.delete(chal_key)
            await r.delete(attempts_key)
            await _log(db, event="totp_brute_force_blocked", request=request,
                       meta={"challenge_id": payload.challenge_id})
            raise HTTPException(status_code=429, detail="Zu viele Fehlversuche. Bitte neu anmelden.")
        data = json.loads(raw)
        uid = data["uid"]
        kind = data["kind"]
        user = await db.scalar(select(User).where(User.id == uid))
        if not user or not user.is_active or not user.is_verified:
            raise HTTPException(status_code=401, detail="Konto nicht verfügbar.")
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail="Konto vorübergehend gesperrt.")

        if kind == "setup":
            secret = data["secret"]
            if not totp_mod.verify(secret, payload.code):
                raise HTTPException(status_code=401, detail="Code falsch.")
            user.totp_secret_enc = totp_mod.encrypt_secret(secret)
            user.totp_enabled = True
            user.totp_confirmed_at = datetime.now(timezone.utc)
            plains, hashes = totp_mod.new_backup_codes()
            user.totp_backup_codes = hashes
            await _issue_session(db, user, request, response)
            await r.delete(f"auth:chal:{payload.challenge_id}")
            await _log(db, event="totp_enabled", request=request, user_id=user.id)
            # Backup-Codes einmalig anzeigen → via Cookie-Antwort (separat zu JSON)
            response.headers["X-Backup-Codes"] = ",".join(plains)
            return AuthOut(id=str(user.id), email=user.email, tier=user.tier, is_verified=True, is_admin=user.is_admin, username=user.username, karma=user.karma, bio=user.bio)

        # kind == "verify"
        secret = totp_mod.decrypt_secret(user.totp_secret_enc or "")
        code = payload.code.strip()
        ok = totp_mod.verify(secret, code)
        if not ok and user.totp_backup_codes:
            idx = totp_mod.backup_matches(code, list(user.totp_backup_codes))
            if idx is not None:
                remaining = list(user.totp_backup_codes)
                remaining.pop(idx)
                user.totp_backup_codes = remaining
                ok = True
                await _log(db, event="backup_code_used", request=request,
                           user_id=user.id, meta={"remaining": len(remaining)})
        if not ok:
            new_attempts = await r.incr(attempts_key)
            await r.expire(attempts_key, CHALLENGE_TTL_SEC)
            await _log(db, event="totp_failed", request=request, user_id=user.id,
                       meta={"attempts": int(new_attempts)})
            if int(new_attempts) >= MAX_TOTP_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(seconds=TOTP_LOCK_DURATION_SEC)
                await db.commit()
                await r.delete(chal_key)
                await _log(db, event="totp_account_locked", request=request, user_id=user.id)
                raise HTTPException(status_code=423, detail="Konto wegen Brute-Force gesperrt. Versuche es später erneut.")
            raise HTTPException(status_code=401, detail="Code falsch.")

        await _issue_session(db, user, request, response)
        await r.delete(f"auth:chal:{payload.challenge_id}")
        await _log(db, event="login", request=request, user_id=user.id)
        return AuthOut(id=str(user.id), email=user.email, tier=user.tier, is_verified=True, is_admin=user.is_admin, username=user.username, karma=user.karma, bio=user.bio)
    finally:
        await r.aclose()


@router.post("/refresh", response_model=AuthOut)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    raw = request.cookies.get(REFRESH_COOKIE)
    csrf = request.headers.get(CSRF_HEADER) or request.cookies.get(CSRF_COOKIE)
    if not raw or not csrf:
        raise HTTPException(status_code=401, detail="Keine gültige Session.")
    if not verify_csrf(hash_refresh(raw), csrf):
        raise HTTPException(status_code=403, detail="CSRF-Validierung fehlgeschlagen.")

    digest = hash_refresh(raw)
    tok = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
    now = datetime.now(timezone.utc)
    if not tok or tok.revoked_at or tok.expires_at <= now:
        if tok and tok.revoked_at:
            await db.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.user_id == tok.user_id)
                .values(revoked_at=now)
            )
            await db.commit()
            await _log(db, event="refresh_replay_detected", request=request, user_id=tok.user_id)
        raise HTTPException(status_code=401, detail="Session abgelaufen.")

    user = await db.scalar(select(User).where(User.id == tok.user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Konto deaktiviert.")

    tok.revoked_at = now
    new_raw, new_digest, new_exp = issue_refresh_token(str(user.id))
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=new_digest,
        expires_at=new_exp,
        rotated_from=tok.id,
        user_agent=user_agent(request),
        ip=client_ip(request),
    ))
    await db.commit()

    access, _ = issue_access_token(str(user.id), user.tier, user.is_admin)
    new_csrf = make_csrf_token(new_digest)
    _set_auth_cookies(response, access, new_raw, new_csrf)
    return AuthOut(id=str(user.id), email=user.email, tier=user.tier, is_verified=user.is_verified, is_admin=user.is_admin, username=user.username, karma=user.karma, bio=user.bio)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        digest = hash_refresh(raw)
        tok = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
        if tok and not tok.revoked_at:
            tok.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            await _log(db, event="logout", request=request, user_id=tok.user_id)
    _clear_auth_cookies(response)
    return Response(status_code=204)


@router.delete("/me", status_code=204)
async def delete_me(
    payload: DeleteAccountIn,
    request: Request,
    response: Response,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    # Harte Schranke: Passwort + getippte Bestätigung
    if payload.confirm.strip().upper() != "LÖSCHEN":
        raise HTTPException(status_code=422, detail="Bitte 'LÖSCHEN' zur Bestätigung eingeben.")
    if not verify_password(user.password_hash, payload.password):
        await _log(db, event="account_delete_failed", request=request, user_id=user.id,
                   meta={"reason": "bad_password"})
        raise HTTPException(status_code=401, detail="Passwort falsch.")

    uid = user.id
    email = user.email
    # Forensik: Audit-Eintrag vor Löschung (user_id wird per SET NULL auf NULL gesetzt)
    await _log(db, event="account_deleted", request=request, user_id=uid,
               meta={"email_hash": hash_refresh(email)[:16]})
    # User-Löschung: Kommentare, Votes, Refresh-Tokens kaskadieren via FK ON DELETE CASCADE.
    # AuditLog- und AbuseEvent-Referenzen werden via SET NULL anonymisiert.
    await db.execute(delete(User).where(User.id == uid))
    await db.commit()
    _clear_auth_cookies(response)
    return Response(status_code=204)


@router.get("/me", response_model=AuthOut)
async def me(user=Depends(current_user), db: AsyncSession = Depends(get_session)):
    from app.db.models import ConnectionComment
    from sqlalchemy import func
    cc = await db.scalar(
        select(func.count(ConnectionComment.id))
        .where(ConnectionComment.author_id == user.id)
        .where(ConnectionComment.hidden.is_(False))
    )
    return AuthOut(
        id=str(user.id), email=user.email, tier=user.tier,
        is_verified=user.is_verified, is_admin=user.is_admin,
        username=user.username, karma=user.karma, bio=user.bio,
        joined=user.created_at.isoformat() if user.created_at else None,
        comment_count=int(cc or 0),
    )
