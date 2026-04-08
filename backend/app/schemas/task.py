"""
Task 数据传输对象
用于 API 请求和响应的数据结构定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""

    CREATED = "CREATED"
    TITLE_GENERATING = "TITLE_GENERATING"
    TITLE_READY = "TITLE_READY"
    OUTLINE_GENERATING = "OUTLINE_GENERATING"
    OUTLINE_READY = "OUTLINE_READY"
    CONTENT_GENERATING = "CONTENT_GENERATING"
    IMAGE_GENERATING = "IMAGE_GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ============ 创建任务请求 ============


class TaskCreateRequest(BaseModel):
    """创建任务请求"""

    topic: str = Field(..., min_length=1, max_length=500, description="选题描述")
    style: str = Field(default="专业", max_length=50, description="文章风格")
    extra_description: Optional[str] = Field(
        default=None, max_length=1000, description="补充描述"
    )


# ============ 任务响应 ============


class TaskResponse(BaseModel):
    """任务响应"""

    id: str = Field(..., description="任务 ID")
    topic: str = Field(..., description="选题描述")
    style: str = Field(..., description="文章风格")
    extra_description: Optional[str] = Field(None, description="补充描述")
    status: TaskStatusEnum = Field(..., description="任务状态")
    status_message: Optional[str] = Field(None, description="状态消息")
    progress: str = Field(default="0", description="进度百分比")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    items: List[TaskResponse]
    total: int


class TaskUpdateStatusRequest(BaseModel):
    """更新任务状态请求"""

    status: TaskStatusEnum = Field(..., description="新状态")
    status_message: Optional[str] = Field(None, description="状态消息")
    progress: Optional[str] = Field(None, description="进度百分比")


# ============ SSE 事件数据结构 ============


class SSEStatusEvent(BaseModel):
    """状态变更 SSE 事件"""

    status: TaskStatusEnum
    message: str


class SSETitleChunkEvent(BaseModel):
    """标题生成片段 SSE 事件"""

    content: str
    index: int


class SSETitleCompleteEvent(BaseModel):
    """标题生成完成 SSE 事件"""

    titles: List[str]


class SSEOutlineChunkEvent(BaseModel):
    """大纲生成片段 SSE 事件"""

    content: str


class SSEOutlineCompleteEvent(BaseModel):
    """大纲生成完成 SSE 事件"""

    outline: Dict[str, Any]


class SSEContentChunkEvent(BaseModel):
    """正文生成片段 SSE 事件"""

    content: str


class SSEImageProgressEvent(BaseModel):
    """配图生成进度 SSE 事件"""

    position: str
    status: str
    provider: Optional[str] = None


class SSEImageCompleteEvent(BaseModel):
    """配图生成完成 SSE 事件"""

    position: str
    url: str
    source: str


class SSEErrorEvent(BaseModel):
    """错误 SSE 事件"""

    code: str
    message: str


class SSEDoneEvent(BaseModel):
    """完成 SSE 事件"""

    article_id: str


# ============ 大纲相关请求 ============


class SelectTitleRequest(BaseModel):
    """选择标题请求"""

    selected_title: str = Field(..., min_length=1, max_length=200, description="选定的标题")


class GenerateOutlineRequest(BaseModel):
    """生成大纲请求"""

    target_length: Optional[int] = Field(default=2000, ge=500, le=10000, description="目标字数")


class OptimizeOutlineRequest(BaseModel):
    """优化大纲请求"""

    user_modifications: str = Field(..., min_length=1, max_length=2000, description="用户修改建议")


class SaveOutlineRequest(BaseModel):
    """保存大纲请求"""

    outline: Dict[str, Any] = Field(..., description="大纲结构数据")


class ConfirmOutlineRequest(BaseModel):
    """确认大纲请求（触发正文生成）"""

    outline: Optional[Dict[str, Any]] = Field(
        default=None, description="用户编辑后的大纲（可选，不传则使用已有大纲）"
    )