"""
schemas 模块初始化
定义数据传输对象 (DTO)
"""

from app.schemas.response import ApiResponse, PagedData, PagedResponse
from app.schemas.error_codes import ErrorCode, ErrorMessages
from app.schemas.sse import (
    SSEEventType,
    SSEStage,
    SSEEventData,
    StatusEventData,
    TitleChunkEventData,
    TitleCompleteEventData,
    OutlineChunkEventData,
    OutlineCompleteEventData,
    ContentChunkEventData,
    ImageProgressEventData,
    ImageCompleteEventData,
    ErrorEventData,
    DoneEventData,
)

__all__ = [
    "ApiResponse",
    "PagedData",
    "PagedResponse",
    "ErrorCode",
    "ErrorMessages",
    # SSE 相关
    "SSEEventType",
    "SSEStage",
    "SSEEventData",
    "StatusEventData",
    "TitleChunkEventData",
    "TitleCompleteEventData",
    "OutlineChunkEventData",
    "OutlineCompleteEventData",
    "ContentChunkEventData",
    "ImageProgressEventData",
    "ImageCompleteEventData",
    "ErrorEventData",
    "DoneEventData",
]