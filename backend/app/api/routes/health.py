"""
健康检查路由
用于验证服务是否正常运行，以及数据库、Redis 等连接状态
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.schemas.response import ApiResponse
from app.config import settings
from app.utils.database import get_db, check_db_health
from app.utils.redis_client import RedisClient


router = APIRouter()


@router.get("/health")
async def health_check():
    """
    基础健康检查接口

    仅检查应用是否运行，不涉及外部依赖。
    """
    return ApiResponse.ok(
        data={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
        message="服务运行正常",
    )


@router.get("/health/full")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """
    完整健康检查接口

    检查所有依赖组件的状态：
    - 数据库连接
    - Redis 连接（可选）
    """
    # 检查数据库
    db_health = await check_db_health()

    # 检查 Redis（如果配置了）
    redis_health = {"status": "not_configured"}
    try:
        redis_client = await RedisClient.get_client()
        await redis_client.ping()
        redis_health = {"status": "healthy", "connected": True}
    except Exception as e:
        redis_health = {"status": "unhealthy", "error": str(e)}

    # 判断整体状态
    overall_healthy = db_health["status"] == "healthy"

    return ApiResponse.ok(
        data={
            "overall": overall_healthy,
            "components": {
                "database": db_health,
                "redis": redis_health,
            },
            "version": settings.APP_VERSION,
            "environment": "development" if settings.DEBUG else "production",
        },
        message="健康检查完成",
    )


@router.get("/health/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    """
    数据库健康检查接口

    详细检查数据库连接和表状态。
    """
    health_info = await check_db_health()

    if health_info["status"] == "healthy":
        return ApiResponse.ok(data=health_info, message="数据库连接正常")
    else:
        return ApiResponse.error(
            code="1701",
            message="数据库连接异常",
            data=health_info,
        )


@router.get("/sse-test")
async def sse_test():
    """SSE 流式推送测试接口"""

    async def generate_events():
        """生成 SSE 事件流"""
        for i in range(5):
            yield f"event: status\ndata: {{\"count\": {i}, \"message\": \"测试消息 {i}\"}}\nid: {i}\n\n"
            await asyncio.sleep(0.5)

        yield "event: done\ndata: {\"message\": \"SSE 测试完成\"}\nid: end\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )