"""
Seedream 文生图服务
字节跳动旗下的 AI 文生图模型，用于定制化主题图生成

配置要求（从 .env 读取）：
- SEEDREAM_API_KEY: Seedream API 密钥
- SEEDREAM_BASE_URL: Seedream API 端点

注意：
- Seedream 是付费服务，需要开通账号并获取 API Key
- 若配置缺失，服务不可用，但不会报错退出
- 请在注释中明确标注 API Key 获取方式
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


class SeedreamService(BaseImageProvider):
    """
    Seedream 文生图服务实现

    特点：
    - 字节跳动 AI 文生图模型
    - 用于定制化主题图、插图、图表生成
    - 适合需要 AI 生成而非搜索的场景

    API Key 获取方式：
    - 访问 Seedream 官网注册账号
    - 在控制台获取 API Key
    - 具体地址请咨询字节跳动官方

    注意：当前实现为 Mock 占位，真实 API 接入需要补充具体端点和参数
    """

    # Seedream API 端点（根据实际 API 文档调整）
    # TODO: 确认真实 API 端点路径
    GENERATE_API_PATH = "/generate"

    def __init__(self):
        """初始化 Seedream 服务"""
        super().__init__(ImageProvider.SEEDREAM)

        # 从 settings 读取配置
        self.api_key = settings.SEEDREAM_API_KEY
        self.base_url = settings.SEEDREAM_BASE_URL

        # 检查配置
        if not self.api_key or self.api_key == "your_seedream_api_key_here":
            logger.warning(
                "[SeedreamService] API Key 未配置或使用占位符，服务不可用"
            )
            self._available = False
        elif not self.base_url:
            logger.warning("[SeedreamService] Base URL 未配置，服务不可用")
            self._available = False
        else:
            self._available = True
            logger.info(f"[SeedreamService] 配置已就绪: {self.base_url}")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    def supports_image_type(self, image_type: ImageType) -> bool:
        """
        Seedream 支持多种图片类型

        适合：
        - photo: AI 生成照片风格图片
        - illustration: AI 生成插图
        - diagram: AI 生成图表/流程图

        不适合：
        - icon: 图标不适合 AI 生成
        - decorative: 装饰元素建议用 Iconify

        Args:
            image_type: 图片类型

        Returns:
            True 如果支持该类型
        """
        supported_types = [
            ImageType.PHOTO,
            ImageType.ILLUSTRATION,
            ImageType.DIAGRAM
        ]
        return image_type in supported_types

    async def fetch_image(
        self,
        keywords: list[str],
        image_type: ImageType,
        width: int = 1200,
        height: int = 800,
    ) -> ImageFetchResult:
        """
        使用 Seedream AI 生成图片

        Args:
            keywords: 生成关键词列表
            image_type: 图片类型
            width: 目标宽度
            height: 目标高度

        Returns:
            ImageFetchResult: 生成结果

        注意：当前为 Mock 实现，真实 API 接入需要：
        1. 确认 API 端点和请求格式
        2. 实现真实的 HTTP 请求
        3. 处理异步生成（可能需要轮询）
        """
        self.log_fetch_attempt(keywords, image_type, width, height)

        if not self.is_available():
            return ImageFetchResult(
                url="",
                provider=ImageProvider.SEEDREAM,
                success=False,
                error="Seedream API Key 或 Base URL 未配置"
            )

        if not self.supports_image_type(image_type):
            return ImageFetchResult(
                url="",
                provider=ImageProvider.SEEDREAM,
                success=False,
                error=f"Seedream 不支持图片类型: {image_type.value}"
            )

        start_time = time.time()

        try:
            # 构建生成提示词
            prompt = self._build_prompt(keywords, image_type)

            # TODO: 真实 API 调用
            # 当前返回 Mock 结果，真实实现需要：
            # 1. 调用 Seedream API 发起生成请求
            # 2. 获取任务 ID 或直接返回图片 URL
            # 3. 如果是异步生成，需要轮询等待结果

            # Mock 实现：返回占位 URL
            # 实际项目中应该调用真实 API
            image_url = await self._mock_generate(prompt, width, height)

            latency = (time.time() - start_time) * 1000
            self.log_fetch_success(image_url, width, height, latency)

            return ImageFetchResult(
                url=image_url,
                provider=ImageProvider.SEEDREAM,
                width=width,
                height=height,
                sourceId=f"seedream-{int(time.time())}",
                success=True,
                meta={
                    "prompt": prompt,
                    "imageType": image_type.value,
                    "latency_ms": latency,
                    "mock": True,  # 标记为 Mock 结果
                }
            )

        except Exception as e:
            self.log_fetch_error(str(e))
            return ImageFetchResult(
                url="",
                provider=ImageProvider.SEEDREAM,
                success=False,
                error=str(e)
            )

    def _build_prompt(self, keywords: list[str], image_type: ImageType) -> str:
        """
        构建 AI 生成提示词

        Args:
            keywords: 关键词列表
            image_type: 图片类型

        Returns:
            生成提示词
        """
        if not keywords:
            return "高质量图片，专业摄影风格"

        # 根据图片类型添加风格修饰词
        base_prompt = " ".join(keywords[:5])

        style_modifiers = {
            ImageType.PHOTO: "高质量照片，专业摄影，光影效果好",
            ImageType.ILLUSTRATION: "精美插图，艺术风格，色彩丰富",
            ImageType.DIAGRAM: "清晰图表，信息可视化，简洁设计",
        }

        modifier = style_modifiers.get(image_type, "")

        return f"{base_prompt}，{modifier}"

    async def _mock_generate(
        self,
        prompt: str,
        width: int,
        height: int
    ) -> str:
        """
        Mock 生成实现

        TODO: 替换为真实 API 调用

        真实实现参考流程：
        1. POST /generate 发起生成请求
        2. 获取任务 ID 或图片 URL
        3. 如果异步，轮询 /status/{task_id} 直到完成
        4. 返回最终图片 URL

        Args:
            prompt: 生成提示词
            width: 图片宽度
            height: 图片高度

        Returns:
            Mock 图片 URL
        """
        # 模拟生成延迟
        await asyncio.sleep(0.5)

        # 返回 Mock URL（使用 Picsum 作为占位）
        # 实际应该返回 Seedream API 生成的真实 URL
        mock_url = f"https://picsum.photos/seed/{hash(prompt) % 1000}/{width}/{height}"

        logger.info(
            f"[SeedreamService] Mock 生成完成: prompt={prompt[:30]}..., "
            f"url={mock_url}"
        )

        return mock_url

    async def _real_generate(
        self,
        prompt: str,
        width: int,
        height: int
    ) -> str:
        """
        真实 API 生成（TODO: 实现）

        当前未实现，需要根据 Seedream 官方 API 文档补充

        Args:
            prompt: 生成提示词
            width: 图片宽度
            height: 图片高度

        Returns:
            生成的图片 URL

        注意：
            - 需要确认 API 端点路径
            - 需要确认请求参数格式
            - 需要处理异步生成或直接返回
        """
        generate_url = f"{self.base_url}{self.GENERATE_API_PATH}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # TODO: 确认真实请求参数
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            # 其他参数需要根据 API 文档补充
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                generate_url,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"生成请求失败: status={response.status_code}")

            data = response.json()
            # TODO: 确认响应格式，提取图片 URL
            return data.get("image_url", "")


# ============ Mock 实现（用于测试） ============


class MockSeedreamService(BaseImageProvider):
    """
    Mock Seedream 服务

    用于单元测试，返回模拟生成图片 URL
    """

    MOCK_IMAGE_URL = "https://picsum.photos/seed/seedream/1200/800"

    def __init__(self):
        super().__init__(ImageProvider.SEEDREAM)
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
        await asyncio.sleep(0.3)

        return ImageFetchResult(
            url=self.MOCK_IMAGE_URL,
            provider=ImageProvider.SEEDREAM,
            width=width,
            height=height,
            sourceId="mock-seedream-12345",
            success=True,
            meta={"mock": True, "keywords": keywords}
        )


# ============ 工厂函数 ============


def create_seedream_service(use_mock: bool = False) -> BaseImageProvider:
    """
    创建 Seedream 服务实例

    Args:
        use_mock: 是否使用 Mock 实现

    Returns:
        Seedream 服务实例
    """
    if use_mock:
        return MockSeedreamService()
    return SeedreamService()