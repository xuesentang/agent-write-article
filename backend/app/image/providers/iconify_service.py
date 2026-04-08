"""
Iconify 图标服务
仅用于图标/装饰类元素，绝对禁止用于正文主图

配置要求（从 .env 读取）：
- ICONIFY_API_URL: Iconify API 端点（默认：https://api.iconify.design）

注意：Iconify 是免费的图标 API，无需 API Key
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.image.base_provider import BaseImageProvider
from app.schemas.image import ImageFetchResult, ImageProvider, ImageType
from app.config import settings


logger = logging.getLogger(__name__)


class IconifyService(BaseImageProvider):
    """
    Iconify 图标服务实现

    特点：
    - 免费图标 API
    - 仅限用于 icon/decorative 类型
    - **硬性规则：绝对禁止用于正文主图**

    API 文档：https://iconify.design/docs/api/
    """

    # Iconify API 端点
    SEARCH_API_URL = "/search"

    # 支持的图标集合（优先选择）
    PREFERRED_ICON_SETS = [
        "mdi",        # Material Design Icons
        "carbon",     # Carbon Design System
        "tabler",     # Tabler Icons
        "heroicons",  # Heroicons
        "fa",         # Font Awesome
    ]

    def __init__(self):
        """初始化 Iconify 服务"""
        super().__init__(ImageProvider.ICONIFY)

        # 从 settings 读取配置
        self.api_url = settings.ICONIFY_API_URL

        # Iconify 无需 API Key，检查 URL 是否配置
        if not self.api_url:
            logger.warning("[IconifyService] API URL 未配置，服务不可用")
            self._available = False
        else:
            self._available = True
            logger.info(f"[IconifyService] API URL 已配置: {self.api_url}")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    def supports_image_type(self, image_type: ImageType) -> bool:
        """
        Iconify 仅支持图标和装饰类型

        **硬性规则：禁止用于 photo/illustration/diagram**

        Args:
            image_type: 图片类型

        Returns:
            True 仅当类型为 icon 或 decorative
        """
        # 只有 icon 和 decorative 类型可以使用 Iconify
        supported_types = [ImageType.ICON, ImageType.DECORATIVE]
        if image_type not in supported_types:
            logger.warning(
                f"[IconifyService] 禁止用于正文主图类型: {image_type.value}"
            )
            return False
        return True

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        """
        从 Iconify 搜索并获取图标

        Args:
            keywords: 搜索关键词列表
            image_type: 图片类型（必须是 icon 或 decorative）
            width: 目标宽度（图标尺寸）
            height: 目标高度（图标尺寸）

        Returns:
            ImageFetchResult: 获取结果

        注意：
            Iconify 返回的是 SVG 图标 URL，不是照片
        """
        self.log_fetch_attempt(keywords, image_type, width, height)

        if not self.is_available():
            return ImageFetchResult(
                url="",
                provider=ImageProvider.ICONIFY,
                success=False,
                error="Iconify API URL 未配置"
            )

        # 硬性类型检查
        if not self.supports_image_type(image_type):
            return ImageFetchResult(
                url="",
                provider=ImageProvider.ICONIFY,
                success=False,
                error="Iconify 禁止用于正文主图，仅限 icon/decorative 类型"
            )

        start_time = time.time()

        try:
            # 构建搜索查询
            query = self._build_search_query(keywords)

            # 搜索图标
            icon_data = await self._search_icon(query)

            if not icon_data:
                return ImageFetchResult(
                    url="",
                    provider=ImageProvider.ICONIFY,
                    success=False,
                    error="未找到匹配的图标"
                )

            # 构建图标 SVG URL
            icon_url = self._build_icon_url(icon_data, width)

            latency = (time.time() - start_time) * 1000
            self.log_fetch_success(icon_url, width, height, latency)

            return ImageFetchResult(
                url=icon_url,
                provider=ImageProvider.ICONIFY,
                width=width,
                height=height,  # 图标通常宽高相同
                sourceId=icon_data.get("icon", ""),
                success=True,
                meta={
                    "iconSet": icon_data.get("prefix"),
                    "iconName": icon_data.get("icon"),
                    "latency_ms": latency,
                }
            )

        except Exception as e:
            self.log_fetch_error(str(e))
            return ImageFetchResult(
                url="",
                provider=ImageProvider.ICONIFY,
                success=False,
                error=str(e)
            )

    def _build_search_query(self, keywords: list[str]) -> str:
        """
        构建图标搜索查询

        Args:
            keywords: 关键词列表

        Returns:
            搜索查询字符串
        """
        if not keywords:
            return "star"  # 默认图标

        # 使用第一个关键词
        return keywords[0].lower()

    async def _search_icon(self, query: str) -> Optional[dict]:
        """
        搜索图标

        Args:
            query: 搜索查询

        Returns:
            图标数据字典 或 None
        """
        search_url = f"{self.api_url}{self.SEARCH_API_URL}"

        params = {
            "query": query,
            "limit": 20,  # 返回结果数量
            "prefixes": ",".join(self.PREFERRED_ICON_SETS),  # 优先图标集
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(search_url, params=params)

            if response.status_code != 200:
                logger.warning(
                    f"[IconifyService] 搜索请求失败: status={response.status_code}"
                )
                return None

            data = response.json()
            icons = data.get("icons", [])

            if not icons:
                logger.warning(f"[IconifyService] 未找到图标: query={query}")
                return None

            # 选择第一个图标
            first_icon = icons[0]

            # 解析图标信息（格式如 "mdi:star"）
            icon_full = first_icon.get("icon", "")
            if ":" in icon_full:
                prefix, name = icon_full.split(":")
            else:
                prefix = self.PREFERRED_ICON_SETS[0]
                name = icon_full

            return {
                "prefix": prefix,
                "icon": name,
                "full": icon_full
            }

    def _build_icon_url(self, icon_data: dict, size: int) -> str:
        """
        构建图标 SVG URL

        Iconify SVG API 格式：
        https://api.iconify.design/{prefix}/{name}.svg?width={size}

        Args:
            icon_data: 图标数据
            size: 图标尺寸

        Returns:
            SVG URL
        """
        prefix = icon_data.get("prefix")
        name = icon_data.get("icon")

        # 构建 SVG URL
        url = f"{self.api_url}/{prefix}/{name}.svg?width={size}&height={size}"

        return url


# ============ Mock 实现（用于测试） ============


class MockIconifyService(BaseImageProvider):
    """
    Mock Iconify 服务

    用于单元测试，返回模拟图标URL
    """

    MOCK_ICON_URL = "https://api.iconify.design/mdi/star.svg?width=1200&height=1200"

    def __init__(self):
        super().__init__(ImageProvider.ICONIFY)
        self._available = True

    def is_available(self) -> bool:
        return self._available

    def supports_image_type(self, image_type: ImageType) -> bool:
        # Mock 也遵守硬性规则
        return image_type in [ImageType.ICON, ImageType.DECORATIVE]

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        # 模拟类型检查
        if not self.supports_image_type(image_type):
            return ImageFetchResult(
                url="",
                provider=ImageProvider.ICONIFY,
                success=False,
                error="Iconify 禁止用于正文主图"
            )

        await asyncio.sleep(0.1)

        return ImageFetchResult(
            url=self.MOCK_ICON_URL,
            provider=ImageProvider.ICONIFY,
            width=width,
            height=height,
            sourceId="mdi:star",
            success=True,
            meta={"mock": True}
        )


# ============ 工厂函数 ============


def create_iconify_service(use_mock: bool = False) -> BaseImageProvider:
    """
    创建 Iconify 服务实例

    Args:
        use_mock: 是否使用 Mock 实现

    Returns:
        Iconify 服务实例
    """
    if use_mock:
        return MockIconifyService()
    return IconifyService()