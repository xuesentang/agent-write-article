"""
图片相关数据结构定义
用于 Agent4 和 Agent5 的输入输出及中间数据传输
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ImageType(str, Enum):
    """图片类型枚举"""
    PHOTO = "photo"           # 照片类正文配图
    ILLUSTRATION = "illustration"  # 插图类
    ICON = "icon"             # 图标类（仅用于装饰）
    DECORATIVE = "decorative"  # 装饰类元素
    DIAGRAM = "diagram"       # 图表/流程图类


class ImageProvider(str, Enum):
    """图片服务提供商枚举"""
    PEXELS = "pexels"         # 正文配图主源
    SEEDREAM = "seedream"     # 定制化主题图（字节跳动文生图）
    ICONIFY = "iconify"       # 仅限图标/装饰类
    PICSUM = "picsum"         # 兜底随机图


class ImageTaskStatus(str, Enum):
    """图片任务状态枚举"""
    PENDING = "pending"       # 待处理
    PROCESSING = "processing" # 正在处理
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 已失败（兜底后也算完成）
    SKIPPED = "skipped"       # 已跳过（无配图需求）


# ============ 图片任务数据结构 ============


class ImageTask(BaseModel):
    """
    单个图片任务

    由 ImageAnalyzerAgent 生成，传递给 ImageGeneratorAgent 执行
    """

    taskId: str = Field(
        ...,
        description="任务唯一ID，UUID格式",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    placeholderId: str = Field(
        ...,
        description="占位符唯一标识，如 image_1、image_2",
        examples=["image_1"]
    )
    position: int = Field(
        ...,
        ge=1,
        description="占位符在正文中的顺序位置（从1开始）",
        examples=[1, 2, 3]
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="图片搜索/生成关键词数组",
        examples=[["科技创新", "人工智能", "未来趋势"]]
    )
    description: str = Field(
        default="",
        max_length=200,
        description="配图用途描述，用于强调配图的具体用途",
        examples=["用于引言部分，展示自媒体时代背景"]
    )
    imageType: ImageType = Field(
        default=ImageType.PHOTO,
        description="图片类型: photo/illustration/icon/decorative/diagram"
    )
    preferredProviders: List[ImageProvider] = Field(
        default_factory=lambda: [ImageProvider.PEXELS],
        description="优先使用的图片服务数组",
        examples=[["pexels", "seedream"]]
    )
    fallbackProviders: List[ImageProvider] = Field(
        default_factory=lambda: [ImageProvider.PICSUM],
        description="降级备选服务数组",
        examples=[["picsum"]]
    )
    retryCount: int = Field(
        default=0,
        ge=0,
        description="已重试次数"
    )
    maxRetries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="最大重试次数"
    )
    status: ImageTaskStatus = Field(
        default=ImageTaskStatus.PENDING,
        description="当前状态: pending/processing/completed/failed/skipped"
    )

    # 上下文内容（占位符前一个自然段的文本，用于构建精准的图片生成 Prompt）
    context: Optional[str] = Field(
        default=None,
        description="占位符前一个自然段的上下文内容，用于构建更精准的 Seedream 生成 Prompt"
    )

    # 用于追踪的元数据
    sectionTitle: Optional[str] = Field(
        default=None,
        description="所属段落标题（用于描述生成）"
    )
    rawPlaceholderText: Optional[str] = Field(
        default=None,
        description="原始占位符文本（用于调试）"
    )


class ImageTaskList(BaseModel):
    """图片任务列表"""

    tasks: List[ImageTask] = Field(
        default_factory=list,
        description="图片任务列表"
    )
    totalCount: int = Field(
        default=0,
        ge=0,
        description="任务总数"
    )
    contentHash: Optional[str] = Field(
        default=None,
        description="正文内容hash，用于校验"
    )


# ============ 图片获取结果数据结构 ============


class ImageFetchResult(BaseModel):
    """
    图片获取结果

    由各图片服务返回，包含获取到的图片信息
    """

    url: str = Field(
        ...,
        description="图片源URL（原始服务URL）"
    )
    provider: ImageProvider = Field(
        ...,
        description="实际使用的服务提供商"
    )
    width: int = Field(
        default=1200,
        ge=1,
        description="图片宽度"
    )
    height: int = Field(
        default=800,
        ge=1,
        description="图片高度"
    )
    sourceId: Optional[str] = Field(
        default=None,
        description="源图片ID（如Pexels photo ID）"
    )
    meta: Optional[dict] = Field(
        default=None,
        description="额外元数据（如作者信息、色彩信息等）"
    )

    # 错误信息（获取失败时）
    error: Optional[str] = Field(
        default=None,
        description="错误信息（如果获取失败）"
    )
    success: bool = Field(
        default=True,
        description="是否成功获取"
    )


# ============ 图片最终结果数据结构 ============


class ImageResult(BaseModel):
    """
    图片最终结果

    由 ImageGeneratorAgent 返回，包含COS上传后的最终信息
    """

    taskId: str = Field(
        ...,
        description="任务ID"
    )
    placeholderId: str = Field(
        ...,
        description="占位符ID，用于替换匹配"
    )
    url: str = Field(
        ...,
        description="最终COS访问URL"
    )
    cosKey: str = Field(
        ...,
        description="COS存储路径/Key"
    )
    width: int = Field(
        default=1200,
        description="图片宽度"
    )
    height: int = Field(
        default=800,
        description="图片高度"
    )
    sourceProvider: ImageProvider = Field(
        ...,
        description="实际使用的源服务"
    )
    status: ImageTaskStatus = Field(
        default=ImageTaskStatus.COMPLETED,
        description="最终状态"
    )
    errorMessage: Optional[str] = Field(
        default=None,
        description="错误信息（如果有）"
    )

    # 用于调试的额外信息
    originalUrl: Optional[str] = Field(
        default=None,
        description="原始图片URL（上传前的URL）"
    )
    uploadTime: Optional[float] = Field(
        default=None,
        description="上传耗时（毫秒）"
    )


class ImageResultList(BaseModel):
    """图片结果列表"""

    results: List[ImageResult] = Field(
        default_factory=list,
        description="图片结果列表"
    )
    totalCount: int = Field(
        default=0,
        ge=0,
        description="结果总数"
    )
    successCount: int = Field(
        default=0,
        ge=0,
        description="成功数量"
    )
    failedCount: int = Field(
        default=0,
        ge=0,
        description="失败数量"
    )


# ============ Agent 输入输出数据结构 ============


class ImageAnalyzerInput(BaseModel):
    """ImageAnalyzerAgent 输入数据"""

    content: str = Field(
        ...,
        min_length=1,
        description="Markdown格式正文内容"
    )
    imagePlaceholders: Optional[List[dict]] = Field(
        default=None,
        description="ContentAgent提取的占位符列表（可选，用于辅助）"
    )


class ImageAnalyzerOutput(BaseModel):
    """ImageAnalyzerAgent 输出数据"""

    tasks: List[ImageTask] = Field(
        default_factory=list,
        description="结构化图片任务列表"
    )
    totalCount: int = Field(
        default=0,
        ge=0,
        description="任务总数"
    )
    contentHash: str = Field(
        ...,
        description="正文内容hash（用于校验）"
    )
    parseErrors: Optional[List[dict]] = Field(
        default=None,
        description="解析过程中遇到的格式错误列表"
    )


class ImageGeneratorInput(BaseModel):
    """ImageGeneratorAgent 输入数据"""

    tasks: List[ImageTask] = Field(
        ...,
        min_length=1,
        description="图片任务列表（来自Agent4）"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="原始正文内容（用于合并）"
    )
    taskId: str = Field(
        ...,
        description="文章生成任务ID（用于SSE推送）"
    )


class ImageGeneratorOutput(BaseModel):
    """ImageGeneratorAgent 输出数据"""

    results: List[ImageResult] = Field(
        default_factory=list,
        description="图片结果列表"
    )
    mergedContent: str = Field(
        ...,
        description="合并后的最终正文（图片已替换）"
    )
    totalCount: int = Field(
        default=0,
        ge=0,
        description="处理总数"
    )
    successCount: int = Field(
        default=0,
        ge=0,
        description="成功数量"
    )
    failedCount: int = Field(
        default=0,
        ge=0,
        description="失败数量"
    )
    skippedCount: int = Field(
        default=0,
        ge=0,
        description="跳过数量（无配图位置）"
    )


# ============ SSE 事件数据结构（新增） ============


class ImageTaskStartEventData(BaseModel):
    """图片任务开始事件数据"""

    taskId: str = Field(..., description="文章生成任务ID")
    totalImageTasks: int = Field(..., ge=0, description="图片任务总数")
    placeholders: List[str] = Field(
        default_factory=list,
        description="占位符ID列表"
    )


class ImageAllCompleteEventData(BaseModel):
    """所有图片任务完成事件数据"""

    taskId: str = Field(..., description="文章生成任务ID")
    totalCount: int = Field(..., ge=0, description="处理总数")
    successCount: int = Field(..., ge=0, description="成功数量")
    failedCount: int = Field(..., ge=0, description="失败数量")
    results: List[dict] = Field(
        default_factory=list,
        description="结果摘要列表"
    )