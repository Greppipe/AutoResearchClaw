from __future__ import annotations

import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings


_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def cache_set(key: str, value: Any, ttl: int = None) -> None:
    r = await get_redis()
    ttl = ttl or settings.REDIS_CACHE_TTL
    await r.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def publish_event(channel: str, event: dict) -> None:
    r = await get_redis()
    await r.publish(channel, json.dumps(event))
