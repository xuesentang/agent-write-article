"""
SSE 流式接口路由
处理 Server-Sent Events 连接和消息推送
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.utils.database import get_db
from app.utils.sse_manager import sse_manager
from app.schemas.response import ApiResponse
from app.services.task_repository import TaskRepository


router = APIRouter()


@router.get("/sse/connect/{task_id}", summary="建立 SSE 连接")
async def sse_connect(task_id: str):
    """
    建立 SSE 连接

    客户端通过此接口建立 SSE 连接，接收任务相关的实时事件推送。

    - **task_id**: 任务唯一标识

    SSE 事件格式：
    ```
    event: {事件类型}
    data: {JSON数据}
    id: {消息序号}
    ```

    支持的事件类型：
    - status: 任务状态变更
    - title_chunk: 标题生成片段
    - title_complete: 标题生成完成
    - outline_chunk: 大纲生成片段
    - outline_complete: 大纲生成完成
    - content_chunk: 正文生成片段
    - image_progress: 配图生成进度
    - image_complete: 配图完成
    - error: 错误信息
    - done: 任务完成
    - heartbeat: 心跳（每 30 秒）
    """

    async def event_generator():
        """事件生成器"""
        async with sse_manager.create_connection(task_id) as conn:
            async for event in conn.receive():
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/sse/status", summary="获取 SSE 连接状态")
async def sse_status():
    """
    获取当前 SSE 连接状态

    返回当前活跃的连接数量和任务列表。
    """
    return ApiResponse.ok(
        data={
            "connection_count": sse_manager.get_connection_count(),
            "active_tasks": sse_manager.get_active_tasks(),
        },
        message="SSE 连接状态",
    )


# ============ 测试端点 ============


@router.get("/sse/test/{task_id}", summary="SSE 测试端点")
async def sse_test(task_id: str):
    """
    SSE 测试端点

    每秒推送一条模拟消息，用于验证 SSE 通信是否正常。

    **测试正常的标志**：
    1. 前端能连续收到 10 条消息
    2. 最后一条消息的事件类型为 `done`
    3. 最后一条消息的 data 包含 `test_passed: true`

    推送的消息序列：
    - 3 条 status 事件（模拟状态变更）
    - 3 条 progress 事件（模拟进度更新）
    - 1 条 content_chunk 事件（模拟内容片段）
    - 1 条 error 事件（模拟错误，可忽略）
    - 1 条 status 事件（恢复正常）
    - 1 条 done 事件（测试完成标志）
    """

    async def test_generator():
        """测试事件生成器"""
        import json
        from datetime import datetime

        # 定义测试事件序列
        test_events = [
            # 1. 状态变更
            {
                "event": "status",
                "data": {
                    "status": "TEST_STARTED",
                    "message": "SSE 测试开始",
                },
                "progress": 0,
            },
            # 2. 进度更新 1
            {
                "event": "progress",
                "stage": "title",
                "data": {"step": 1, "total": 10},
                "progress": 10,
                "message": "测试进度: 10%",
            },
            # 3. 内容片段
            {
                "event": "content_chunk",
                "stage": "content",
                "data": {"content": "这是一条测试内容片段"},
                "progress": 20,
            },
            # 4. 进度更新 2
            {
                "event": "progress",
                "stage": "outline",
                "data": {"step": 3, "total": 10},
                "progress": 40,
                "message": "测试进度: 40%",
            },
            # 5. 图片进度
            {
                "event": "image_progress",
                "stage": "image",
                "data": {
                    "position": "para_1",
                    "status": "generating",
                    "provider": "test_provider",
                },
                "progress": 50,
            },
            # 6. 进度更新 3
            {
                "event": "progress",
                "stage": "image",
                "data": {"step": 6, "total": 10},
                "progress": 60,
                "message": "测试进度: 60%",
            },
            # 7. 图片完成
            {
                "event": "image_complete",
                "stage": "image",
                "data": {
                    "position": "para_1",
                    "url": "https://example.com/test-image.jpg",
                    "source": "test",
                },
                "progress": 70,
            },
            # 8. 进度更新 4
            {
                "event": "progress",
                "data": {"step": 8, "total": 10},
                "progress": 80,
                "message": "测试进度: 80%",
            },
            # 9. 状态变更
            {
                "event": "status",
                "data": {
                    "status": "TEST_FINISHING",
                    "message": "SSE 测试即将完成",
                },
                "progress": 90,
            },
            # 10. 完成（关键：测试通过的标志）
            {
                "event": "done",
                "data": {
                    "article_id": "test-article-id",
                    "test_passed": True,  # 这是最重要的标志
                    "message": "SSE 测试成功完成！共发送 10 条消息",
                    "total_messages": 10,
                },
                "progress": 100,
                "message": "测试完成",
            },
        ]

        # 逐条发送事件
        for i, event in enumerate(test_events, 1):
            lines = [f"event: {event['event']}"]

            # 构建完整的数据对象
            full_data = {
                "event": event["event"],
                "stage": event.get("stage"),
                "data": event["data"],
                "progress": event.get("progress", 0),
                "message": event.get("message"),
                "timestamp": datetime.now().isoformat(),
                "sequence": i,  # 消息序号
                "total": len(test_events),
            }

            lines.append(f"data: {json.dumps(full_data, ensure_ascii=False)}")
            lines.append(f"id: {i}")

            yield "\n".join(lines) + "\n\n"

            # 每秒发送一条
            await asyncio.sleep(1)

    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/sse/send/{task_id}", summary="手动发送 SSE 事件（测试用）")
async def sse_send(
    task_id: str,
    event_type: str = Query(..., description="事件类型"),
    message: str = Query(..., description="消息内容"),
    progress: int = Query(default=0, ge=0, le=100, description="进度"),
):
    """
    手动发送 SSE 事件（测试用）

    用于测试 SSE 连接是否正常工作。

    - **task_id**: 任务 ID
    - **event_type**: 事件类型（status/progress/content_chunk/error/done）
    - **message**: 消息内容
    - **progress**: 进度百分比
    """
    from app.schemas.sse import SSEEventType

    # 验证事件类型
    try:
        event_enum = SSEEventType(event_type)
    except ValueError:
        return ApiResponse.error(
            code="1002",
            message=f"无效的事件类型: {event_type}。支持的类型: {[e.value for e in SSEEventType]}",
        )

    # 检查连接是否存在
    if not await sse_manager.get_connection(task_id):
        return ApiResponse.error(
            code="1600",
            message=f"SSE 连接不存在: task_id={task_id}。请先调用 /api/sse/connect/{task_id} 建立连接。",
        )

    # 发送事件
    success = await sse_manager.send_event(
        task_id=task_id,
        event_type=event_enum,
        data={"message": message},
        progress=progress,
        message=message,
    )

    if success:
        return ApiResponse.ok(
            data={
                "task_id": task_id,
                "event_type": event_type,
                "message": message,
                "progress": progress,
            },
            message="事件发送成功",
        )
    else:
        return ApiResponse.error(
            code="1602",
            message="事件发送失败",
        )