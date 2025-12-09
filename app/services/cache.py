"""
Lightweight Redis cache helper.

Designed to be optional: if no REDIS_URL is provided, helpers are no-ops so
the app continues to function without Redis.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Optional

from redis.asyncio import Redis, from_url
import base64

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Optional[Redis]:
    """Create (or reuse) a Redis client if configured."""
    settings = get_settings()
    if not settings.redis_url:
        logger.info("Redis disabled: no redis_url configured")
        return None

    # Build connection URL (support optional TLS)
    url = settings.redis_url
    if settings.redis_tls and url.startswith("redis://"):
        url = url.replace("redis://", "rediss://", 1)

    client = from_url(url, encoding="utf-8", decode_responses=True)
    return client


async def cache_get_json(key: str) -> Optional[Any]:
    client = get_redis_client()
    if not client:
        return None
    try:
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as exc:  # pragma: no cover - best-effort cache
        logger.warning(f"Redis get failed for key={key}: {exc}")
        return None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    client = get_redis_client()
    if not client:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:  # pragma: no cover - best-effort cache
        logger.warning(f"Redis set failed for key={key}: {exc}")


async def cache_get_bytes(key: str) -> Optional[bytes]:
    client = get_redis_client()
    if not client:
        return None
    try:
        data = await client.get(key)
        if data is None:
            return None
        try:
            return base64.b64decode(data)
        except Exception:
            return None
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Redis get bytes failed for key={key}: {exc}")
        return None


async def cache_set_bytes(key: str, value: bytes, ttl: int) -> None:
    client = get_redis_client()
    if not client:
        return
    try:
        await client.set(key, base64.b64encode(value).decode("utf-8"), ex=ttl)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Redis set bytes failed for key={key}: {exc}")

