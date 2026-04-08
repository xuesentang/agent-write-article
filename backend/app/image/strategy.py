"""
图片服务策略
根据任务类型、关键词、可用性、失败重试状态选择具体服务
"""

import logging
from typing import Optional, Tuple

from app.schemas.image import ImageTask, ImageFetchResult, ImageProvider, ImageType, ImageTaskStatus
from app.image.base_provider import BaseImageProvider


logger = logging.getLogger(__name__)


class ImageServiceStrategy:
    """
    图片服务策略总管

    负责根据任务属性选择合适的图片服务提供商。
    核心决策逻辑：
    - 根据 imageType 选择首选服务
    - 根据 preferredProviders/fallbackProviders 降级
    - 检查服务可用性
    - 处理重试和失败状态

    硬性规则：
    - Iconify 仅限用于 icon/decorative 类型，绝对禁止正文主图
    - 单图失败不阻塞整体流程
    """

    # 服务提供商实例（由外部注入）
    _providers: dict[ImageProvider, BaseImageProvider] = {}

    def __init__(
        self,
        pexels_provider: Optional[BaseImageProvider] = None,
        iconify_provider: Optional[BaseImageProvider] = None,
        seedream_provider: Optional[BaseImageProvider] = None,
        picsum_provider: Optional[BaseImageProvider] = None,
    ):
        """
        初始化服务策略

        Args:
            pexels_provider: Pexels 服务实例
            iconify_provider: Iconify 服务实例
            seedream_provider: Seedream 服务实例
            picsum_provider: Picsum 服务实例
        """
        # 注册提供商
        if pexels_provider:
            self._providers[ImageProvider.PEXELS] = pexels_provider
        if iconify_provider:
            self._providers[ImageProvider.ICONIFY] = iconify_provider
        if seedream_provider:
            self._providers[ImageProvider.SEEDREAM] = seedream_provider
        if picsum_provider:
            self._providers[ImageProvider.PICSUM] = picsum_provider

        logger.info(
            f"[ImageServiceStrategy] 初始化完成，已注册 "
            f"{len(self._providers)} 个服务提供商"
        )

    def register_provider(self, provider: BaseImageProvider):
        """
        注册服务提供商

        Args:
            provider: 服务提供商实例
        """
        self._providers[provider.get_provider_name()] = provider
        logger.info(f"[ImageServiceStrategy] 注册服务: {provider.get_provider_name().value}")

    def get_provider(self, provider_name: ImageProvider) -> Optional[BaseImageProvider]:
        """
        获取服务提供商实例

        Args:
            provider_name: 提供商名称

        Returns:
            服务实例或 None
        """
        return self._providers.get(provider_name)

    def select_provider(
        self,
        task: ImageTask,
        exclude_failed: list[ImageProvider] = None
    ) -> Optional[BaseImageProvider]:
        """
        根据任务选择服务提供商

        Args:
            task: 图片任务
            exclude_failed: 需排除的失败服务列表

        Returns:
            选中的服务提供商实例

        决策流程：
        1. 检查 imageType 限制（Iconify 仅限 icon/decorative）
        2. 从 preferredProviders 中选择（排除已失败的）
        3. 检查服务可用性
        4. 如果首选都不可用，降级到 fallbackProviders
        """
        exclude_failed = exclude_failed or []

        # 硬性规则：Iconify 仅限 icon/decorative
        if task.imageType in [ImageType.PHOTO, ImageType.ILLUSTRATION, ImageType.DIAGRAM]:
            # 正文主图相关类型，排除 Iconify
            if ImageProvider.ICONIFY not in exclude_failed:
                exclude_failed.append(ImageProvider.ICONIFY)

        # 首选服务列表（排除已失败的）
        preferred = [
            p for p in task.preferredProviders
            if p not in exclude_failed
        ]

        # 尝试首选服务
        for provider_name in preferred:
            provider = self._providers.get(provider_name)
            if provider and provider.is_available():
                # 再次检查类型支持
                if provider.supports_image_type(task.imageType):
                    logger.info(
                        f"[ImageServiceStrategy] 为任务 {task.placeholderId} "
                        f"选择首选服务: {provider_name.value}"
                    )
                    return provider

        # 首选服务都不可用，降级到 fallback
        fallback = [
            p for p in task.fallbackProviders
            if p not in exclude_failed
        ]

        for provider_name in fallback:
            provider = self._providers.get(provider_name)
            if provider and provider.is_available():
                logger.info(
                    f"[ImageServiceStrategy] 为任务 {task.placeholderId} "
                    f"降级到备选服务: {provider_name.value}"
                )
                return provider

        # 最后兜底：Picsum（如果注册了）
        picsum = self._providers.get(ImageProvider.PICSUM)
        if picsum and picsum.is_available():
            logger.warning(
                f"[ImageServiceStrategy] 为任务 {task.placeholderId} "
                f"强制使用 Picsum 兜底"
            )
            return picsum

        # 无可用服务
        logger.error(
            f"[ImageServiceStrategy] 无可用服务提供商，"
            f"任务 {task.placeholderId} 将失败"
        )
        return None

    async def fetch_with_retry(
        self,
        task: ImageTask,
        max_retries: int = 3
    ) -> ImageFetchResult:
        """
        带重试机制的图片获取

        Args:
            task: 图片任务
            max_retries: 最大重试次数

        Returns:
            ImageFetchResult: 最终结果（成功或失败）

        重试流程：
        1. 选择首选服务，尝试获取
        2. 失败后记录失败服务，选择下一个首选
        3. 首选全部失败后，降级到 fallback
        4. fallback 全部失败后，强制 Picsum
        5. Picsum 也失败（理论上不会），返回错误结果
        """
        failed_providers: list[ImageProvider] = []
        last_error: Optional[str] = None

        for retry in range(max_retries + 1):
            # 选择提供商（排除已失败的）
            provider = self.select_provider(task, failed_providers)

            if not provider:
                # 无可用服务
                break

            # 尝试获取图片
            try:
                result = await provider.fetch_image(
                    keywords=task.keywords,
                    image_type=task.imageType,
                    width=1200,
                    height=800
                )

                if result.success:
                    logger.info(
                        f"[ImageServiceStrategy] 任务 {task.placeholderId} "
                        f"获取成功，使用 {result.provider.value}"
                    )
                    return result

                # 获取失败（但没抛异常）
                last_error = result.error or "未知错误"
                failed_providers.append(provider.get_provider_name())
                logger.warning(
                    f"[ImageServiceStrategy] 任务 {task.placeholderId} "
                    f"获取失败 (retry {retry}): {last_error}"
                )

            except Exception as e:
                last_error = str(e)
                failed_providers.append(provider.get_provider_name())
                logger.warning(
                    f"[ImageServiceStrategy] 任务 {task.placeholderId} "
                    f"获取异常 (retry {retry}): {e}"
                )

        # 所有尝试都失败，返回错误结果
        return ImageFetchResult(
            url="",
            provider=ImageProvider.PICSUM,  # 标记为兜底
            width=1200,
            height=800,
            success=False,
            error=f"所有服务均失败: {last_error}"
        )

    def get_available_providers(self) -> list[ImageProvider]:
        """
        获取所有可用的服务提供商列表

        Returns:
            可用提供商列表
        """
        available = []
        for name, provider in self._providers.items():
            if provider.is_available():
                available.append(name)
        return available

    def get_provider_status(self) -> dict:
        """
        获取所有服务提供商的状态

        Returns:
            状态字典 {provider_name: available}
        """
        status = {}
        for name, provider in self._providers.items():
            status[name.value] = {
                "available": provider.is_available(),
                "name": name.value
            }
        return status


# ============ 工厂函数 ============


def create_image_service_strategy(
    pexels_provider: Optional[BaseImageProvider] = None,
    iconify_provider: Optional[BaseImageProvider] = None,
    seedream_provider: Optional[BaseImageProvider] = None,
    picsum_provider: Optional[BaseImageProvider] = None,
) -> ImageServiceStrategy:
    """
    创建图片服务策略实例

    Args:
        各服务提供商实例

    Returns:
        ImageServiceStrategy 实例
    """
    return ImageServiceStrategy(
        pexels_provider=pexels_provider,
        iconify_provider=iconify_provider,
        seedream_provider=seedream_provider,
        picsum_provider=picsum_provider,
    )