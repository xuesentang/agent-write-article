"""
CRUD 操作基类
提供通用的数据库操作方法
"""

from typing import TypeVar, Generic, Type, List, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    CRUD 操作基类

    提供通用的数据库操作方法：
    - create: 创建记录
    - get: 根据 ID 查询
    - get_multi: 分页查询列表
    - update: 更新记录
    - delete: 删除记录
    - count: 统计记录数
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        初始化仓库

        Args:
            model: ORM 模型类
            session: 数据库会话
        """
        self.model = model
        self.session = session

    async def create(self, data: dict) -> ModelType:
        """
        创建新记录

        Args:
            data: 字段数据字典

        Returns:
            创建的模型实例
        """
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get(self, id: str) -> Optional[ModelType]:
        """
        根据 ID 查询记录

        Args:
            id: 记录 ID

        Returns:
            模型实例或 None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict] = None,
        order_by: Optional[Any] = None,
    ) -> List[ModelType]:
        """
        分页查询记录列表

        Args:
            skip: 跳过记录数（偏移量）
            limit: 返回记录数上限
            filters: 过滤条件字典 {字段名: 值}
            order_by: 排序字段

        Returns:
            模型实例列表
        """
        query = select(self.model)

        # 应用过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        # 应用排序
        if order_by is not None:
            query = query.order_by(order_by)
        else:
            # 默认按创建时间降序
            query = query.order_by(self.model.created_at.desc())

        # 应用分页
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, id: str, data: dict) -> Optional[ModelType]:
        """
        更新记录

        Args:
            id: 记录 ID
            data: 更新数据字典

        Returns:
            更新后的模型实例或 None
        """
        instance = await self.get(id)
        if instance:
            for field, value in data.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
            await self.session.flush()
            await self.session.refresh(instance)
        return instance

    async def delete(self, id: str) -> bool:
        """
        删除记录

        Args:
            id: 记录 ID

        Returns:
            是否删除成功
        """
        instance = await self.get(id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False

    async def count(self, filters: Optional[dict] = None) -> int:
        """
        统计记录数

        Args:
            filters: 过滤条件字典

        Returns:
            记录总数
        """
        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0