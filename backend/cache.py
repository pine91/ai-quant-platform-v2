"""Optional short-lived candle cache. Redis downtime falls back to the provider."""
import json
import os

from redis.asyncio import Redis
from redis.exceptions import RedisError


async def cached_candles(key, load):
    url = os.getenv("REDIS_URL")
    if not url:
        return await load()
    async with Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5) as redis:
        try:
            cached = await redis.get(key)
            if cached is not None:
                return json.loads(cached)
        except (RedisError, ValueError):
            pass
        rows = await load()
        if rows:
            try:
                await redis.set(key, json.dumps(rows), ex=30)
            except RedisError:
                pass
        return rows
