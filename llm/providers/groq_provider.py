import httpx
import logging
from llm.providers.base import BaseProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(BaseProvider):
    """
    Groq Free Tier — kostenlos, 500-800 Tokens/Sekunde.
    Modell: llama-3.1-8b-instant
    Limit: 14.400 Anfragen/Tag, 30 req/min
    Primary Provider (schneller als lokales Ollama auf GTX 1070 Ti).
    API Key kostenlos unter: https://console.groq.com

    Optimierungen:
      - Persistenter httpx.AsyncClient (kein TLS-Handshake je Request)
      - Kein has_quota()-Ping mehr — Konfigurationscheck reicht (sticky 60s im Router)
    """

    MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                http2=False,
            )
        return self._client

    async def complete(self, system: str, user: str, max_tokens: int = 512) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY nicht gesetzt")

        client = self._get_client()
        try:
            response = await client.post(
                GROQ_API_URL,
                json={
                    "model": self.MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq HTTP error: {e.response.status_code} {e.response.text[:200]}")
            raise
        except (KeyError, IndexError):
            logger.error("Unexpected Groq response format")
            raise

    async def is_available(self) -> bool:
        """Wird vom Router nur noch zur Abwärtskompatibilität gerufen."""
        return self.is_configured()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
