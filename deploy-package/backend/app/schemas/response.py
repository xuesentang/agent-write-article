"""
统一响应格式定义
所有 API 接口返回统一的响应结构，便于前端统一处理
"""

from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

from app.schemas.error_codes import ErrorCode, ErrorMessages


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""

    code: str = ErrorCode.SUCCESS
    message: str = "操作成功"
    data: Optional[T] = None
    success: bool = True

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "操作成功") -> "ApiResponse[T]":
        """成功响应"""
        return cls(
            code=ErrorCode.SUCCESS,
            message=message,
            data=data,
            success=True,
        )

    @classmethod
    def error(
        cls,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        message: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> "ApiResponse[T]":
        """错误响应"""
        error_message = message or ErrorMessages.get_message(code)
        return cls(
            code=code,
            message=error_message,
            data=data,
            success=False,
        )


class PagedData(BaseModel, Generic[T]):
    """分页数据结构"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 10,
    ) -> "PagedData[T]":
        """创建分页数据"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PagedResponse(BaseModel, Generic[T]):
    """分页响应"""

    code: str = ErrorCode.SUCCESS
    message: str = "操作成功"
    data: Optional[PagedData[T]] = None
    success: bool = True

    @classmethod
    def ok(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 10,
        message: str = "操作成功",
    ) -> "PagedResponse[T]":
        """成功分页响应"""
        paged_data = PagedData.create(items, total, page, page_size)
        return cls(
            code=ErrorCode.SUCCESS,
            message=message,
            data=paged_data,
            success=True,
        )