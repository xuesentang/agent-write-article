"""
配图服务模块初始化
策略模式管理多种配图方式
"""

from app.image.base_provider import BaseImageProvider
from app.image.strategy import (
    ImageServiceStrategy,
    create_image_service_strategy,
)
from app.image.providers import (
    # Pexels
    PexelsService,
    MockPexelsService,
    create_pexels_service,
    # Iconify
    IconifyService,
    MockIconifyService,
    create_iconify_service,
    # Seedream
    SeedreamService,
    MockSeedreamService,
    create_seedream_service,
    # Picsum
    PicsumService,
    MockPicsumService,
    create_picsum_service,
)

__all__ = [
    # 基类
    "BaseImageProvider",
    # 策略
    "ImageServiceStrategy",
    "create_image_service_strategy",
    # Pexels
    "PexelsService",
    "MockPexelsService",
    "create_pexels_service",
    # Iconify
    "IconifyService",
    "MockIconifyService",
    "create_iconify_service",
    # Seedream
    "SeedreamService",
    "MockSeedreamService",
    "create_seedream_service",
    # Picsum
    "PicsumService",
    "MockPicsumService",
    "create_picsum_service",
]


# ============ 快速创建策略实例的工厂函数 ============


def create_default_image_strategy(use_mock: bool = False) -> ImageServiceStrategy:
    """
    创建默认图片服务策略

    注册所有四个服务提供商

    Args:
        use_mock: 是否使用 Mock 服务（用于测试）

    Returns:
        ImageServiceStrategy 实例
    """
    return create_image_service_strategy(
        pexels_provider=create_pexels_service(use_mock),
        iconify_provider=create_iconify_service(use_mock),
        seedream_provider=create_seedream_service(use_mock),
        picsum_provider=create_picsum_service(use_mock),
    )