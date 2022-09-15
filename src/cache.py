import json
import logging
import aioredis
from aioredis import Redis

from src.config import settings

logger = logging.getLogger("events")


class RedisCache:
    redis: Redis

    async def set(self, cache_key, data):
        await self.redis.set(cache_key, json.dumps(data))

    async def get(self, cache_key):
        raw_data = await self.redis.get(cache_key)
        if raw_data:
            return json.loads(raw_data.decode("utf-8"))
        return None

    async def change_value(self, cache_key, key, value):
        raw_data = await self.redis.get(cache_key)
        if raw_data:
            data = json.loads(raw_data.decode("utf-8"))
            data[key] = value
            await self.redis.set(cache_key, json.dumps(data))
            return data
        return None

    async def get_value(self, cache_key, key):
        raw_data = await self.redis.get(cache_key)
        if raw_data:
            data = json.loads(raw_data.decode("utf-8"))
            return data.get(key)
        return None


cache = RedisCache()


async def connect_cache():
    logger.info("Connecting to Redis")
    cache.redis = await aioredis.from_url(settings.REDIS_URL)
    logger.info("Connected to Redis")


async def disconnect_cache():
    logger.info("Disconnecting from Redis")
    await cache.redis.close()
