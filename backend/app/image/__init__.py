"""
配图服务模块初始化
策略模式管理多种配图方式
"""

import logging

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

logger = logging.getLogger(__name__)

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
    创建简化图片服务策略

    仅使用 Seedream 作为唯一图片源，无兜底服务。

    Args:
        use_mock: 是否使用 Mock 服务（用于测试）

    Returns:
        ImageServiceStrategy 实例
    """
    logger.info(f"[ImageStrategy] 创建 Seedream-only 图片策略，use_mock={use_mock}")

    try:
        seedream = create_seedream_service(use_mock)
        logger.info(f"[ImageStrategy] Seedream 服务创建完成, available={seedream.is_available() if seedream else 'None'}")
    except Exception as e:
        logger.warning(f"[ImageStrategy] 创建 Seedream 服务失败: {e}")
        seedream = None

    # 仅注册 Seedream
    strategy = create_image_service_strategy(
        seedream_provider=seedream,
    )

    logger.info(f"[ImageStrategy] 图片策略创建完成, 可用服务: {strategy.get_available_providers()}")
    return strategy