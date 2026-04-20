"""
图片相关模块单元测试
测试 Agent4、Agent5、服务策略层、COS上传
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.image_analyzer_agent import (
    ImageAnalyzerAgent,
    ImageAnalyzerInput,
    create_image_analyzer_agent,
    EXAMPLE_CONTENT_WITH_PLACEHOLDERS,
    EXAMPLE_CONTENT_NO_PLACEHOLDERS,
    EXAMPLE_CONTENT_INVALID_PLACEHOLDER,
)
from app.agents.image_generator_agent import (
    ImageGeneratorAgent,
    create_image_generator_agent,
)
from app.schemas.image import (
    ImageType,
    ImageProvider,
    ImageTaskStatus,
    ImageTask,
    ImageFetchResult,
    ImageResult,
    ImageGeneratorInput,
)
from app.image.strategy import ImageServiceStrategy, create_image_service_strategy
from app.image.providers.pexels_service import MockPexelsService
from app.image.providers.iconify_service import MockIconifyService
from app.image.providers.seedream_service import MockSeedreamService
from app.image.providers.picsum_service import MockPicsumService
from app.utils.cos_uploader import MockCOSUploader


# ============ Agent4 (ImageAnalyzerAgent) 测试 ============


class TestImageAnalyzerAgent:
    """ImageAnalyzerAgent 单元测试"""

    @pytest.fixture
    def agent(self):
        """创建 Agent 实例"""
        return create_image_analyzer_agent()

    @pytest.mark.asyncio
    async def test_parse_normal_placeholders(self, agent):
        """测试正常解析占位符"""
        input_data = ImageAnalyzerInput(content=EXAMPLE_CONTENT_WITH_PLACEHOLDERS)

        output = await agent.execute(input_data)

        # 验证输出
        assert output.totalCount == 4
        assert len(output.tasks) == 4
        assert output.parseErrors is None

        # 验证第一个任务
        task1 = output.tasks[0]
        assert task1.placeholderId == "image_1"
        assert task1.position == 1
        assert "自媒体" in task1.keywords
        assert task1.imageType == ImageType.PHOTO
        assert ImageProvider.PEXELS in task1.preferredProviders

    @pytest.mark.asyncio
    async def test_parse_no_placeholders(self, agent):
        """测试无占位符情况"""
        input_data = ImageAnalyzerInput(content=EXAMPLE_CONTENT_NO_PLACEHOLDERS)

        output = await agent.execute(input_data)

        assert output.totalCount == 0
        assert len(output.tasks) == 0
        assert output.parseErrors is None

    @pytest.mark.asyncio
    async def test_parse_invalid_placeholders(self, agent):
        """测试格式错误的占位符"""
        input_data = ImageAnalyzerInput(content=EXAMPLE_CONTENT_INVALID_PLACEHOLDER)

        output = await agent.execute(input_data)

        # 应该解析出 2 个有效任务
        assert output.totalCount == 2
        assert output.parseErrors is not None
        assert len(output.parseErrors) > 0

    @pytest.mark.asyncio
    async def test_task_order_preserved(self, agent):
        """测试占位符顺序保持"""
        input_data = ImageAnalyzerInput(content=EXAMPLE_CONTENT_WITH_PLACEHOLDERS)

        output = await agent.execute(input_data)

        # 验证顺序
        positions = [task.position for task in output.tasks]
        assert positions == sorted(positions)

    @pytest.mark.asyncio
    async def test_image_type_inference(self, agent):
        """测试图片类型推断"""
        # 测试 photo 类型
        content = "![IMAGE_PLACEHOLDER](image_1|科技、创新、未来)"
        input_data = ImageAnalyzerInput(content=content)
        output = await agent.execute(input_data)
        assert output.tasks[0].imageType == ImageType.PHOTO

    @pytest.mark.asyncio
    async def test_provider_selection_for_photo(self, agent):
        """测试 photo 类型的服务选择"""
        content = "![IMAGE_PLACEHOLDER](image_1|科技、创新)"
        input_data = ImageAnalyzerInput(content=content)
        output = await agent.execute(input_data)

        task = output.tasks[0]
        # photo 类型应该优先使用 pexels 和 seedream
        assert ImageProvider.PEXELS in task.preferredProviders
        assert ImageProvider.SEEDREAM in task.preferredProviders
        # picsum 应该在 fallback 中
        assert ImageProvider.PICSUM in task.fallbackProviders
        # iconify 不应该在列表中（禁止用于正文主图）
        assert ImageProvider.ICONIFY not in task.preferredProviders

    @pytest.mark.asyncio
    async def test_provider_selection_for_icon(self, agent):
        """测试 icon 类型的服务选择"""
        # 构造包含图标关键词的内容
        content = "![IMAGE_PLACEHOLDER](image_1|图标、logo、标志)"
        input_data = ImageAnalyzerInput(content=content)
        output = await agent.execute(input_data)

        task = output.tasks[0]
        # icon 类型应该使用 iconify
        assert ImageProvider.ICONIFY in task.preferredProviders


# ============ 服务策略层测试 ============


class TestImageServiceStrategy:
    """ImageServiceStrategy 单元测试"""

    @pytest.fixture
    def strategy(self):
        """创建策略实例（使用 Mock 服务）"""
        return create_image_service_strategy(
            pexels_provider=MockPexelsService(),
            iconify_provider=MockIconifyService(),
            seedream_provider=MockSeedreamService(),
            picsum_provider=MockPicsumService(),
        )

    def test_all_providers_registered(self, strategy):
        """测试所有服务已注册"""
        available = strategy.get_available_providers()
        assert ImageProvider.PEXELS in available
        assert ImageProvider.ICONIFY in available
        assert ImageProvider.SEEDREAM in available
        assert ImageProvider.PICSUM in available

    def test_iconify_blocked_for_photo(self, strategy):
        """测试 Iconify 禁止用于正文主图"""
        task = ImageTask(
            taskId="test-1",
            placeholderId="image_1",
            position=1,
            keywords=["科技"],
            imageType=ImageType.PHOTO,
            preferredProviders=[ImageProvider.PEXELS, ImageProvider.ICONIFY],
            fallbackProviders=[ImageProvider.PICSUM],
        )

        # 选择服务时应该排除 Iconify
        provider = strategy.select_provider(task)
        assert provider.get_provider_name() == ImageProvider.PEXELS

    @pytest.mark.asyncio
    async def test_fetch_with_retry_success(self, strategy):
        """测试带重试的图片获取（成功）"""
        task = ImageTask(
            taskId="test-1",
            placeholderId="image_1",
            position=1,
            keywords=["科技"],
            imageType=ImageType.PHOTO,
            preferredProviders=[ImageProvider.PEXELS],
            fallbackProviders=[ImageProvider.PICSUM],
        )

        result = await strategy.fetch_with_retry(task)

        assert result.success
        assert result.provider == ImageProvider.PEXELS

    @pytest.mark.asyncio
    async def test_fallback_to_picsum(self, strategy):
        """测试降级到 Picsum"""
        # 创建一个会失败的任务
        task = ImageTask(
            taskId="test-1",
            placeholderId="image_1",
            position=1,
            keywords=["科技"],
            imageType=ImageType.PHOTO,
            preferredProviders=[],  # 空的首选列表
            fallbackProviders=[ImageProvider.PICSUM],
        )

        result = await strategy.fetch_with_retry(task)

        # 应该降级到 Picsum
        assert result.success
        assert result.provider == ImageProvider.PICSUM


# ============ Agent5 (ImageGeneratorAgent) 测试 ============


class TestImageGeneratorAgent:
    """ImageGeneratorAgent 单元测试"""

    @pytest.fixture
    def agent(self):
        """创建 Agent 实例（使用 Mock 服务）"""
        strategy = create_image_service_strategy(
            pexels_provider=MockPexelsService(),
            iconify_provider=MockIconifyService(),
            seedream_provider=MockSeedreamService(),
            picsum_provider=MockPicsumService(),
        )
        return create_image_generator_agent(
            strategy=strategy,
            cos_uploader=MockCOSUploader(),
            use_mock=True,
        )

    @pytest.fixture
    def sample_tasks(self):
        """创建示例任务列表"""
        return [
            ImageTask(
                taskId="task-1",
                placeholderId="image_1",
                position=1,
                keywords=["科技", "创新"],
                imageType=ImageType.PHOTO,
                preferredProviders=[ImageProvider.PEXELS],
                fallbackProviders=[ImageProvider.PICSUM],
            ),
            ImageTask(
                taskId="task-2",
                placeholderId="image_2",
                position=2,
                keywords=["设计", "艺术"],
                imageType=ImageType.PHOTO,
                preferredProviders=[ImageProvider.PEXELS],
                fallbackProviders=[ImageProvider.PICSUM],
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_single_task(self, agent, sample_tasks):
        """测试执行单个任务"""
        content = "正文内容 ![IMAGE_PLACEHOLDER](image_1|科技、创新) 更多内容"
        input_data = ImageGeneratorInput(
            tasks=sample_tasks[:1],
            content=content,
            taskId="test-article-id",
        )

        output = await agent.execute(input_data)

        assert output.totalCount == 1
        assert output.successCount == 1
        assert output.failedCount == 0

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self, agent, sample_tasks):
        """测试并行执行多个任务"""
        content = """
        正文内容
        ![IMAGE_PLACEHOLDER](image_1|科技、创新)
        更多内容
        ![IMAGE_PLACEHOLDER](image_2|设计、艺术)
        """
        input_data = ImageGeneratorInput(
            tasks=sample_tasks,
            content=content,
            taskId="test-article-id",
        )

        output = await agent.execute(input_data)

        assert output.totalCount == 2
        assert output.successCount == 2

    @pytest.mark.asyncio
    async def test_merge_images_into_content(self, agent, sample_tasks):
        """测试图文合并"""
        content = """
# 标题

![IMAGE_PLACEHOLDER](image_1|科技、创新)

正文段落

![IMAGE_PLACEHOLDER](image_2|设计、艺术)

结尾
"""
        input_data = ImageGeneratorInput(
            tasks=sample_tasks,
            content=content,
            taskId="test-article-id",
        )

        output = await agent.execute(input_data)

        # 验证合并后的内容不包含占位符
        assert "IMAGE_PLACEHOLDER" not in output.mergedContent
        # 应该包含图片链接
        assert "![" in output.mergedContent

    @pytest.mark.asyncio
    async def test_failed_image_removed(self, agent):
        """测试失败图片从正文中删除"""
        # 创建一个会失败的任务
        task = ImageTask(
            taskId="task-fail",
            placeholderId="image_fail",
            position=1,
            keywords=["测试"],
            imageType=ImageType.PHOTO,
            preferredProviders=[],  # 空列表，会失败
            fallbackProviders=[],
        )

        content = "正文 ![IMAGE_PLACEHOLDER](image_fail|测试) 结尾"
        input_data = ImageGeneratorInput(
            tasks=[task],
            content=content,
            taskId="test-article-id",
        )

        output = await agent.execute(input_data)

        # 失败的图片应该被删除
        assert "IMAGE_PLACEHOLDER" not in output.mergedContent


# ============ COS 上传测试 ============


class TestCOSUploader:
    """COSUploader 单元测试"""

    @pytest.fixture
    def uploader(self):
        """创建 Mock 上传器"""
        return MockCOSUploader()

    @pytest.mark.asyncio
    async def test_upload_from_url(self, uploader):
        """测试从 URL 上传"""
        result = await uploader.upload_from_url(
            image_url="https://example.com/image.jpg",
            placeholder_id="image_1",
            task_id="task-1",
            source_provider=ImageProvider.PEXELS,
        )

        assert result.status == ImageTaskStatus.COMPLETED
        assert result.url != ""
        assert result.placeholderId == "image_1"


# ============ 集成测试 ============


class TestImagePipelineIntegration:
    """图片处理流水线集成测试"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """测试完整流水线：Agent4 -> Agent5"""
        # 1. 使用 Agent4 分析正文
        analyzer = create_image_analyzer_agent()
        analyzer_output = await analyzer.execute(
            ImageAnalyzerInput(content=EXAMPLE_CONTENT_WITH_PLACEHOLDERS)
        )

        assert analyzer_output.totalCount == 4

        # 2. 使用 Agent5 生成图片并合并
        strategy = create_image_service_strategy(
            pexels_provider=MockPexelsService(),
            iconify_provider=MockIconifyService(),
            seedream_provider=MockSeedreamService(),
            picsum_provider=MockPicsumService(),
        )
        generator = create_image_generator_agent(
            strategy=strategy,
            cos_uploader=MockCOSUploader(),
            use_mock=True,
        )

        generator_output = await generator.execute(
            ImageGeneratorInput(
                tasks=analyzer_output.tasks,
                content=EXAMPLE_CONTENT_WITH_PLACEHOLDERS,
                taskId="integration-test",
            )
        )

        # 3. 验证结果
        assert generator_output.totalCount == 4
        assert generator_output.successCount == 4
        assert "IMAGE_PLACEHOLDER" not in generator_output.mergedContent

    @pytest.mark.asyncio
    async def test_degradation_flow(self):
        """测试服务降级流程"""
        # 创建只使用 Picsum 的策略
        strategy = create_image_service_strategy(
            picsum_provider=MockPicsumService(),
        )

        task = ImageTask(
            taskId="degrade-test",
            placeholderId="image_1",
            position=1,
            keywords=["测试"],
            imageType=ImageType.PHOTO,
            preferredProviders=[ImageProvider.PEXELS],  # Pexels 未注册
            fallbackProviders=[ImageProvider.PICSUM],  # 降级到 Picsum
        )

        result = await strategy.fetch_with_retry(task)

        # 应该降级到 Picsum
        assert result.success
        assert result.provider == ImageProvider.PICSUM


# ============ 运行测试 ============


if __name__ == "__main__":
    pytest.main([__file__, "-v"])