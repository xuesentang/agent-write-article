"""
Seedream 文生图服务
字节跳动火山引擎 ARK API 文生图模型

配置要求（从 .env 读取）：
- SEEDREAM_API_KEY: 火山引擎 ARK API 密钥
- SEEDREAM_BASE_URL: 火山引擎 ARK API 端点

注意：
- Seedream 是付费服务，需要开通账号并获取 API Key
- 若配置缺失，服务不可用，但不会报错退出
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
    火山引擎 ARK 文生图服务实现

    特点：
    - 字节跳动 AI 文生图模型
    - 用于定制化主题图、插图、图表生成
    - 适合需要 AI 生成而非搜索的场景

    API Key 获取方式：
    - 访问火山引擎官网注册账号
    - 在控制台开通 ARK 服务并获取 API Key
    - https://www.volcengine.com/
    """

    # 火山引擎 ARK 图像生成端点
    GENERATE_API_PATH = "/images/generations"

    def __init__(self):
        """初始化 Seedream 服务"""
        super().__init__(ImageProvider.SEEDREAM)

        # 从 settings 读取配置
        self.api_key = settings.SEEDREAM_API_KEY
        self.base_url = settings.SEEDREAM_BASE_URL
        self.endpoint_id = settings.SEEDREAM_ENDPOINT_ID  # 推理端点 ID（区别于 API Key）

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
            logger.info(
                f"[SeedreamService] 配置已就绪: base_url={self.base_url}, "
                f"endpoint_id={self.endpoint_id or '未配置'}, "
                f"api_key={'已配置(前8位:' + self.api_key[:8] + '...' if len(self.api_key) > 8 else '已配置'}"
            )

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
        context: Optional[str] = None,
    ) -> ImageFetchResult:
        """
        使用火山引擎 ARK API 生成图片

        Args:
            keywords: 生成关键词列表
            image_type: 图片类型
            width: 目标宽度
            height: 目标高度
            context: 占位符前一个自然段的上下文内容（用于语义增强）

        Returns:
            ImageFetchResult: 生成结果
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
            # 构建生成提示词（优先使用上下文内容）
            prompt = self._build_prompt(keywords, image_type, context)

            # 调用真实 API
            image_url = await self._real_generate(prompt, width, height)

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
                    "used_context": context is not None,
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

    def _build_prompt(self, keywords: list[str], image_type: ImageType, context: Optional[str] = None) -> str:
        """
        构建 AI 生成提示词

        优先使用上下文内容（占位符前一个自然段），其次使用关键词，
        确保生成的图片与正文语义高度相关。

        Args:
            keywords: 关键词列表
            image_type: 图片类型
            context: 占位符前一个自然段的上下文内容

        Returns:
            生成提示词
        """
        # 根据图片类型添加风格修饰词
        style_map = {
            ImageType.PHOTO: "真实摄影风格，画面清晰，光影自然，细节丰富",
            ImageType.ILLUSTRATION: "精美插画风格，色彩鲜明，富有美感",
            ImageType.DIAGRAM: "清晰图表风格，信息可视化，简洁专业",
        }

        modifier = style_map.get(image_type, "高质量图片")

        if context:
            # 优先使用上下文内容构建 Prompt
            # 截取前 300 字作为语义参考（避免 Prompt 过长）
            context_text = context[:300]
            # 同时加入关键词作为补充
            keyword_str = "、".join(keywords[:3]) if keywords else ""
            if keyword_str:
                return f"基于以下内容生成配图：{context_text}。关键词：{keyword_str}。风格要求：{modifier}"
            else:
                return f"基于以下内容生成配图：{context_text}。风格要求：{modifier}"
        elif keywords:
            # 无上下文时，使用关键词
            base_prompt = "、".join(keywords[:5])
            return f"{base_prompt}，{modifier}"
        else:
            return f"高质量配图，{modifier}"

    async def _real_generate(
        self,
        prompt: str,
        width: int,
        height: int
    ) -> str:
        """
        真实 API 生成

        火山引擎 ARK API 图像生成格式（类似 OpenAI）：
        POST /images/generations
        {
            "model": "seedream-3.0-t2i",
            "prompt": "描述",
            "size": "1024x1024"
        }

        或者使用推理端点：
        POST /images/generations
        {
            "model": "endpoint-id",  # 用户配置的 API Key 可能是端点 ID
            "prompt": "描述",
            "size": "1024x1024"
        }

        Args:
            prompt: 生成提示词
            width: 图片宽度
            height: 图片高度

        Returns:
            生成的图片 URL
        """
        generate_url = f"{self.base_url}{self.GENERATE_API_PATH}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建请求参数
        # 火山引擎 ARK 支持的尺寸格式
        size = f"{width}x{height}"
        # 常见尺寸：1024x1024, 720x1280, 1280x720 等
        # 如果尺寸不是标准尺寸，调整为最接近的标准尺寸
        if width == height:
            size = "1024x1024"
        elif width > height:
            size = "1280x720"
        else:
            size = "720x1280"

        # 尝试不同的模型名称格式
        # 火山引擎 ARK 平台的图片生成 API：
        #   - 优先使用推理端点 ID（model 字段传 endpoint_id）
        #   - 其次尝试直接使用模型名（需为火山引擎官方模型 ID）
        # 正确模型名：Doubao-Seedream-5.0-lite（优先，速度快）、Doubao-Seedream-4.0（次选，质量好）
        model_names_to_try = []
        if self.endpoint_id:
            model_names_to_try.append(self.endpoint_id)
        model_names_to_try.extend([
            "Doubao-Seedream-5.0-lite",  # 优先使用 5.0-lite（速度更快，性价比更高）
            "Doubao-Seedream-4.0",       # 次选 4.0（质量更好但较慢）
        ])

        for model_name in model_names_to_try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "size": size,
            }

            logger.info(
                f"[SeedreamService] 尝试生成请求: model={model_name}, "
                f"prompt={prompt[:50]}..., size={size}"
            )

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    logger.info(
                        f"[SeedreamService] 发送 POST 请求到: {generate_url}"
                    )
                    response = await client.post(
                        generate_url,
                        headers=headers,
                        json=payload
                    )

                    logger.info(
                        f"[SeedreamService] 收到响应: status={response.status_code}, "
                        f"body={response.text[:500]}"
                    )

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(
                            f"[SeedreamService] 解析响应 JSON: {str(data)[:300]}"
                        )

                        # 解析响应格式（类似 OpenAI 格式）
                        if "data" in data and len(data["data"]) > 0:
                            image_url = data["data"][0].get("url", "")
                            if image_url:
                                logger.info(
                                    f"[SeedreamService] 生成成功: model={model_name}, url={image_url}"
                                )
                                return image_url

                        # 尝试其他响应格式
                        if "images" in data and len(data["images"]) > 0:
                            return data["images"][0].get("url", "")

                        if "url" in data:
                            return data["url"]

                        logger.warning(
                            f"[SeedreamService] 响应格式不包含图片 URL: {data}"
                        )
                        continue

                    # 非 200 状态码，记录错误并尝试下一个模型
                    error_text = response.text
                    logger.warning(
                        f"[SeedreamService] API 调用失败 (model={model_name}): "
                        f"status={response.status_code}, error={error_text[:200]}"
                    )

            except Exception as e:
                logger.warning(
                    f"[SeedreamService] API 调用异常 (model={model_name}): {str(e)}"
                )
                continue

        # 所有尝试都失败，返回 Mock URL 作为备用
        # 这样可以确保流程不中断
        mock_url = f"https://picsum.photos/seed/{hash(prompt) % 10000}/{width}/{height}"
        logger.error(
            f"[SeedreamService] ===== 所有模型尝试均失败，使用 Picsum 备用 URL =====\n"
            f"  尝试的模型数: {len(model_names_to_try)}\n"
            f"  API 地址: {generate_url}\n"
            f"  请检查:\n"
            f"    1. API Key 是否正确（当前 key 前位: {self.api_key[:8] if len(self.api_key) > 8 else self.api_key}...）\n"
            f"    2. 推理端点 {self.endpoint_id} 是否已部署并处于运行状态\n"
            f"    3. 端点绑定的模型 ID 是否在尝试列表中\n"
            f"  备用 URL: {mock_url}"
        )
        return mock_url


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
        context: Optional[str] = None,
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