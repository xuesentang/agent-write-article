"""
schemas 模块初始化
定义数据传输对象 (DTO)
"""

from app.schemas.response import ApiResponse, PagedData, PagedResponse
from app.schemas.error_codes import ErrorCode, ErrorMessages

__all__ = [
    "ApiResponse",
    "PagedData",
    "PagedResponse",
    "ErrorCode",
    "ErrorMessages",
]