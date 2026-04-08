"""
Picsum 随机图服务
最终兜底服务，提供随机高质量图片

特点：
- 无需 API Key，完全免费
- 作为所有服务失败后的最终兜底
- 图片质量随机，但保证可用
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional

import httpx

from app.image.base_provider import BaseImageProvider
from app.schemas.image import ImageFetchResult, ImageProvider, ImageType
from app.config import settings


logger = logging.getLogger(__name__)


class PicsumService(BaseImageProvider):
    """
    Picsum 随机图服务实现

    特点：
    - Lorem Picsum 提供的随机图片服务
    - 无需 API Key，完全免费
    - 用于所有其他服务失败后的最终兜底
    - 永不失败（除非网络问题）

    API 文档：https://picsum.photos/
    """

    # Picsum API 端点
    BASE_URL = "https://picsum.photos"

    # 图片 ID 范围（Picsum 有固定数量的图片）
    MAX_IMAGE_ID = 1000

    def __init__(self):
        """初始化 Picsum 服务"""
        super().__init__(ImageProvider.PICSUM)

        # Picsum 无需配置，始终可用
        self._available = True
        logger.info("[PicsumService] 服务初始化完成，始终可用（兜底服务）")

    def is_available(self) -> bool:
        """检查服务是否可用（始终返回 True）"""
        return self._available

    def supports_image_type(self, image_type: ImageType) -> bool:
        """
        Picsum 支持所有图片类型（作为兜底）

        Args:
            image_type: 图片类型

        Returns:
            True（始终支持）
        """
        return True  # 作为兜底服务，支持所有类型

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        """
        从 Picsum 获取随机图片

        Args:
            keywords: 关键词列表（用于生成种子，保证一致性）
            image_type: 图片类型
            width: 目标宽度
            height: 目标高度

        Returns:
            ImageFetchResult: 获取结果（永不失败）

        注意：
            Picsum 图片是随机的，但可以通过 seed 保证一致性
        """
        self.log_fetch_attempt(keywords, image_type, width, height)

        start_time = time.time()

        try:
            # 使用关键词生成种子（保证相同关键词返回相同图片）
            seed = self._generate_seed(keywords)

            # 构建图片 URL
            image_url = self._build_url(seed, width, height)

            # 验证 URL 可访问性（可选）
            is_valid = await self._validate_url(image_url)

            latency = (time.time() - start_time) * 1000

            if is_valid:
                self.log_fetch_success(image_url, width, height, latency)
                return ImageFetchResult(
                    url=image_url,
                    provider=ImageProvider.PICSUM,
                    width=width,
                    height=height,
                    sourceId=str(seed),
                    success=True,
                    meta={
                        "seed": seed,
                        "keywords_based": bool(keywords),
                        "latency_ms": latency,
                    }
                )
            else:
                # URL 不可访问，使用备用 URL
                fallback_url = self._build_fallback_url(width, height)
                self.log_fetch_success(fallback_url, width, height, latency)
                return ImageFetchResult(
                    url=fallback_url,
                    provider=ImageProvider.PICSUM,
                    width=width,
                    height=height,
                    sourceId="fallback",
                    success=True,
                    meta={
                        "fallback": True,
                        "latency_ms": latency,
                    }
                )

        except Exception as e:
            # Picsum 作为兜底，即使出错也要返回一个 URL
            self.log_fetch_error(str(e))

            # 强制返回备用 URL（永不失败）
            fallback_url = self._build_fallback_url(width, height)
            logger.warning(
                f"[PicsumService] 强制兜底返回: {fallback_url}"
            )

            return ImageFetchResult(
                url=fallback_url,
                provider=ImageProvider.PICSUM,
                width=width,
                height=height,
                sourceId="forced_fallback",
                success=True,  # 强制标记为成功
                meta={
                    "forced": True,
                    "error": str(e),
                }
            )

    def _generate_seed(self, keywords: list[str]) -> int:
        """
        根据关键词生成种子值

        相同关键词会生成相同种子，保证一致性

        Args:
            keywords: 关键词列表

        Returns:
            种子值（0-999）
        """
        if not keywords:
            # 无关键词，使用时间戳生成随机种子
            return int(time.time() * 1000) % self.MAX_IMAGE_ID

        # 使用关键词生成 hash
        keywords_str = " ".join(keywords)
        hash_value = hashlib.md5(keywords_str.encode()).hexdigest()
        seed = int(hash_value[:8], 16) % self.MAX_IMAGE_ID

        return seed

    def _build_url(self, seed: int, width: int, height: int) -> str:
        """
        构建带种子的 Picsum URL

        URL 格式：https://picsum.photos/seed/{seed}/{width}/{height}

        Args:
            seed: 种子值
            width: 图片宽度
            height: 图片高度

        Returns:
            图片 URL
        """
        return f"{self.BASE_URL}/seed/{seed}/{width}/{height}"

    def _build_fallback_url(self, width: int, height: int) -> str:
        """
        构建备用 URL（无种子，随机图片）

        Args:
            width: 图片宽度
            height: 图片高度

        Returns:
            备用图片 URL
        """
        return f"{self.BASE_URL}/{width}/{height}"

    async def _validate_url(self, url: str) -> bool:
        """
        验证 URL 是否可访问

        Args:
            url: 图片 URL

        Returns:
            True 如果可访问，False 否则
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(url)
                return response.status_code == 200
        except Exception:
            return False


# ============ Mock 实现（用于测试） ============


class MockPicsumService(BaseImageProvider):
    """
    Mock Picsum 服务

    用于单元测试，返回模拟图片 URL
    """

    MOCK_IMAGE_URL = "https://picsum.photos/seed/mock/1200/800"

    def __init__(self):
        super().__init__(ImageProvider.PICSUM)
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
        await asyncio.sleep(0.05)

        return ImageFetchResult(
            url=self.MOCK_IMAGE_URL,
            provider=ImageProvider.PICSUM,
            width=width,
            height=height,
            sourceId="mock-picsum-12345",
            success=True,
            meta={"mock": True}
        )


# ============ 工厂函数 ============


def create_picsum_service(use_mock: bool = False) -> BaseImageProvider:
    """
    创建 Picsum 服务实例

    Args:
        use_mock: 是否使用 Mock 实现

    Returns:
        Picsum 服务实例
    """
    if use_mock:
        return MockPicsumService()
    return PicsumService()