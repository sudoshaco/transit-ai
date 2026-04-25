import json
import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise
        return self._redis

    async def get(self, key: str) -> Optional[dict]:
        try:
            r = await self._get_redis()
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
        return None

    async def set(self, key: str, value, ttl: int = 300) -> None:
        try:
            r = await self._get_redis()
            if hasattr(value, "model_dump"):
                data = json.dumps(value.model_dump(), default=str)
            else:
                data = json.dumps(value, default=str)
            await r.set(key, data, ex=ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")

    async def delete(self, key: str) -> None:
        try:
            r = await self._get_redis()
            await r.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
