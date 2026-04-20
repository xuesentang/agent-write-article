"""
文章管理路由
提供文章的 CRUD 操作接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.response import ApiResponse, PagedResponse
from app.schemas.article import (
    ArticleResponse,
    ArticleListResponse,
    ArticleSelectTitleRequest,
    ArticleUpdateOutlineRequest,
    ArticleUpdateImagesRequest,
    TitleOption,
    OutlineStructure,
    ImageInfo,
)
from app.services.article_repository import ArticleRepository
from app.services.task_repository import TaskRepository
from app.models.task import TaskStatus


router = APIRouter()


@router.get("/articles/{article_id}", summary="获取文章详情")
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据 ID 获取文章详情

    - **article_id**: 文章唯一标识
    """
    repo = ArticleRepository(db)
    article = await repo.get(article_id)

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    return ApiResponse.ok(
        data=ArticleResponse(
            id=article.id,
            task_id=article.task_id,
            selected_title=article.selected_title,
            title_options=[TitleOption(**t) for t in (article.title_options or [])],
            outline=OutlineStructure(**article.outline) if article.outline else None,
            content=article.content,
            images=[ImageInfo(**img) for img in (article.images or [])],
            final_output=article.final_output,
            final_html=article.final_html,
            word_count=article.word_count,
            created_at=article.created_at,
            updated_at=article.updated_at,
        ),
    )


@router.get("/articles", summary="获取文章列表")
async def list_articles(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    分页获取文章列表

    - **page**: 页码（默认 1）
    - **page_size**: 每页数量（默认 10）
    """
    repo = ArticleRepository(db)

    skip = (page - 1) * page_size
    articles = await repo.get_multi(skip=skip, limit=page_size)
    total = await repo.count()

    items = [
        ArticleResponse(
            id=article.id,
            task_id=article.task_id,
            selected_title=article.selected_title,
            title_options=[TitleOption(**t) for t in (article.title_options or [])],
            outline=OutlineStructure(**article.outline) if article.outline else None,
            content=article.content,
            images=[ImageInfo(**img) for img in (article.images or [])],
            final_output=article.final_output,
            word_count=article.word_count,
            created_at=article.created_at,
            updated_at=article.updated_at,
        )
        for article in articles
    ]

    return PagedResponse.ok(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/by-task/{task_id}", summary="根据任务ID获取文章")
async def get_article_by_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据关联任务 ID 获取文章

    - **task_id**: 关联任务唯一标识
    """
    repo = ArticleRepository(db)
    article = await repo.get_by_task_id(task_id)

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    return ApiResponse.ok(
        data=ArticleResponse(
            id=article.id,
            task_id=article.task_id,
            selected_title=article.selected_title,
            title_options=[TitleOption(**t) for t in (article.title_options or [])],
            outline=OutlineStructure(**article.outline) if article.outline else None,
            content=article.content,
            images=[ImageInfo(**img) for img in (article.images or [])],
            final_output=article.final_output,
            final_html=article.final_html,
            word_count=article.word_count,
            created_at=article.created_at,
            updated_at=article.updated_at,
        ),
    )


@router.patch("/articles/{article_id}/title", summary="选择标题")
async def select_title(
    article_id: str,
    request: ArticleSelectTitleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    设置用户选择的标题

    - **article_id**: 文章唯一标识
    - **selected_title**: 用户选定的标题
    """
    repo = ArticleRepository(db)
    article = await repo.select_title(article_id, request.selected_title)

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    # 更新任务状态
    task_repo = TaskRepository(db)
    await task_repo.update_status(
        article.task_id,
        TaskStatus.OUTLINE_GENERATING,
        "正在生成大纲...",
        "30",
    )

    return ApiResponse.ok(
        data={"selected_title": article.selected_title},
        message="标题选择成功",
    )


@router.patch("/articles/{article_id}/outline", summary="更新大纲")
async def update_outline(
    article_id: str,
    request: ArticleUpdateOutlineRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新文章大纲

    - **article_id**: 文章唯一标识
    - **outline**: 新的大纲结构
    """
    repo = ArticleRepository(db)
    article = await repo.update_outline(article_id, request.outline.model_dump())

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    return ApiResponse.ok(
        data=OutlineStructure(**article.outline) if article.outline else None,
        message="大纲更新成功",
    )


@router.patch("/articles/{article_id}/images", summary="更新配图")
async def update_images(
    article_id: str,
    request: ArticleUpdateImagesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新文章配图

    - **article_id**: 文章唯一标识
    - **images**: 配图信息列表
    """
    repo = ArticleRepository(db)
    article = await repo.update_images(
        article_id, [img.model_dump() for img in request.images]
    )

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    return ApiResponse.ok(
        data=[ImageInfo(**img) for img in (article.images or [])],
        message="配图更新成功",
    )


@router.delete("/articles/{article_id}", summary="删除文章")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除文章

    - **article_id**: 文章唯一标识
    """
    repo = ArticleRepository(db)
    success = await repo.delete(article_id)

    if not success:
        return ApiResponse.error(code="1300", message="文章不存在")

    return ApiResponse.ok(message="文章删除成功")


@router.get("/articles/{article_id}/export", summary="导出文章")
async def export_article(
    article_id: str,
    format: str = "html",
    db: AsyncSession = Depends(get_db),
):
    """
    导出文章

    - **article_id**: 文章唯一标识
    - **format**: 导出格式 (html/markdown)，默认 html
    """
    repo = ArticleRepository(db)
    article = await repo.get(article_id)

    if not article:
        return ApiResponse.error(code="1300", message="文章不存在")

    if format == "html" and article.final_html:
        return ApiResponse.ok(
            data={
                "title": article.selected_title,
                "content": article.final_html,
                "html": article.final_html,
                "word_count": article.word_count,
                "format": "html",
            },
        )

    # 如果有最终合并内容，返回 Markdown
    if article.final_output:
        return ApiResponse.ok(
            data={
                "title": article.selected_title,
                "content": article.final_output,
                "word_count": article.word_count,
                "format": "markdown",
            },
        )

    # 否则返回正文和配图分开的数据
    return ApiResponse.ok(
        data={
            "title": article.selected_title,
            "content": article.content,
            "images": [ImageInfo(**img) for img in (article.images or [])],
            "word_count": article.word_count,
            "format": "markdown",
        },
    )