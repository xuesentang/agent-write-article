"""
Article 文章模型
存储文章各阶段的生成内容
"""

import uuid
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship

from app.models.base import Base


class Article(Base):
    """
    文章表

    存储文章生成的完整内容，包括：
    - 标题方案和选定的标题
    - 结构化大纲（JSON）
    - Markdown 正文
    - 配图信息列表（JSON）
    - 最终合并的完整内容

    与 Task 表是一对一关系，每个任务对应一篇文章。
    """

    __tablename__ = "articles"

    # 主键：UUID 格式
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="文章唯一标识 (UUID)",
    )

    # 关联任务 ID（外键）
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 一对一关系
        comment="关联的任务ID",
    )

    # 用户选择的标题
    selected_title = Column(
        String(200),
        nullable=True,
        comment="用户最终选择的标题",
    )

    # 标题方案列表（JSON 数组）
    title_options = Column(
        JSON,
        nullable=True,
        comment="""AI 生成的标题方案列表
        示例: [
            {"title": "如何在30天内打造爆款自媒体账号", "index": 0},
            {"title": "自媒体新人必看：快速涨粉秘籍", "index": 1},
            {"title": "从0到10万粉丝：我的自媒体成长之路", "index": 2}
        ]""",
    )

    # 文章大纲（JSON 结构）
    outline = Column(
        JSON,
        nullable=True,
        comment="""结构化大纲
        示例: {
            "sections": [
                {
                    "id": "section_1",
                    "title": "引言",
                    "level": 1,
                    "key_points": ["背景介绍", "问题引出"],
                    "estimated_length": 200
                },
                {
                    "id": "section_2",
                    "title": "核心观点",
                    "level": 1,
                    "subsections": [...]
                }
            ]
        }""",
    )

    # Markdown 正文（带配图占位符）
    content = Column(
        Text,
        nullable=True,
        comment="Markdown 格式的正文内容，包含配图占位符如 {{image:para_2}}",
    )

    # 配图信息列表（JSON）
    images = Column(
        JSON,
        nullable=True,
        comment="""配图信息列表
        示例: [
            {
                "position": "after_paragraph_2",
                "url": "https://cos.xxx/img1.jpg",
                "source": "pexels",
                "keywords": ["科技", "创新"],
                "width": 800,
                "height": 600
            }
        ]""",
    )

    # 最终合并的完整内容
    final_output = Column(
        Text,
        nullable=True,
        comment="正文和配图合并后的完整文章内容（Markdown格式），可直接导出",
    )

    # 最终合并的 HTML 富文本内容
    final_html = Column(
        Text,
        nullable=True,
        comment="正文和配图合并后的 HTML 富文本内容，可直接用于展示和导出",
    )

    # 文章字数统计
    word_count = Column(
        String(10),
        nullable=True,
        comment="文章总字数，用于统计展示",
    )

    # 关联任务
    task = relationship(
        "Task",
        back_populates="article",
        lazy="selectin",
    )

    # 索引设计
    __table_args__ = (
        # 按任务 ID 查询文章（主要查询方式）
        Index("ix_articles_task_id", "task_id"),

        # 按创建时间排序
        Index("ix_articles_created_at", "created_at"),

        # 按标题搜索（模糊搜索优化）
        Index("ix_articles_selected_title", "selected_title"),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title={self.selected_title})>"