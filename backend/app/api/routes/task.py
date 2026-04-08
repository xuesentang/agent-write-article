"""
任务管理路由
提供任务的 CRUD 操作接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.utils.database import get_db
from app.utils.sse_manager import sse_manager
from app.schemas.response import ApiResponse, PagedResponse
from app.schemas.task import (
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse,
    TaskUpdateStatusRequest,
    TaskStatusEnum,
    SelectTitleRequest,
    GenerateOutlineRequest,
    OptimizeOutlineRequest,
    SaveOutlineRequest,
    ConfirmOutlineRequest,
)
from app.services.task_repository import TaskRepository
from app.services.article_repository import ArticleRepository
from app.models.task import Task, TaskStatus
from app.agents import (
    TitleAgent,
    TitleAgentInput,
    OutlineAgent,
    OutlineAgentInput,
    ContentAgent,
    ContentAgentInput,
)


logger = logging.getLogger(__name__)


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


# ============ 大纲生成辅助函数 ============


async def _generate_content_task(
    task_id: str,
    selected_title: str,
    outline: dict,
    style: str,
    extra_description: Optional[str],
    use_mock: bool = False,
):
    """
    后台任务：生成正文

    Args:
        task_id: 任务 ID
        selected_title: 选定的标题
        outline: 确认后的文章大纲
        style: 文章风格
        extra_description: 补充描述（作为额外上下文）
        use_mock: 是否使用 mock LLM
    """
    from app.utils.database import async_session_factory

    try:
        # 创建正文智能体
        agent = ContentAgent(use_mock=use_mock)

        # 定义 SSE 流式回调
        async def stream_callback(content: str):
            await sse_manager.send_content_chunk(
                task_id=task_id,
                content=content,
                progress=55,
            )

        # 执行正文生成
        input_data = ContentAgentInput(
            selected_title=selected_title,
            outline=outline,
            style=style,
            extra_context=extra_description,
        )

        output = await agent.execute(input_data, stream_callback=stream_callback)

        # 更新数据库状态
        async with async_session_factory() as db:
            article_repo = ArticleRepository(db)
            task_repo = TaskRepository(db)

            # 更新文章正文
            article = await article_repo.get_by_task_id(task_id)
            if article:
                # 保存正文和字数统计
                await article_repo.update_content(
                    article_id=article.id,
                    content=output.content,
                    word_count=str(output.word_count),
                )

            # 更新状态为 CONTENT_GENERATED（暂时使用 OUTLINE_READY 表示正文完成）
            # 注意：后续流程会触发配图生成，状态将变为 IMAGE_GENERATING
            await task_repo.update_status(
                task_id=task_id,
                status=TaskStatus.CONTENT_GENERATING,
                status_message="正文生成完成，准备生成配图",
                progress="60",
            )

            # 发送正文完成事件
            await sse_manager.send_content_complete(
                task_id=task_id,
                content=output.content,
                word_count=output.word_count,
                image_count=len(output.image_placeholders),
                progress=60,
            )

            # 发送状态更新事件
            await sse_manager.send_status(
                task_id=task_id,
                status=TaskStatus.CONTENT_GENERATING.value,
                message="正文生成完成",
                progress=60,
            )

            logger.info(
                f"[ContentTask] 正文生成完成: task_id={task_id}, "
                f"word_count={output.word_count}, image_count={len(output.image_placeholders)}"
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
            code="CONTENT_GENERATION_ERROR",
            message="正文生成失败",
            details=str(e),
        )


async def _generate_outline_task(
    task_id: str,
    selected_title: str,
    topic: str,
    style: str,
    extra_description: Optional[str],
    target_length: int,
    use_mock: bool = False,
):
    """
    后台任务：生成大纲

    Args:
        task_id: 任务 ID
        selected_title: 用户选择的标题
        topic: 原始选题
        style: 文章风格
        extra_description: 补充描述
        target_length: 目标字数
        use_mock: 是否使用 mock LLM
    """
    from app.utils.database import async_session_factory

    try:
        # 创建大纲智能体
        agent = OutlineAgent(use_mock=use_mock)

        # 定义 SSE 流式回调
        async def stream_callback(content: str):
            await sse_manager.send_outline_chunk(
                task_id=task_id,
                content=content,
                progress=35,
            )

        # 执行大纲生成
        input_data = OutlineAgentInput(
            selected_title=selected_title,
            topic=topic,
            style=style,
            target_length=target_length,
            extra_description=extra_description,
        )

        output = await agent.execute(input_data, stream_callback=stream_callback)

        # 更新数据库状态
        async with async_session_factory() as db:
            article_repo = ArticleRepository(db)
            task_repo = TaskRepository(db)

            # 更新文章大纲
            article = await article_repo.get_by_task_id(task_id)
            if article:
                await article_repo.update_outline(
                    article_id=article.id,
                    outline=output.outline.model_dump(),
                )

            # 更新状态为 OUTLINE_READY
            await task_repo.update_status(
                task_id=task_id,
                status=TaskStatus.OUTLINE_READY,
                status_message="大纲生成完成，请确认或编辑",
                progress="40",
            )

            # 发送大纲完成事件
            await sse_manager.send_outline_complete(
                task_id=task_id,
                outline=output.outline.model_dump(),
                progress=40,
            )

            # 发送状态更新事件
            await sse_manager.send_status(
                task_id=task_id,
                status=TaskStatus.OUTLINE_READY.value,
                message="大纲生成完成，请确认或编辑",
                progress=40,
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
            code="OUTLINE_GENERATION_ERROR",
            message="大纲生成失败",
            details=str(e),
        )


async def _optimize_outline_task(
    task_id: str,
    selected_title: str,
    style: str,
    current_outline: Dict[str, Any],
    user_modifications: str,
    use_mock: bool = False,
):
    """
    后台任务：优化大纲

    Args:
        task_id: 任务 ID
        selected_title: 用户选择的标题
        style: 文章风格
        current_outline: 当前大纲
        user_modifications: 用户修改建议
        use_mock: 是否使用 mock LLM
    """
    from app.utils.database import async_session_factory

    try:
        # 创建大纲智能体
        agent = OutlineAgent(use_mock=use_mock)

        # 定义 SSE 流式回调
        async def stream_callback(content: str):
            await sse_manager.send_outline_chunk(
                task_id=task_id,
                content=content,
                progress=45,
            )

        # 执行大纲优化
        input_data = OutlineAgentInput(
            selected_title=selected_title,
            topic="",  # 优化模式不需要 topic
            style=style,
            optimize_mode=True,
            current_outline=current_outline,
            user_modifications=user_modifications,
        )

        output = await agent.execute(input_data, stream_callback=stream_callback)

        # 更新数据库状态
        async with async_session_factory() as db:
            article_repo = ArticleRepository(db)
            task_repo = TaskRepository(db)

            # 更新文章大纲
            article = await article_repo.get_by_task_id(task_id)
            if article:
                await article_repo.update_outline(
                    article_id=article.id,
                    outline=output.outline.model_dump(),
                )

            # 更新状态为 OUTLINE_READY
            await task_repo.update_status(
                task_id=task_id,
                status=TaskStatus.OUTLINE_READY,
                status_message="大纲优化完成",
                progress="45",
            )

            # 发送大纲完成事件
            await sse_manager.send_outline_complete(
                task_id=task_id,
                outline=output.outline.model_dump(),
                progress=45,
            )

            # 发送状态更新事件
            await sse_manager.send_status(
                task_id=task_id,
                status=TaskStatus.OUTLINE_READY.value,
                message="大纲优化完成",
                progress=45,
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
            code="OUTLINE_OPTIMIZATION_ERROR",
            message="大纲优化失败",
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


# ============ 大纲相关接口 ============


@router.post("/tasks/{task_id}/select-title", summary="选择标题")
async def select_title(
    task_id: str,
    request: SelectTitleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户选择标题

    用户从生成的标题方案中选择一个标题，触发后续大纲生成流程。

    - **task_id**: 任务唯一标识
    - **selected_title**: 用户选定的标题

    使用流程：
    1. 调用 POST /api/tasks/{task_id}/generate-titles 获取标题方案
    2. 用户选择一个标题后调用此接口
    3. 调用 POST /api/tasks/{task_id}/generate-outline 生成大纲
    """
    task_repo = TaskRepository(db)
    task = await task_repo.get(task_id)

    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态
    if task.status != TaskStatus.TITLE_READY:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许选择标题：当前状态={task.status.value}，需要 TITLE_READY",
        )

    # 更新文章记录
    article_repo = ArticleRepository(db)
    article = await article_repo.get_by_task_id(task_id)

    if not article:
        # 如果文章不存在，创建一条记录
        article = await article_repo.create({
            "task_id": task_id,
            "selected_title": request.selected_title,
        })
    else:
        # 更新选定的标题
        await article_repo.select_title(article.id, request.selected_title)

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "selected_title": request.selected_title,
            "message": "标题选择成功，请调用 generate-outline 接口生成大纲",
        },
        message="标题选择成功",
    )


@router.post("/tasks/{task_id}/generate-outline", summary="触发大纲生成")
async def generate_outline(
    task_id: str,
    background_tasks: BackgroundTasks,
    request: GenerateOutlineRequest = None,
    use_mock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    触发大纲生成任务

    此接口会启动后台任务生成文章大纲，通过 SSE 推送进度和结果。
    复用标题生成的 SSE 连接端点，通过 stage 字段区分当前阶段。

    - **task_id**: 任务唯一标识
    - **target_length**: 目标字数（可选，默认 2000）
    - **use_mock**: 是否使用 mock LLM（测试用，默认 false）

    SSE 事件序列：
    - outline_chunk: 大纲内容片段（多次）
    - outline_complete: 大纲生成完成，包含结构化大纲
    - status: 状态更新为 OUTLINE_READY
    """
    task_repo = TaskRepository(db)
    article_repo = ArticleRepository(db)

    task = await task_repo.get(task_id)
    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态
    if task.status != TaskStatus.TITLE_READY:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成大纲：当前状态={task.status.value}，需要 TITLE_READY",
        )

    # 获取文章记录，检查是否已选择标题
    article = await article_repo.get_by_task_id(task_id)
    if not article or not article.selected_title:
        return ApiResponse.error(
            code="1202",
            message="请先选择标题后再生成大纲",
        )

    # 获取目标字数
    target_length = request.target_length if request else 2000

    # 更新状态为 OUTLINE_GENERATING
    await task_repo.update_status(
        task_id=task_id,
        status=TaskStatus.OUTLINE_GENERATING,
        status_message="正在生成大纲...",
        progress="30",
    )

    # 发送状态变更事件（如果有 SSE 连接）
    await sse_manager.send_status(
        task_id=task_id,
        status=TaskStatus.OUTLINE_GENERATING.value,
        message="正在生成大纲...",
        progress=30,
    )

    # 启动后台任务
    background_tasks.add_task(
        _generate_outline_task,
        task_id,
        article.selected_title,
        task.topic,
        task.style,
        task.extra_description,
        target_length,
        use_mock,
    )

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "status": TaskStatus.OUTLINE_GENERATING.value,
            "stage": "outline",
            "message": "大纲生成任务已启动，请通过 SSE 接收结果",
        },
        message="大纲生成任务已启动",
    )


@router.post("/tasks/{task_id}/optimize-outline", summary="优化大纲")
async def optimize_outline(
    task_id: str,
    background_tasks: BackgroundTasks,
    request: OptimizeOutlineRequest,
    use_mock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    优化大纲

    用户提供修改建议后，对现有大纲进行优化。
    复用标题生成的 SSE 连接端点，通过 stage 字段区分当前阶段。

    - **task_id**: 任务唯一标识
    - **user_modifications**: 用户修改建议
    - **use_mock**: 是否使用 mock LLM（测试用，默认 false）

    SSE 事件序列：
    - outline_chunk: 大纲内容片段（多次）
    - outline_complete: 大纲优化完成，包含新的结构化大纲
    - status: 状态更新为 OUTLINE_READY
    """
    task_repo = TaskRepository(db)
    article_repo = ArticleRepository(db)

    task = await task_repo.get(task_id)
    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态（大纲生成中或大纲就绪都可以优化）
    if task.status not in [TaskStatus.OUTLINE_GENERATING, TaskStatus.OUTLINE_READY]:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许优化大纲：当前状态={task.status.value}",
        )

    # 获取文章记录，检查是否已有大纲
    article = await article_repo.get_by_task_id(task_id)
    if not article or not article.outline:
        return ApiResponse.error(
            code="1202",
            message="请先生成大纲后再进行优化",
        )

    # 更新状态为 OUTLINE_GENERATING（优化中）
    await task_repo.update_status(
        task_id=task_id,
        status=TaskStatus.OUTLINE_GENERATING,
        status_message="正在优化大纲...",
        progress="42",
    )

    # 发送状态变更事件（如果有 SSE 连接）
    await sse_manager.send_status(
        task_id=task_id,
        status=TaskStatus.OUTLINE_GENERATING.value,
        message="正在优化大纲...",
        progress=42,
    )

    # 启动后台任务
    background_tasks.add_task(
        _optimize_outline_task,
        task_id,
        article.selected_title,
        task.style,
        article.outline,
        request.user_modifications,
        use_mock,
    )

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "status": TaskStatus.OUTLINE_GENERATING.value,
            "stage": "outline",
            "message": "大纲优化任务已启动，请通过 SSE 接收结果",
        },
        message="大纲优化任务已启动",
    )


@router.put("/tasks/{task_id}/outline", summary="保存大纲")
async def save_outline(
    task_id: str,
    request: SaveOutlineRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户直接保存编辑后的大纲

    用户在编辑器中修改大纲后，直接保存到数据库。
    不会触发 LLM 生成，直接保存用户编辑的内容。

    - **task_id**: 任务唯一标识
    - **outline**: 用户编辑的大纲结构数据
    """
    task_repo = TaskRepository(db)
    article_repo = ArticleRepository(db)

    task = await task_repo.get(task_id)
    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态
    if task.status != TaskStatus.OUTLINE_READY:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许保存大纲：当前状态={task.status.value}，需要 OUTLINE_READY",
        )

    # 更新文章大纲
    article = await article_repo.get_by_task_id(task_id)
    if not article:
        return ApiResponse.error(code="1202", message="文章记录不存在")

    await article_repo.update_outline(article.id, request.outline)

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "outline": request.outline,
        },
        message="大纲保存成功",
    )


# ============ 正文生成接口 ============


@router.post("/tasks/{task_id}/confirm-outline", summary="确认大纲并触发正文生成")
async def confirm_outline(
    task_id: str,
    background_tasks: BackgroundTasks,
    request: ConfirmOutlineRequest = None,
    use_mock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    确认大纲，触发正文生成

    用户确认大纲后，启动正文生成任务。正文将通过 SSE 实时推送，
    用户可以在前端看到文字逐渐出现的效果。

    - **task_id**: 任务唯一标识
    - **outline**: 用户编辑后的大纲（可选，不传则使用已有大纲）
    - **use_mock**: 是否使用 mock LLM（测试用，默认 false）

    SSE 事件序列：
    - content_chunk: 正文内容片段（多次，实时推送）
    - content_complete: 正文生成完成，包含完整正文和字数统计
    - status: 状态更新为 CONTENT_GENERATING

    使用流程：
    1. 调用 POST /api/tasks/{task_id}/generate-outline 获取大纲
    2. 用户确认或编辑大纲后调用此接口
    3. 通过 SSE 接收正文生成进度和结果
    """
    task_repo = TaskRepository(db)
    article_repo = ArticleRepository(db)

    task = await task_repo.get(task_id)
    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态
    if task.status != TaskStatus.OUTLINE_READY:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成正文：当前状态={task.status.value}，需要 OUTLINE_READY",
        )

    # 获取文章记录
    article = await article_repo.get_by_task_id(task_id)
    if not article or not article.selected_title:
        return ApiResponse.error(
            code="1202",
            message="请先选择标题后再生成正文",
        )

    # 获取大纲（优先使用请求中的大纲，否则使用已有大纲）
    outline = request.outline if request and request.outline else article.outline
    if not outline:
        return ApiResponse.error(
            code="1203",
            message="大纲不存在，请先生成或保存大纲",
        )

    # 如果请求中提供了新大纲，先更新数据库
    if request and request.outline:
        await article_repo.update_outline(article.id, request.outline)

    # 更新状态为 CONTENT_GENERATING
    await task_repo.update_status(
        task_id=task_id,
        status=TaskStatus.CONTENT_GENERATING,
        status_message="正在生成正文...",
        progress="50",
    )

    # 发送状态变更事件（如果有 SSE 连接）
    await sse_manager.send_status(
        task_id=task_id,
        status=TaskStatus.CONTENT_GENERATING.value,
        message="正在生成正文...",
        progress=50,
    )

    # 启动后台任务
    background_tasks.add_task(
        _generate_content_task,
        task_id,
        article.selected_title,
        outline,
        task.style,
        task.extra_description,
        use_mock,
    )

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "status": TaskStatus.CONTENT_GENERATING.value,
            "stage": "content",
            "message": "正文生成任务已启动，请通过 SSE 接收结果",
        },
        message="正文生成任务已启动",
    )