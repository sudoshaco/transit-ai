import json
import hashlib
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from app.models.request import UserIntent
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from llm.providers.router import LLMRouter
from llm.prompts.intent_parser import build_intent_prompt


INTENT_CACHE_TTL = 86400  # 24h — Intent ist deterministisch je Query


def _hash_key(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"llm:{prefix}:{digest}"


class LLMService:

    def __init__(self):
        self.router = LLMRouter()
        self.cache = CacheService()

    async def parse_intent(self, query: str) -> UserIntent:
        """Extrahiert strukturierte Daten aus natürlichsprachlicher Anfrage."""
        normalized = query.strip().lower()
        # Datum in den Cache-Key, damit "morgen"/"heute Abend" nicht mit
        # gestrigem Kalender beantwortet wird.
        today = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
        cache_key = _hash_key("intent", today, normalized)

        cached = await self.cache.get(cache_key)
        if cached is not None:
            try:
                return UserIntent(**cached)
            except Exception as e:
                logger.warning(f"Cached intent invalid, ignoring: {e}")

        try:
            provider = await self.router.get_provider()
        except RuntimeError as e:
            logger.warning(f"No LLM provider for intent parsing: {e}")
            return UserIntent()

        prompt = build_intent_prompt(query)

        try:
            response = await provider.complete(
                system=(
                    "Du bist ein Transit-Assistent für Deutschland. "
                    "Extrahiere aus der Nutzeranfrage: Abfahrtsort, Zielort, "
                    "Abfahrtszeit ODER Ankunftszeit, Budget, Präferenzen. "
                    "Beachte die Wochentag-Tabelle im Prompt penibel. "
                    "Antworte NUR mit validem JSON. Keine Erklärungen."
                ),
                user=prompt,
                max_tokens=384,
            )
            data = json.loads(response)
            intent = UserIntent(**data)
            await self.cache.set(cache_key, intent, ttl=INTENT_CACHE_TTL)
            return intent
        except json.JSONDecodeError:
            logger.warning(f"LLM returned invalid JSON for intent parsing: {query}")
            return UserIntent()
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            return UserIntent()

