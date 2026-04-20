"""
数据库模型基类
提供通用字段和方法
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM 基类"""

    # 创建时间（自动填充）
    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    # 更新时间（自动更新）
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )