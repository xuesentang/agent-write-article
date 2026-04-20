"""
Article 文章仓库
提供文章相关的数据库操作
"""

from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.base_repository import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    """
    文章仓库

    继承基础仓库，添加文章特有的操作方法。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Article, session)

    async def get_by_task_id(self, task_id: str) -> Optional[Article]:
        """
        根据任务 ID 获取文章

        Args:
            task_id: 关联的任务 ID

        Returns:
            文章实例或 None
        """
        result = await self.session.execute(
            select(Article).where(Article.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_title_options(
        self, article_id: str, title_options: List[dict]
    ) -> Optional[Article]:
        """
        更新标题方案列表

        Args:
            article_id: 文章 ID
            title_options: 标题方案列表

        Returns:
            更新后的文章实例
        """
        return await self.update(article_id, {"title_options": title_options})

    async def select_title(
        self, article_id: str, selected_title: str
    ) -> Optional[Article]:
        """
        设置用户选择的标题

        Args:
            article_id: 文章 ID
            selected_title: 选定的标题

        Returns:
            更新后的文章实例
        """
        return await self.update(article_id, {"selected_title": selected_title})

    async def update_outline(self, article_id: str, outline: dict) -> Optional[Article]:
        """
        更新文章大纲

        Args:
            article_id: 文章 ID
            outline: 结构化大纲数据

        Returns:
            更新后的文章实例
        """
        return await self.update(article_id, {"outline": outline})

    async def update_content(
        self, article_id: str, content: str, word_count: Optional[str] = None
    ) -> Optional[Article]:
        """
        更新文章正文

        Args:
            article_id: 文章 ID
            content: Markdown 正文内容
            word_count: 文章字数

        Returns:
            更新后的文章实例
        """
        update_data = {"content": content}
        if word_count:
            update_data["word_count"] = word_count
        return await self.update(article_id, update_data)

    async def update_images(
        self, article_id: str, images: List[dict]
    ) -> Optional[Article]:
        """
        更新配图信息

        Args:
            article_id: 文章 ID
            images: 配图信息列表

        Returns:
            更新后的文章实例
        """
        return await self.update(article_id, {"images": images})

    async def update_final_output(
        self, article_id: str, final_output: str
    ) -> Optional[Article]:
        """
        更新最终合并内容

        Args:
            article_id: 文章 ID
            final_output: 合并后的完整文章

        Returns:
            更新后的文章实例
        """
        return await self.update(article_id, {"final_output": final_output})

    async def search_by_title(self, keyword: str, limit: int = 10) -> List[Article]:
        """
        根据标题关键词搜索文章

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的文章列表
        """
        result = await self.session.execute(
            select(Article)
            .where(
                or_(
                    Article.selected_title.contains(keyword),
                    Article.title_options.contains(keyword),
                )
            )
            .order_by(Article.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_articles(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[Article]:
        """
        获取最近的文章列表

        Args:
            user_id: 用户 ID（可选，用于后续用户系统）
            limit: 返回数量限制

        Returns:
            文章列表
        """
        query = select(Article).join(Article.task).order_by(Article.created_at.desc())

        if user_id:
            query = query.where(Article.task.has(user_id=user_id))

        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())