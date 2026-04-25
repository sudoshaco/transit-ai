"""Resend HTTP client — transactional mail (Verify + security events)."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


async def send_mail(to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    key = getattr(settings, "RESEND_API_KEY", "")
    sender = getattr(settings, "RESEND_FROM", "")
    if not key or not sender:
        logger.warning("Resend nicht konfiguriert — Mail an %s nicht versendet.", to)
        return False

    payload = {
        "from": f"Transit-AI <{sender}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                _RESEND_URL,
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
        if r.status_code >= 300:
            logger.error("Resend %s: %s", r.status_code, r.text[:400])
            return False
        return True
    except Exception as e:
        logger.error("Resend network error: %s", e)
        return False


def verify_email_html(link: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de"><body style="font-family:system-ui,sans-serif;background:#0a0a0a;color:#f5f5f5;padding:32px">
<div style="max-width:520px;margin:0 auto;background:#141414;border-radius:12px;padding:32px">
  <h1 style="margin:0 0 16px;color:#ffb400">Transit-AI</h1>
  <p style="font-size:16px;line-height:1.6">Hallo,</p>
  <p style="font-size:16px;line-height:1.6">um dein Konto zu aktivieren, klick bitte auf den Bestätigungs-Button. Der Link ist 24 Stunden gültig.</p>
  <p style="margin:24px 0"><a href="{link}" style="background:#ffb400;color:#0a0a0a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">E-Mail bestätigen</a></p>
  <p style="font-size:13px;color:#999">Oder kopiere diesen Link in den Browser:<br><code style="color:#ccc;word-break:break-all">{link}</code></p>
  <hr style="border:none;border-top:1px solid #2a2a2a;margin:24px 0">
  <p style="font-size:12px;color:#777">Du hast dich nicht registriert? Ignoriere diese Mail einfach.</p>
</div></body></html>"""


def login_alert_html(ip: str, ua: str, when: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de"><body style="font-family:system-ui,sans-serif;background:#0a0a0a;color:#f5f5f5;padding:32px">
<div style="max-width:520px;margin:0 auto;background:#141414;border-radius:12px;padding:32px">
  <h1 style="margin:0 0 16px;color:#ffb400">Neuer Login</h1>
  <p style="font-size:16px;line-height:1.6">Ein neuer Login in dein Transit-AI Konto wurde erkannt:</p>
  <ul style="font-size:14px;line-height:1.8;color:#ccc">
    <li><b>Zeit:</b> {when}</li>
    <li><b>IP:</b> {ip}</li>
    <li><b>Gerät:</b> {ua[:120]}</li>
  </ul>
  <p style="font-size:13px;color:#999">Warst du das nicht? Ändere sofort dein Passwort.</p>
</div></body></html>"""
