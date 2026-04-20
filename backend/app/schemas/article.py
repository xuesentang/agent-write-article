"""
Article 数据传输对象
用于 API 请求和响应的数据结构定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 大纲结构 ============


class OutlineSection(BaseModel):
    """大纲段落结构"""

    id: str = Field(..., description="段落唯一标识")
    title: str = Field(..., description="段落标题")
    level: int = Field(..., ge=1, le=5, description="层级深度")
    key_points: Optional[List[str]] = Field(default=None, description="要点列表")
    estimated_length: Optional[int] = Field(None, description="预估字数")
    subsections: Optional[List["OutlineSection"]] = Field(
        default=None, description="子段落列表"
    )


class OutlineStructure(BaseModel):
    """完整大纲结构"""

    sections: List[OutlineSection] = Field(..., description="段落列表")


# ============ 配图结构 ============


class ImageInfo(BaseModel):
    """配图信息"""

    position: str = Field(..., description="图片位置标识，如 after_paragraph_2")
    url: str = Field(..., description="图片 URL")
    source: str = Field(..., description="图片来源，如 pexels, seedream")
    keywords: Optional[List[str]] = Field(None, description="搜索关键词")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")


# ============ 标题方案 ============


class TitleOption(BaseModel):
    """标题方案"""

    title: str = Field(..., description="标题内容")
    index: int = Field(..., ge=0, description="方案序号")


# ============ 文章响应 ============


class ArticleResponse(BaseModel):
    """文章响应"""

    id: str = Field(..., description="文章 ID")
    task_id: str = Field(..., description="关联任务 ID")
    selected_title: Optional[str] = Field(None, description="选定标题")
    title_options: Optional[List[TitleOption]] = Field(None, description="标题方案列表")
    outline: Optional[OutlineStructure] = Field(None, description="文章大纲")
    content: Optional[str] = Field(None, description="Markdown 正文")
    images: Optional[List[ImageInfo]] = Field(None, description="配图列表")
    final_output: Optional[str] = Field(None, description="最终合并内容")
    word_count: Optional[str] = Field(None, description="文章字数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ArticleListResponse(BaseModel):
    """文章列表响应"""

    items: List[ArticleResponse]
    total: int


# ============ 文章更新请求 ============


class ArticleSelectTitleRequest(BaseModel):
    """选择标题请求"""

    selected_title: str = Field(..., min_length=1, max_length=200, description="选定的标题")


class ArticleUpdateOutlineRequest(BaseModel):
    """更新大纲请求"""

    outline: OutlineStructure = Field(..., description="新的大纲结构")


class ArticleAppendContentRequest(BaseModel):
    """追加正文请求（用于流式生成）"""

    chunk: str = Field(..., description="正文片段")


class ArticleUpdateImagesRequest(BaseModel):
    """更新配图请求"""

    images: List[ImageInfo] = Field(..., description="配图列表")


# ============ 文章导出格式 ============


class ArticleExportResponse(BaseModel):
    """文章导出响应"""

    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="完整内容")
    html: Optional[str] = Field(None, description="HTML 富文本内容")
    word_count: int = Field(..., description="总字数")
    images: List[Dict[str, Any]] = Field(..., description="配图信息")
    format: str = Field(default="markdown", description="导出格式")