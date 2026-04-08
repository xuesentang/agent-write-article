"""
Task 任务仓库
提供任务相关的数据库操作
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.services.base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """
    任务仓库

    继承基础仓库，添加任务特有的操作方法。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Task, session)

    async def get_by_status(self, status: TaskStatus) -> List[Task]:
        """
        查询指定状态的任务列表

        Args:
            status: 任务状态

        Returns:
            任务列表
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.status == status)
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_in_progress(self) -> List[Task]:
        """
        查询所有进行中的任务

        包括状态：TITLE_GENERATING, OUTLINE_GENERATING, CONTENT_GENERATING, IMAGE_GENERATING

        Returns:
            进行中的任务列表
        """
        in_progress_statuses = [
            TaskStatus.TITLE_GENERATING,
            TaskStatus.OUTLINE_GENERATING,
            TaskStatus.CONTENT_GENERATING,
            TaskStatus.IMAGE_GENERATING,
        ]

        result = await self.session.execute(
            select(Task)
            .where(Task.status.in_(in_progress_statuses))
            .order_by(Task.created_at)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        status_message: Optional[str] = None,
        progress: Optional[str] = None,
    ) -> Optional[Task]:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态
            status_message: 状态描述消息
            progress: 进度百分比

        Returns:
            更新后的任务实例
        """
        update_data = {"status": status}
        if status_message:
            update_data["status_message"] = status_message
        if progress:
            update_data["progress"] = progress

        return await self.update(task_id, update_data)

    async def set_error(self, task_id: str, error_message: str) -> Optional[Task]:
        """
        设置任务错误状态

        Args:
            task_id: 任务 ID
            error_message: 错误信息

        Returns:
            更新后的任务实例
        """
        return await self.update(
            task_id,
            {
                "status": TaskStatus.FAILED,
                "error_message": error_message,
                "status_message": "任务执行失败",
            },
        )

    async def get_completed_tasks(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[Task]:
        """
        查询已完成的任务列表

        Args:
            user_id: 用户 ID（可选）
            limit: 返回数量限制

        Returns:
            已完成的任务列表
        """
        query = select(Task).where(Task.status == TaskStatus.COMPLETED)

        if user_id:
            query = query.where(Task.user_id == user_id)

        query = query.order_by(Task.updated_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_by_topic(self, keyword: str, limit: int = 10) -> List[Task]:
        """
        根据选题关键词搜索任务

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的任务列表
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.topic.contains(keyword))
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())