import httpx
import logging
from llm.providers.base import BaseProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """
    Qwen2.5 7B auf GTX 1070 Ti (8GB VRAM).
    Passt mit ~5GB in den VRAM, ~45 Tokens/Sekunde.
    Fallback-Provider — Groq ist primary.

    Optimierungen:
      - Persistenter httpx.AsyncClient (kein Connection-Setup je Request)
      - Vereinfachte Verfügbarkeitsprüfung (kein Load-Score mehr)
    """

    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.MODEL = settings.OLLAMA_MODEL
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(60.0, connect=5.0),
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            )
        return self._client

    async def complete(self, system: str, user: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        try:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self.MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                        "num_gpu": 1,
                        "num_thread": 4,
                    },
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except httpx.TimeoutException:
            logger.error("Ollama request timed out (60s)")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise
        except KeyError:
            logger.error("Unexpected Ollama response format")
            raise

    async def is_available(self) -> bool:
        """Prüft ob das konfigurierte Modell auf Ollama geladen werden kann."""
        try:
            client = self._get_client()
            r = await client.get("/api/tags", timeout=5.0)
            models = [m["name"] for m in r.json().get("models", [])]
            model_base = self.MODEL.split(":")[0]
            return any(model_base in m for m in models)
        except Exception:
            return False

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
