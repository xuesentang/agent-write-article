"""
Redis 客户端配置
用于 SSE 消息通道、任务状态缓存等
"""

import redis.asyncio as redis
from typing import Optional

from app.config import settings


class RedisClient:
    """Redis 客户端"""

    _client: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if cls._client is None:
            cls._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
        return cls._client

    @classmethod
    async def close(cls):
        """关闭 Redis 连接"""
        if cls._client:
            await cls._client.close()
            cls._client = None


async def get_redis() -> redis.Redis:
    """FastAPI 依赖注入：获取 Redis 客户端"""
    return await RedisClient.get_client()