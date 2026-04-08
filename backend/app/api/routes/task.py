"""
任务管理路由
提供任务的 CRUD 操作接口
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.utils.database import get_db
from app.utils.sse_manager import sse_manager
from app.schemas.response import ApiResponse, PagedResponse
from app.schemas.task import (
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse,
    TaskUpdateStatusRequest,
    TaskStatusEnum,
)
from app.services.task_repository import TaskRepository
from app.models.task import Task, TaskStatus
from app.agents import TitleAgent, TitleAgentInput


router = APIRouter()


# ============ 标题生成辅助函数 ============


async def _generate_titles_task(
    task_id: str,
    topic: str,
    style: str,
    extra_description: Optional[str],
    use_mock: bool = False,
):
    """
    后台任务：生成标题

    Args:
        task_id: 任务 ID
        topic: 选题
        style: 文章风格
        extra_description: 补充描述
        use_mock: 是否使用 mock LLM
    """
    from app.utils.database import async_session_factory

    try:
        # 创建标题智能体
        agent = TitleAgent(use_mock=use_mock)

        # 定义 SSE 流式回调
        async def stream_callback(content: str):
            await sse_manager.send_title_chunk(
                task_id=task_id,
                content=content,
                index=0,  # 统一使用 index=0，前端解析整体内容
                progress=10,
            )

        # 执行标题生成
        input_data = TitleAgentInput(
            topic=topic,
            style=style,
            extra_description=extra_description,
            count=5,
        )

        output = await agent.execute(input_data, stream_callback=stream_callback)

        # 更新数据库状态
        async with async_session_factory() as db:
            repo = TaskRepository(db)

            # 提取标题列表
            titles = [t.title for t in output.titles]

            # 更新状态为 TITLE_READY
            await repo.update_status(
                task_id=task_id,
                status=TaskStatus.TITLE_READY,
                status_message="标题生成完成，请选择标题",
                progress="20",
            )

            # 发送标题完成事件
            await sse_manager.send_title_complete(
                task_id=task_id,
                titles=titles,
                progress=20,
            )

            # 发送状态更新事件
            await sse_manager.send_status(
                task_id=task_id,
                status=TaskStatus.TITLE_READY.value,
                message="标题生成完成，请选择标题",
                progress=20,
            )

    except Exception as e:
        # 错误处理
        from app.utils.database import async_session_factory

        async with async_session_factory() as db:
            repo = TaskRepository(db)
            await repo.set_error(task_id, str(e))

        # 发送错误事件
        await sse_manager.send_error(
            task_id=task_id,
            code="TITLE_GENERATION_ERROR",
            message="标题生成失败",
            details=str(e),
        )


# ============ API 端点 ============


@router.post("/tasks", summary="创建任务")
async def create_task(
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新的文章生成任务

    - **topic**: 用户输入的选题描述
    - **style**: 文章风格（专业/轻松/幽默/深度/热点/教程）
    - **extra_description**: 补充描述（可选）
    """
    repo = TaskRepository(db)
    task = await repo.create(
        {
            "topic": request.topic,
            "style": request.style,
            "extra_description": request.extra_description,
            "status": TaskStatus.CREATED,
            "status_message": "任务已创建，准备开始",
            "progress": "0",
        }
    )

    return ApiResponse.ok(
        data=TaskResponse(
            id=task.id,
            topic=task.topic,
            style=task.style,
            extra_description=task.extra_description,
            status=TaskStatusEnum(task.status.value),
            status_message=task.status_message,
            progress=task.progress,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        message="任务创建成功",
    )


@router.get("/tasks/{task_id}", summary="获取任务详情")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据 ID 获取任务详情

    - **task_id**: 任务唯一标识
    """
    repo = TaskRepository(db)
    task = await repo.get(task_id)

    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    return ApiResponse.ok(
        data=TaskResponse(
            id=task.id,
            topic=task.topic,
            style=task.style,
            extra_description=task.extra_description,
            status=TaskStatusEnum(task.status.value),
            status_message=task.status_message,
            progress=task.progress,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
    )


@router.get("/tasks", summary="获取任务列表")
async def list_tasks(
    page: int = 1,
    page_size: int = 10,
    status: Optional[TaskStatusEnum] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    分页获取任务列表

    - **page**: 页码（默认 1）
    - **page_size**: 每页数量（默认 10）
    - **status**: 按状态筛选（可选）
    """
    repo = TaskRepository(db)

    filters = None
    if status:
        filters = {"status": TaskStatus(status.value)}

    skip = (page - 1) * page_size
    tasks = await repo.get_multi(skip=skip, limit=page_size, filters=filters)
    total = await repo.count(filters=filters)

    items = [
        TaskResponse(
            id=task.id,
            topic=task.topic,
            style=task.style,
            extra_description=task.extra_description,
            status=TaskStatusEnum(task.status.value),
            status_message=task.status_message,
            progress=task.progress,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]

    return PagedResponse.ok(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/tasks/{task_id}/status", summary="更新任务状态")
async def update_task_status(
    task_id: str,
    request: TaskUpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新任务状态

    - **task_id**: 任务唯一标识
    - **status**: 新状态
    - **status_message**: 状态消息（可选）
    - **progress**: 进度百分比（可选）
    """
    repo = TaskRepository(db)
    task = await repo.update_status(
        task_id=task_id,
        status=TaskStatus(request.status.value),
        status_message=request.status_message,
        progress=request.progress,
    )

    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    return ApiResponse.ok(
        data=TaskResponse(
            id=task.id,
            topic=task.topic,
            style=task.style,
            extra_description=task.extra_description,
            status=TaskStatusEnum(task.status.value),
            status_message=task.status_message,
            progress=task.progress,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        message="状态更新成功",
    )


@router.delete("/tasks/{task_id}", summary="删除任务")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除任务及其关联的文章

    - **task_id**: 任务唯一标识
    """
    repo = TaskRepository(db)
    success = await repo.delete(task_id)

    if not success:
        return ApiResponse.error(code="1200", message="任务不存在")

    return ApiResponse.ok(message="任务删除成功")


@router.get("/tasks/in-progress", summary="获取进行中的任务")
async def get_in_progress_tasks(
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有正在进行的任务

    包括状态为生成中的所有任务。
    """
    repo = TaskRepository(db)
    tasks = await repo.get_in_progress()

    items = [
        TaskResponse(
            id=task.id,
            topic=task.topic,
            style=task.style,
            extra_description=task.extra_description,
            status=TaskStatusEnum(task.status.value),
            status_message=task.status_message,
            progress=task.progress,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]

    return ApiResponse.ok(data=items, message=f"当前有 {len(items)} 个任务进行中")


# ============ 标题生成接口 ============


@router.post("/tasks/{task_id}/generate-titles", summary="触发标题生成")
async def generate_titles(
    task_id: str,
    background_tasks: BackgroundTasks,
    use_mock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    触发标题生成任务

    此接口会启动后台任务生成标题，通过 SSE 推送进度和结果。

    - **task_id**: 任务唯一标识
    - **use_mock**: 是否使用 mock LLM（测试用，默认 false）

    使用流程：
    1. 先调用 POST /api/tasks 创建任务获取 task_id
    2. 建立 SSE 连接 GET /api/sse/connect/{task_id}
    3. 调用此接口触发标题生成
    4. 通过 SSE 接收标题生成进度和结果

    SSE 事件序列：
    - title_chunk: 标题内容片段（多次）
    - title_complete: 标题生成完成，包含完整标题列表
    - status: 状态更新为 TITLE_READY
    """
    repo = TaskRepository(db)
    task = await repo.get(task_id)

    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态
    if task.status not in [TaskStatus.CREATED, TaskStatus.FAILED]:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成标题：当前状态={task.status.value}",
        )

    # 更新状态为 TITLE_GENERATING
    await repo.update_status(
        task_id=task_id,
        status=TaskStatus.TITLE_GENERATING,
        status_message="正在生成标题...",
        progress="5",
    )

    # 发送状态变更事件（如果有 SSE 连接）
    await sse_manager.send_status(
        task_id=task_id,
        status=TaskStatus.TITLE_GENERATING.value,
        message="正在生成标题...",
        progress=5,
    )

    # 启动后台任务
    background_tasks.add_task(
        _generate_titles_task,
        task_id,
        task.topic,
        task.style,
        task.extra_description,
        use_mock,
    )

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "status": TaskStatus.TITLE_GENERATING.value,
            "message": "标题生成任务已启动，请通过 SSE 接收结果",
        },
        message="标题生成任务已启动",
    )


@router.get("/tasks/{task_id}/stream", summary="获取任务 SSE 流")
async def get_task_stream(task_id: str):
    """
    获取任务的 SSE 流式连接端点

    此端点与 /api/sse/connect/{task_id} 功能相同，
    为了方便使用，提供了这个别名端点。

    - **task_id**: 任务唯一标识

    使用方式：
    前端使用 EventSource 连接此端点接收实时事件。
    """
    from fastapi.responses import StreamingResponse

    async def event_generator():
        async with sse_manager.create_connection(task_id) as conn:
            async for event in conn.receive():
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )