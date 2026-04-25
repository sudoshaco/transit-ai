import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings


ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def issue_access_token(user_id: str, tier: str, is_admin: bool) -> tuple[str, datetime]:
    exp = _now() + timedelta(seconds=settings.JWT_ACCESS_TTL_SECONDS)
    payload = {
        "sub": str(user_id),
        "typ": ACCESS_TYPE,
        "tier": tier,
        "adm": bool(is_admin),
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    return token, exp


def issue_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Returns (raw_token, sha256_hash, expires_at)."""
    raw = secrets.token_urlsafe(64)
    exp = _now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SECONDS)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, digest, exp


def hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access(token: str) -> dict:
    data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    if data.get("typ") != ACCESS_TYPE:
        raise jwt.InvalidTokenError("wrong token type")
    return data


def make_csrf_token(session_id: str) -> str:
    secret = settings.CSRF_SECRET or settings.JWT_SECRET
    return hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()


def verify_csrf(session_id: str, csrf: str) -> bool:
    expected = make_csrf_token(session_id)
    return hmac.compare_digest(expected, csrf or "")
