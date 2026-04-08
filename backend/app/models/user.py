"""
User 用户模型
预留用户系统，支持未来扩展
"""

import uuid
from sqlalchemy import Column, String, Boolean, Index

from app.models.base import Base


class User(Base):
    """
    用户表（预留）

    当前项目为个人/小团队使用，用户系统暂不完整实现。
    后续可扩展为完整的用户认证系统。
    """

    __tablename__ = "users"

    # 主键
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="用户唯一标识 (UUID)",
    )

    # 用户名
    username = Column(
        String(50),
        unique=True,
        nullable=True,
        comment="用户名",
    )

    # 邮箱
    email = Column(
        String(100),
        unique=True,
        nullable=True,
        comment="邮箱地址",
    )

    # 密码哈希
    password_hash = Column(
        String(128),
        nullable=True,
        comment="密码哈希值",
    )

    # 是否激活
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="用户是否激活",
    )

    # 索引设计
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"