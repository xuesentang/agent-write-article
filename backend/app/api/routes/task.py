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
    ImageAnalyzerAgent,
    ImageAnalyzerInput,
    ImageGeneratorAgent,
    ImageGeneratorInput,
    create_image_analyzer_agent,
    create_image_generator_agent,
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

    logger.info(f"[TitleTask] 开始生成标题: task_id={task_id}")

    try:
        # 创建标题智能体
        agent = TitleAgent(use_mock=use_mock)

        # 定义 SSE 流式回调
        async def stream_callback(content: str):
            logger.debug(f"[TitleTask] 发送 title_chunk: {content[:30]}...")
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
            logger.info(f"[TitleTask] 解析到 {len(titles)} 个标题: {titles}")

            # 更新状态为 TITLE_READY
            await repo.update_status(
                task_id=task_id,
                status=TaskStatus.TITLE_READY,
                status_message="标题生成完成，请选择标题",
                progress="20",
            )

            # 确保事务提交
            await db.commit()
            logger.info(f"[TitleTask] 数据库事务已提交，状态更新为 TITLE_READY")

            # 发送标题完成事件
            logger.info(f"[TitleTask] 准备发送 title_complete 事件")
            success = await sse_manager.send_title_complete(
                task_id=task_id,
                titles=titles,
                progress=20,
            )
            logger.info(f"[TitleTask] title_complete 发送结果: {success}")

            # 发送状态更新事件
            await sse_manager.send_status(
                task_id=task_id,
                status=TaskStatus.TITLE_READY.value,
                message="标题生成完成，请选择标题",
                progress=20,
            )
            logger.info(f"[TitleTask] 标题生成流程完成")

    except Exception as e:
        logger.error(f"[TitleTask] 标题生成失败: {e}", exc_info=True)
        # 错误处理
        from app.utils.database import async_session_factory

        async with async_session_factory() as db:
            repo = TaskRepository(db)
            await repo.set_error(task_id, str(e))
            await db.commit()

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

            # 更新状态为 CONTENT_READY（正文完成，等待配图）
            await task_repo.update_status(
                task_id=task_id,
                status=TaskStatus.CONTENT_READY,
                status_message="正文生成完成，准备生成配图",
                progress="60",
            )

            # 确保事务提交
            await db.commit()
            logger.info(f"[ContentTask] 数据库事务已提交，状态更新为 CONTENT_READY")

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
                status=TaskStatus.CONTENT_READY.value,
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
            await db.commit()

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
            logger.info(f"[OutlineTask] 查询文章记录: task_id={task_id}, article_exists={article is not None}")
            if article:
                logger.info(f"[OutlineTask] 文章ID: {article.id}, 正在保存大纲...")
                await article_repo.update_outline(
                    article_id=article.id,
                    outline=output.outline.model_dump(),
                )
                logger.info(f"[OutlineTask] 大纲已保存到数据库")
                # 确保提交
                await db.commit()
                logger.info(f"[OutlineTask] 数据库事务已提交")
            else:
                logger.warning(f"[OutlineTask] 文章记录不存在，无法保存大纲: task_id={task_id}")

            # 更新状态为 OUTLINE_READY
            await task_repo.update_status(
                task_id=task_id,
                status=TaskStatus.OUTLINE_READY,
                status_message="大纲生成完成，请确认或编辑",
                progress="40",
            )

            # 确保事务提交
            await db.commit()
            logger.info(f"[OutlineTask] 数据库事务已提交，状态更新为 OUTLINE_READY")

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
            await db.commit()

        # 发送错误事件
        await sse_manager.send_error(
            task_id=task_id,
            code="OUTLINE_GENERATION_ERROR",
            message="大纲生成失败",
            details=str(e),
        )


# ============ 配图生成辅助函数 ============


async def _generate_images_task(
    task_id: str,
    content: str,
    use_mock: bool = False,
):
    """
    后台任务：生成配图

    流程：
    1. ImageAnalyzerAgent 解析正文中的 IMAGE_PLACEHOLDER
    2. ImageGeneratorAgent 并行执行图片任务
    3. 更新文章正文（图文合并后的最终内容）
    4. 完成任务

    Args:
        task_id: 任务 ID
        content: 正文内容
        use_mock: 是否使用 mock 实现
    """
    from app.utils.database import async_session_factory

    logger.info(f"[ImageTask] 开始配图生成: task_id={task_id}, use_mock={use_mock}")
    logger.info(f"[ImageTask] 正文内容长度: {len(content)} 字符")

    # 调试：检查正文是否包含占位符
    import re
    placeholder_pattern = r'!\[IMAGE_PLACEHOLDER\]\([^)]+\)'
    placeholders_found = re.findall(placeholder_pattern, content)
    logger.info(f"[ImageTask] 正文中的占位符数量: {len(placeholders_found)}")
    if placeholders_found:
        logger.info(f"[ImageTask] 占位符示例: {placeholders_found[:3]}")

    try:
        # 1. 使用 ImageAnalyzerAgent 解析正文中的占位符
        logger.info(f"[ImageTask] 创建 ImageAnalyzerAgent...")
        analyzer_agent = create_image_analyzer_agent()

        logger.info(f"[ImageTask] 创建 ImageAnalyzerInput...")
        analyzer_input = ImageAnalyzerInput(content=content)

        logger.info(f"[ImageTask] 执行 analyzer_agent.execute()...")
        analyzer_output = await analyzer_agent.execute(analyzer_input)

        logger.info(f"[ImageTask] 分析完成: totalCount={analyzer_output.totalCount}")

        logger.info(
            f"[ImageTask] 解析完成，发现 {analyzer_output.totalCount} 个图片任务"
        )

        # 2. 如果没有占位符，直接完成
        if analyzer_output.totalCount == 0:
            logger.info(f"[ImageTask] 正文无配图占位符，直接完成任务")

            async with async_session_factory() as db:
                article_repo = ArticleRepository(db)
                task_repo = TaskRepository(db)

                # 更新文章状态
                article = await article_repo.get_by_task_id(task_id)
                if article:
                    # 将正文作为最终输出
                    await article_repo.update_final_output(
                        article_id=article.id,
                        final_output=content,
                    )

                # 更新任务状态为完成
                await task_repo.update_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    status_message="文章创作完成（无配图）",
                    progress="100",
                )

                # 确保事务提交
                await db.commit()
                logger.info(f"[ImageTask] 数据库事务已提交（无配图情况）")

                # 发送完成事件（携带最终内容）
                await sse_manager.send_done(
                    task_id=task_id,
                    article_id=article.id if article else task_id,
                    final_output=content,
                )

                # 发送状态更新
                await sse_manager.send_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED.value,
                    message="文章创作完成",
                    progress=100,
                )

            return

        # 3. 使用 ImageGeneratorAgent 执行图片任务
        logger.info(f"[ImageTask] 创建 ImageGeneratorAgent, use_mock={use_mock}...")
        try:
            generator_agent = create_image_generator_agent(use_mock=use_mock)
            logger.info(f"[ImageTask] ImageGeneratorAgent 创建成功")
        except Exception as agent_error:
            logger.error(f"[ImageTask] 创建 ImageGeneratorAgent 失败: {agent_error}", exc_info=True)
            raise

        logger.info(f"[ImageTask] 创建 ImageGeneratorInput, tasks_count={len(analyzer_output.tasks)}...")
        generator_input = ImageGeneratorInput(
            tasks=analyzer_output.tasks,
            content=content,
            taskId=task_id,
        )

        logger.info(f"[ImageTask] 执行 generator_agent.execute()...")
        generator_output = await generator_agent.execute(generator_input)

        logger.info(
            f"[ImageTask] 图片生成完成: total={generator_output.totalCount}, "
            f"success={generator_output.successCount}, failed={generator_output.failedCount}"
        )

        # 4. 更新数据库
        async with async_session_factory() as db:
            article_repo = ArticleRepository(db)
            task_repo = TaskRepository(db)

            # 更新文章正文和最终输出
            article = await article_repo.get_by_task_id(task_id)
            if article:
                await article_repo.update_content(
                    article_id=article.id,
                    content=generator_output.mergedContent,
                    word_count=str(len(generator_output.mergedContent)),
                )
                await article_repo.update_final_output(
                    article_id=article.id,
                    final_output=generator_output.mergedContent,
                )

                # 更新任务状态为完成
                await task_repo.update_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    status_message=f"文章创作完成，配图 {generator_output.successCount} 张",
                    progress="100",
                )

                # 确保事务提交
                await db.commit()
                logger.info(f"[ImageTask] 数据库事务已提交，状态更新为 COMPLETED")

                # 发送完成事件（携带合并后的最终内容）
                await sse_manager.send_done(
                    task_id=task_id,
                    article_id=article.id,
                    final_output=generator_output.mergedContent,
                    final_html=generator_output.mergedHtml,
                )

                # 发送状态更新
                await sse_manager.send_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED.value,
                    message="文章创作完成",
                    progress=100,
                )

            logger.info(f"[ImageTask] 配图生成流程完成")

    except Exception as e:
        logger.error(f"[ImageTask] 配图生成失败: {e}", exc_info=True)

        from app.utils.database import async_session_factory

        async with async_session_factory() as db:
            repo = TaskRepository(db)
            await repo.set_error(task_id, str(e))
            await db.commit()

        # 发送错误事件
        await sse_manager.send_error(
            task_id=task_id,
            code="IMAGE_GENERATION_ERROR",
            message="配图生成失败",
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

            # 确保事务提交
            await db.commit()
            logger.info(f"[OptimizeOutlineTask] 数据库事务已提交，状态更新为 OUTLINE_READY")

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
            await db.commit()

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

    # 检查任务状态 - 放宽验证，允许 TITLE_GENERATING（可能数据库同步延迟）
    # 如果状态是 TITLE_GENERATING 或 TITLE_READY，都允许选择标题
    if task.status not in [TaskStatus.TITLE_READY, TaskStatus.TITLE_GENERATING]:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许选择标题：当前状态={task.status.value}",
        )

    # 如果状态是 TITLE_GENERATING，自动更新为 TITLE_READY（处理数据库同步延迟）
    if task.status == TaskStatus.TITLE_GENERATING:
        logger.info(f"[SelectTitle] 任务状态为 TITLE_GENERATING，自动更新为 TITLE_READY: task_id={task_id}")
        await task_repo.update_status(
            task_id=task_id,
            status=TaskStatus.TITLE_READY,
            status_message="标题生成完成，请选择标题",
            progress="20",
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

    # 检查任务状态 - 放宽验证，处理数据库同步延迟
    if task.status not in [TaskStatus.TITLE_READY, TaskStatus.TITLE_GENERATING]:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成大纲：当前状态={task.status.value}",
        )

    # 如果状态是 TITLE_GENERATING，自动更新为 TITLE_READY
    if task.status == TaskStatus.TITLE_GENERATING:
        logger.info(f"[GenerateOutline] 任务状态为 TITLE_GENERATING，自动更新为 TITLE_READY: task_id={task_id}")
        await task_repo.update_status(
            task_id=task_id,
            status=TaskStatus.TITLE_READY,
            status_message="标题生成完成，请选择标题",
            progress="20",
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

    # 检查任务状态 - 放宽验证，处理数据库同步延迟
    if task.status not in [TaskStatus.OUTLINE_READY, TaskStatus.OUTLINE_GENERATING]:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成正文：当前状态={task.status.value}",
        )

    # 如果状态是 OUTLINE_GENERATING，自动更新为 OUTLINE_READY
    if task.status == TaskStatus.OUTLINE_GENERATING:
        logger.info(f"[ConfirmOutline] 任务状态为 OUTLINE_GENERATING，自动更新为 OUTLINE_READY: task_id={task_id}")
        await task_repo.update_status(
            task_id=task_id,
            status=TaskStatus.OUTLINE_READY,
            status_message="大纲生成完成，请确认大纲",
            progress="40",
        )

    # 获取文章记录
    article = await article_repo.get_by_task_id(task_id)
    logger.info(f"[ConfirmOutline] 查询文章记录: task_id={task_id}, article_exists={article is not None}")
    if article:
        logger.info(f"[ConfirmOutline] 文章ID: {article.id}, selected_title={article.selected_title}, outline_exists={article.outline is not None}")
        if article.outline:
            logger.info(f"[ConfirmOutline] 大纲内容摘要: {str(article.outline)[:200]}...")

    if not article or not article.selected_title:
        return ApiResponse.error(
            code="1202",
            message="请先选择标题后再生成正文",
        )

    # 获取大纲（优先使用请求中的大纲，否则使用已有大纲）
    outline = request.outline if request and request.outline else article.outline
    logger.info(f"[ConfirmOutline] 使用大纲来源: request_outline={request and request.outline is not None}, article_outline={article.outline is not None}")

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


# ============ 配图生成接口 ============


@router.post("/tasks/{task_id}/start-image-analysis", summary="触发配图生成")
async def start_image_analysis(
    task_id: str,
    background_tasks: BackgroundTasks,
    use_mock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    触发配图分析和生成

    正文生成完成后，启动配图流程：
    1. ImageAnalyzerAgent 解析正文中的 IMAGE_PLACEHOLDER 占位符
    2. ImageGeneratorAgent 并行执行图片任务
    3. 图文合并，生成最终输出

    - **task_id**: 任务唯一标识
    - **use_mock**: 是否使用 mock 实现（测试用，默认 false）

    SSE 事件序列：
    - image_task_start: 图片任务开始，包含任务总数
    - image_progress: 单张图片处理进度（多次）
    - image_complete: 单张图片完成（多次）
    - image_all_complete: 所有图片任务完成
    - done: 文章创作完成

    使用流程：
    1. 正文生成完成后调用此接口
    2. 通过 SSE 接收配图进度和结果
    3. 收到 done 事件后可查看完整文章
    """
    task_repo = TaskRepository(db)
    article_repo = ArticleRepository(db)

    task = await task_repo.get(task_id)
    if not task:
        return ApiResponse.error(code="1200", message="任务不存在")

    # 检查任务状态 - 正文完成后才能开始配图
    if task.status != TaskStatus.CONTENT_READY:
        return ApiResponse.error(
            code="1201",
            message=f"任务状态不允许生成配图：当前状态={task.status.value}，需要正文完成后才能开始配图",
        )

    # 获取文章记录和正文内容
    article = await article_repo.get_by_task_id(task_id)
    if not article or not article.content:
        return ApiResponse.error(
            code="1202",
            message="正文不存在，请先生成正文",
        )

    # 更新状态为 IMAGE_GENERATING
    await task_repo.update_status(
        task_id=task_id,
        status=TaskStatus.IMAGE_GENERATING,
        status_message="正在生成配图...",
        progress="65",
    )

    # 发送状态变更事件（如果有 SSE 连接）
    await sse_manager.send_status(
        task_id=task_id,
        status=TaskStatus.IMAGE_GENERATING.value,
        message="正在生成配图...",
        progress=65,
    )

    # 启动后台任务
    background_tasks.add_task(
        _generate_images_task,
        task_id,
        article.content,
        use_mock,
    )

    return ApiResponse.ok(
        data={
            "task_id": task_id,
            "status": TaskStatus.IMAGE_GENERATING.value,
            "stage": "image",
            "message": "配图生成任务已启动，请通过 SSE 接收结果",
        },
        message="配图生成任务已启动",
    )