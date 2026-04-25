from typing import Optional
import uuid
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import User
from app.security.jwt_tokens import decode_access

ACCESS_COOKIE = "tai_at"
REFRESH_COOKIE = "tai_rt"
CSRF_COOKIE = "tai_csrf"
CSRF_HEADER = "X-CSRF-Token"


async def current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        # Fallback: Authorization: Bearer (für API-Clients)
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        data = decode_access(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    try:
        uid = uuid.UUID(data["sub"])
    except (KeyError, ValueError):
        return None
    user = await db.scalar(select(User).where(User.id == uid))
    if user and user.is_active:
        return user
    return None


async def current_user(
    user: Optional[User] = Depends(current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht angemeldet")
    return user


async def current_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user


def normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    # local-part + domain. Wir lowercase beides (pragmatisch, konform genug).
    return email
