import logging
import time
from llm.providers.base import BaseProvider
from llm.providers.ollama_provider import OllamaProvider
from llm.providers.groq_provider import GroqProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Provider-Router mit Sticky-Decision (60s):
      Stufe 1: Groq Free Tier (~200ms, 14400 req/Tag)
      Stufe 2: Ollama lokal (Fallback, langsam aber unbegrenzt)

    Die Entscheidung wird 60s gecached, damit nicht vor jeder Anfrage
    Health-Pings durchgeführt werden müssen. Bei einem Fehler in
    `mark_failed()` wird der Cache gezielt invalidiert.
    """

    DECISION_TTL = 60.0  # seconds

    def __init__(self):
        self.groq = GroqProvider()
        self.ollama = OllamaProvider()
        self._cached_provider: BaseProvider | None = None
        self._cached_at: float = 0.0

    async def get_provider(self) -> BaseProvider:
        now = time.time()
        if self._cached_provider and (now - self._cached_at) < self.DECISION_TTL:
            return self._cached_provider

        # Stufe 1: Groq (schnellste Option, schlägt Ollama auf der GTX 1070 Ti um Faktor 25+)
        if self.groq.is_configured():
            logger.info("LLM Router: Groq selected (sticky 60s)")
            self._cached_provider = self.groq
            self._cached_at = now
            return self.groq

        # Stufe 2: Ollama lokal als Fallback
        try:
            if await self.ollama.is_available():
                logger.info("LLM Router: Ollama fallback selected (sticky 60s)")
                self._cached_provider = self.ollama
                self._cached_at = now
                return self.ollama
        except Exception as e:
            logger.warning(f"LLM Router: Ollama check failed: {e}")

        logger.error("LLM Router: no provider available")
        raise RuntimeError(
            "KI-Service momentan nicht verfügbar. Bitte in 1 Minute erneut versuchen."
        )

    def mark_failed(self, provider: BaseProvider) -> None:
        """Invalidate sticky cache so the next call re-selects a different provider."""
        if self._cached_provider is provider:
            logger.warning("LLM Router: marking current provider as failed, will re-pick")
            self._cached_provider = None
            self._cached_at = 0.0
