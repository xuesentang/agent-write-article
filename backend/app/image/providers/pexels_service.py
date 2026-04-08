"""
Pexels 图片服务
正文配图主源，高质量免费图片搜索

配置要求（从 .env 读取）：
- PEXELS_API_KEY: Pexels API 密钥

注意：若 API_KEY 未配置，服务不可用，但不会报错退出
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

from app.image.base_provider import BaseImageProvider
from app.schemas.image import ImageFetchResult, ImageProvider, ImageType
from app.config import settings


logger = logging.getLogger(__name__)


class PexelsService(BaseImageProvider):
    """
    Pexels 图片服务实现

    特点：
    - 高质量免费图片库
    - 正文配图首选
    - 仅用于 photo/illustration 类型

    API 文档：https://www.pexels.com/api/documentation/
    """

    # Pexels API 端点
    SEARCH_API_URL = "https://api.pexels.com/v1/search"
    PHOTO_API_URL = "https://api.pexels.com/v1/photos"

    # 默认搜索参数
    DEFAULT_PER_PAGE = 15
    DEFAULT_PAGE = 1

    def __init__(self):
        """初始化 Pexels 服务"""
        super().__init__(ImageProvider.PEXELS)

        # 从 settings 读取配置
        self.api_key = settings.PEXELS_API_KEY

        # 检查配置
        if not self.api_key or self.api_key == "your_pexels_api_key_here":
            logger.warning(
                "[PexelsService] API Key 未配置或使用占位符，服务不可用"
            )
            self._available = False
        else:
            self._available = True
            logger.info("[PexelsService] API Key 已配置，服务可用")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    def supports_image_type(self, image_type: ImageType) -> bool:
        """
        Pexels 仅支持照片和插图类型

        Args:
            image_type: 图片类型

        Returns:
            True 仅当类型为 photo 或 illustration
        """
        supported_types = [ImageType.PHOTO, ImageType.ILLUSTRATION]
        return image_type in supported_types

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        """
        从 Pexels 搜索并获取图片

        Args:
            keywords: 搜索关键词列表
            image_type: 图片类型（必须是 photo 或 illustration）
            width: 目标宽度
            height: 目标高度

        Returns:
            ImageFetchResult: 获取结果
        """
        self.log_fetch_attempt(keywords, image_type, width, height)

        if not self.is_available():
            return ImageFetchResult(
                url="",
                provider=ImageProvider.PEXELS,
                success=False,
                error="Pexels API Key 未配置"
            )

        # 类型检查
        if not self.supports_image_type(image_type):
            return ImageFetchResult(
                url="",
                provider=ImageProvider.PEXELS,
                success=False,
                error=f"Pexels 不支持图片类型: {image_type.value}"
            )

        start_time = time.time()

        try:
            # 构建搜索查询
            query = self._build_search_query(keywords)

            # 搜索图片
            photo_id = await self._search_photo(query, width, height)

            if not photo_id:
                return ImageFetchResult(
                    url="",
                    provider=ImageProvider.PEXELS,
                    success=False,
                    error="未找到匹配的图片"
                )

            # 获取图片详情
            photo_data = await self._get_photo_detail(photo_id)

            # 选择合适的图片尺寸
            image_url = self._select_image_size(photo_data, width, height)

            latency = (time.time() - start_time) * 1000
            self.log_fetch_success(image_url, width, height, latency)

            return ImageFetchResult(
                url=image_url,
                provider=ImageProvider.PEXELS,
                width=photo_data.get("width", width),
                height=photo_data.get("height", height),
                sourceId=str(photo_id),
                success=True,
                meta={
                    "photographer": photo_data.get("photographer"),
                    "photographer_url": photo_data.get("photographer_url"),
                    "avg_color": photo_data.get("avg_color"),
                    "latency_ms": latency,
                }
            )

        except Exception as e:
            self.log_fetch_error(str(e))
            return ImageFetchResult(
                url="",
                provider=ImageProvider.PEXELS,
                success=False,
                error=str(e)
            )

    def _build_search_query(self, keywords: list[str]) -> str:
        """
        构建搜索查询字符串

        Args:
            keywords: 关键词列表

        Returns:
            搜索查询字符串
        """
        # 使用第一个关键词作为主查询
        # 可以添加更多关键词作为补充
        if not keywords:
            return "nature"

        # 使用空格连接关键词（Pexels 支持）
        query = " ".join(keywords[:3])

        # 根据图片类型添加修饰词
        # photo 类型不需要额外修饰

        return query

    async def _search_photo(
        self,
        query: str,
        target_width: int,
        target_height: int
    ) -> Optional[int]:
        """
        搜索图片并返回第一个合适的图片ID

        Args:
            query: 搜索查询
            target_width: 目标宽度
            target_height: 目标高度

        Returns:
            图片ID 或 None
        """
        headers = {"Authorization": self.api_key}

        params = {
            "query": query,
            "per_page": self.DEFAULT_PER_PAGE,
            "page": self.DEFAULT_PAGE,
            # 可选：按方向筛选
            # "orientation": "landscape" if target_width > target_height else "portrait"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.SEARCH_API_URL,
                headers=headers,
                params=params
            )

            if response.status_code != 200:
                logger.warning(
                    f"[PexelsService] 搜索请求失败: status={response.status_code}"
                )
                return None

            data = response.json()
            photos = data.get("photos", [])

            if not photos:
                logger.warning(f"[PexelsService] 未找到图片: query={query}")
                return None

            # 选择第一个图片（或选择尺寸最合适的）
            # 这里简单选择第一个
            return photos[0].get("id")

    async def _get_photo_detail(self, photo_id: int) -> dict:
        """
        获取图片详情

        Args:
            photo_id: 图片ID

        Returns:
            图片详情字典
        """
        headers = {"Authorization": self.api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.PHOTO_API_URL}/{photo_id}",
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f"获取图片详情失败: status={response.status_code}")

            return response.json()

    def _select_image_size(
        self,
        photo_data: dict,
        target_width: int,
        target_height: int
    ) -> str:
        """
        从图片尺寸列表中选择合适的尺寸

        Pexels 提供多种尺寸：
        - original: 原图
        - large: 大图 (通常 1200x800 左右)
        - medium: 中图
        - small: 小图

        Args:
            photo_data: 图片详情数据
            target_width: 目标宽度
            target_height: 目标高度

        Returns:
            图片URL
        """
        src = photo_data.get("src", {})

        # 优先使用 large 尺寸（接近 1200x800）
        # 如果需要更大，使用 original
        if target_width >= 1500:
            return src.get("original", src.get("large", ""))

        # 默认使用 large
        return src.get("large", src.get("medium", src.get("original", "")))


# ============ Mock 实现（用于测试） ============


class MockPexelsService(BaseImageProvider):
    """
    Mock Pexels 服务

    用于单元测试，返回模拟图片URL
    """

    MOCK_IMAGE_URL = "https://images.pexels.com/photos/12345/mock-image.jpeg"

    def __init__(self):
        super().__init__(ImageProvider.PEXELS)
        self._available = True

    def is_available(self) -> bool:
        return self._available

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        await asyncio.sleep(0.1)  # 模拟延迟

        return ImageFetchResult(
            url=self.MOCK_IMAGE_URL,
            provider=ImageProvider.PEXELS,
            width=width,
            height=height,
            sourceId="mock-photo-12345",
            success=True,
            meta={"mock": True}
        )


# ============ 工厂函数 ============


def create_pexels_service(use_mock: bool = False) -> BaseImageProvider:
    """
    创建 Pexels 服务实例

    Args:
        use_mock: 是否使用 Mock 实现

    Returns:
        Pexels 服务实例
    """
    if use_mock:
        return MockPexelsService()
    return PexelsService()