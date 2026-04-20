"""
图片服务提供商基类
定义所有图片服务的统一接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.image import ImageFetchResult, ImageProvider, ImageType


logger = logging.getLogger(__name__)


class BaseImageProvider(ABC):
    """
    图片服务提供商基类

    所有图片服务（Pexels、Iconify、Seedream、Picsum）都继承此基类。
    提供统一的接口：
    - fetch_image: 获取图片
    - is_available: 检查服务是否可用（配置是否完整）
    - get_provider_name: 返回提供商名称
    """

    def __init__(self, provider_name: ImageProvider):
        """
        初始化基类

        Args:
            provider_name: 提供商名称枚举
        """
        self.provider_name = provider_name

    @abstractmethod
    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
        context: Optional[str] = None,
    ) -> ImageFetchResult:
        """
        获取图片

        Args:
            keywords: 搜索关键词列表
            image_type: 图片类型
            width: 目标宽度
            height: 目标高度
            context: 占位符前一个自然段的上下文内容（用于 Seedream 语义增强）

        Returns:
            ImageFetchResult: 图片获取结果
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            True 如果配置完整且可用，False 否则
        """
        pass

    def get_provider_name(self) -> ImageProvider:
        """
        获取提供商名称

        Returns:
            ImageProvider 枚举值
        """
        return self.provider_name

    def supports_image_type(self, image_type: ImageType) -> bool:
        """
        检查是否支持指定的图片类型

        Args:
            image_type: 图片类型

        Returns:
            True 如果支持，False 否则
        """
        # 默认所有服务都支持所有类型
        # 具体服务可以覆盖此方法添加限制
        return True

    def log_fetch_attempt(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int,
        height: int
    ):
        """记录获取尝试日志"""
        logger.info(
            f"[{self.provider_name.value}] 尝试获取图片: "
            f"keywords={keywords}, type={image_type.value}, "
            f"size={width}x{height}"
        )

    def log_fetch_success(
        self,
        url: str,
        width: int,
        height: int,
        latency_ms: Optional[float] = None
    ):
        """记录获取成功日志"""
        logger.info(
            f"[{self.provider_name.value}] 图片获取成功: "
            f"url={url[:50]}..., size={width}x{height}, "
            f"latency={latency_ms:.2f}ms" if latency_ms else ""
        )

    def log_fetch_error(self, error: str):
        """记录获取失败日志"""
        logger.error(f"[{self.provider_name.value}] 图片获取失败: {error}")