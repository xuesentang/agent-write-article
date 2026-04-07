"""
健康检查路由
用于验证服务是否正常运行，以及 SSE 连接测试
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

from app.schemas.response import ApiResponse
from app.config import settings


router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return ApiResponse.ok(
        data={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
        message="服务运行正常",
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