"""TOTP (RFC 6238) + Backup-Codes.

Secret wird bei Setup generiert, bis zur Bestätigung in Redis zwischengespeichert
und erst nach erfolgreicher Verifikation in die DB geschrieben (verschlüsselt via Fernet).
"""
from __future__ import annotations

import base64
import hashlib
import io
import secrets
from typing import List, Tuple

import pyotp
import qrcode
from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    seed = (settings.JWT_SECRET + "|totp").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="Transit-AI")


def qr_png_data_url(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def verify(secret: str, code: str) -> bool:
    if not code or not secret:
        return False
    try:
        return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
    except Exception:
        return False


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def new_backup_codes(n: int = 8) -> Tuple[List[str], List[str]]:
    """Returns (plain_codes_for_user, hashed_codes_for_db)."""
    plains = [f"{secrets.randbelow(10**4):04d}-{secrets.randbelow(10**4):04d}" for _ in range(n)]
    hashes = [hashlib.sha256(c.encode()).hexdigest() for c in plains]
    return plains, hashes


def backup_matches(code: str, stored: List[str]) -> int | None:
    """Returns index of matching hash, or None."""
    h = hashlib.sha256(code.strip().encode()).hexdigest()
    for i, s in enumerate(stored):
        if secrets.compare_digest(h, s):
            return i
    return None
