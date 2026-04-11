"""
Task 任务模型
管理文章生成任务的状态流转
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, DateTime, ForeignKey, Index
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""

    CREATED = "CREATED"                    # 已创建，等待开始
    TITLE_GENERATING = "TITLE_GENERATING"  # 标题生成中
    TITLE_READY = "TITLE_READY"            # 标题方案就绪，待用户选择
    OUTLINE_GENERATING = "OUTLINE_GENERATING"  # 大纲生成中
    OUTLINE_READY = "OUTLINE_READY"        # 大纲就绪，待用户确认
    CONTENT_GENERATING = "CONTENT_GENERATING"  # 正文生成中
    CONTENT_READY = "CONTENT_READY"        # 正文完成，等待配图
    IMAGE_GENERATING = "IMAGE_GENERATING"  # 配图生成中
    COMPLETED = "COMPLETED"                # 已完成
    FAILED = "FAILED"                      # ailure


class Task(Base):
    """
    任务表

    记录每次文章生成任务的完整生命周期，包括：
    - 用户输入的选题信息
    - 当前任务状态
    - 各阶段完成时间

    状态流转：CREATED → TITLE_GENERATING → TITLE_READY →
              OUTLINE_GENERATING → OUTLINE_READY →
              CONTENT_GENERATING → IMAGE_GENERATING → COMPLETED
    """

    __tablename__ = "tasks"

    # 主键：UUID 格式，自动生成
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="任务唯一标识 (UUID)",
    )

    # 用户 ID（预留，后续接入用户系统）
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="用户ID，预留字段",
    )

    # 选题信息
    topic = Column(
        String(500),
        nullable=False,
        comment="用户输入的选题描述",
    )

    # 文章风格
    style = Column(
        String(50),
        nullable=False,
        default="专业",
        comment="文章风格：专业/轻松/幽默/深度/热点/教程",
    )

    # 用户补充描述
    extra_description = Column(
        Text,
        nullable=True,
        comment="用户补充的创作方向描述",
    )

    # 任务状态
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.CREATED,
        comment="当前任务状态",
    )

    # 状态消息（用于前端展示）
    status_message = Column(
        String(200),
        nullable=True,
        comment="当前状态的描述消息，如'正在生成标题...'",
    )

    # 进度百分比（0-100）
    progress = Column(
        String(5),
        nullable=False,
        default="0",
        comment="任务进度百分比，如'45'",
    )

    # 错误信息（失败时记录）
    error_message = Column(
        Text,
        nullable=True,
        comment="任务失败时的错误详情",
    )

    # 各阶段完成时间（JSON 格式存储）
    stage_times = Column(
        JSON,
        nullable=True,
        comment="""各阶段完成时间记录
        示例: {
            "title_completed": "2024-01-01T10:00:00",
            "outline_completed": "2024-01-01T10:05:00",
            "content_completed": "2024-01-01T10:15:00",
            "image_completed": "2024-01-01T10:20:00"
        }""",
    )

    # 关联文章（一对一）
    article = relationship(
        "Article",
        back_populates="task",
        uselist=False,
        lazy="selectin",
    )

    # 索引设计
    __table_args__ = (
        # 按状态查询（如查询所有进行中的任务）
        Index("ix_tasks_status", "status"),

        # 按创建时间排序（历史记录列表）
        Index("ix_tasks_created_at", "created_at"),

        # 按用户查询（预留）
        Index("ix_tasks_user_id", "user_id"),

        # 复合索引：用户+状态（查询某用户的所有进行中任务）
        Index("ix_tasks_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status}, topic={self.topic[:20]}...)>"