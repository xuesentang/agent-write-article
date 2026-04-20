"""
SSE (Server-Sent Events) 数据结构定义
统一的事件数据格式
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
from enum import Enum


class SSEEventType(str, Enum):
    """SSE 事件类型枚举"""

    # 任务状态变更
    STATUS = "status"

    # 标题生成相关
    TITLE_CHUNK = "title_chunk"
    TITLE_COMPLETE = "title_complete"

    # 大纲生成相关
    OUTLINE_CHUNK = "outline_chunk"
    OUTLINE_COMPLETE = "outline_complete"

    # 正文生成相关
    CONTENT_CHUNK = "content_chunk"
    CONTENT_COMPLETE = "content_complete"

    # 配图生成相关
    IMAGE_TASK_START = "image_task_start"      # 图片任务开始
    IMAGE_PROGRESS = "image_progress"          # 图片生成进度
    IMAGE_COMPLETE = "image_complete"          # 单张图片完成
    IMAGE_ALL_COMPLETE = "image_all_complete"  # 所有图片任务完成

    # 通用事件
    PROGRESS = "progress"  # 进度更新
    ERROR = "error"        # 错误信息
    DONE = "done"          # 任务完成
    HEARTBEAT = "heartbeat"  # 心跳


class SSEStage(str, Enum):
    """SSE 阶段枚举"""

    TITLE = "title"
    OUTLINE = "outline"
    CONTENT = "content"
    IMAGE = "image"


# ============ 统一事件数据格式 ============


class SSEEventData(BaseModel):
    """
    统一 SSE 事件数据格式

    所有 SSE 事件都使用这个统一格式，便于前端统一处理。
    """

    event: SSEEventType = Field(..., description="事件类型")
    stage: Optional[SSEStage] = Field(None, description="当前阶段")
    data: Any = Field(None, description="事件内容")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比 0-100")
    message: Optional[str] = Field(None, description="人类可读的消息")
    timestamp: Optional[str] = Field(None, description="时间戳")

    def to_sse_format(self, event_id: Optional[int] = None) -> str:
        """
        转换为 SSE 标准格式字符串

        SSE 格式:
        event: {事件类型}
        data: {JSON 数据}
        id: {消息序号}

        Args:
            event_id: 消息序号（可选）

        Returns:
            SSE 格式字符串
        """
        import json
        from datetime import datetime

        # 添加时间戳
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

        lines = [f"event: {self.event.value}"]
        lines.append(f"data: {json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)}")

        if event_id is not None:
            lines.append(f"id: {event_id}")

        return "\n".join(lines) + "\n\n"


# ============ 具体事件数据模型 ============


class StatusEventData(BaseModel):
    """状态变更事件数据"""

    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="状态描述")


class TitleChunkEventData(BaseModel):
    """标题生成片段数据"""

    content: str = Field(..., description="标题片段内容")
    index: int = Field(..., ge=0, description="标题序号（第几个标题方案）")


class TitleCompleteEventData(BaseModel):
    """标题生成完成数据"""

    titles: List[str] = Field(..., description="生成的标题列表")


class OutlineChunkEventData(BaseModel):
    """大纲生成片段数据"""

    content: str = Field(..., description="大纲片段内容")


class OutlineCompleteEventData(BaseModel):
    """大纲生成完成数据"""

    outline: dict = Field(..., description="结构化大纲")


class ContentChunkEventData(BaseModel):
    """正文生成片段数据"""

    content: str = Field(..., description="正文片段内容")


class ContentCompleteEventData(BaseModel):
    """正文生成完成数据"""

    content: str = Field(..., description="完整正文内容")
    word_count: int = Field(..., description="字数统计")
    image_count: int = Field(default=0, description="配图数量")


class ImageProgressEventData(BaseModel):
    """配图生成进度数据"""

    position: str = Field(..., description="图片位置标识")
    status: str = Field(..., description="状态：generating/completed/failed")
    provider: Optional[str] = Field(None, description="配图服务提供者")


class ImageCompleteEventData(BaseModel):
    """配图生成完成数据"""

    position: str = Field(..., description="图片位置标识")
    url: str = Field(..., description="图片 URL")
    source: str = Field(..., description="图片来源服务")


class ErrorEventData(BaseModel):
    """错误事件数据"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    details: Optional[str] = Field(None, description="错误详情")


class DoneEventData(BaseModel):
    """任务完成事件数据"""

    article_id: str = Field(..., description="生成的文章 ID")
    final_output: Optional[str] = Field(None, description="合并后的最终正文内容（含配图）")
    message: str = Field(default="文章生成完成", description="完成消息")


class ImageTaskStartEventData(BaseModel):
    """图片任务开始事件数据"""

    task_id: str = Field(..., description="文章生成任务ID")
    total_image_tasks: int = Field(..., ge=0, description="图片任务总数")
    placeholders: List[str] = Field(
        default_factory=list,
        description="占位符ID列表"
    )


class ImageAllCompleteEventData(BaseModel):
    """所有图片任务完成事件数据"""

    task_id: str = Field(..., description="文章生成任务ID")
    total_count: int = Field(..., ge=0, description="处理总数")
    success_count: int = Field(..., ge=0, description="成功数量")
    failed_count: int = Field(..., ge=0, description="失败数量")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="结果摘要列表"
    )
    merged_content: Optional[str] = Field(None, description="图文合并后的 Markdown 正文")
    merged_html: Optional[str] = Field(None, description="图文合并后的 HTML 富文本")