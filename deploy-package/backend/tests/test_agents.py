"""
智能体模块测试
测试 TitleAgent 和 LLM 服务集成
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os

# 设置测试环境变量
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_article.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "zhipu")


# ============ LLM Service Tests ============


class TestMockLLMService:
    """测试 MockLLMService"""

    @pytest.mark.asyncio
    async def test_mock_llm_call(self):
        """测试 mock LLM 调用"""
        from app.services.llm_service import MockLLMService

        service = MockLLMService()

        # 测试基本调用
        response = await service.call(prompt="测试提示词")

        assert response is not None
        assert len(response) > 0
        assert "标题" in response  # 默认 mock 响应包含标题

    @pytest.mark.asyncio
    async def test_mock_llm_stream(self):
        """测试 mock LLM 流式调用"""
        from app.services.llm_service import MockLLMService

        service = MockLLMService()

        # 测试流式调用
        chunks = []
        async for chunk in service.call_stream(prompt="测试提示词"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "标题" in full_response

    @pytest.mark.asyncio
    async def test_mock_llm_with_callback(self):
        """测试 mock LLM 带回调"""
        from app.services.llm_service import MockLLMService

        service = MockLLMService()

        # 测试带回调的调用
        callback_chunks = []
        response = await service.call(
            prompt="测试提示词",
            stream_callback=lambda chunk: callback_chunks.append(chunk),
        )

        assert len(callback_chunks) > 0
        assert response == "".join(callback_chunks)

    @pytest.mark.asyncio
    async def test_mock_llm_custom_response(self):
        """测试自定义 mock 响应"""
        from app.services.llm_service import MockLLMService

        custom_response = """
标题1: 自定义标题一
推荐理由: 测试理由
风格标签: 测试标签
"""
        service = MockLLMService(mock_response=custom_response)

        response = await service.call(prompt="测试")

        assert "自定义标题一" in response

    @pytest.mark.asyncio
    async def test_mock_llm_call_log(self):
        """测试 mock LLM 调用日志"""
        from app.services.llm_service import MockLLMService

        service = MockLLMService()

        await service.call(prompt="测试")

        assert len(service.call_logs) == 1
        log = service.call_logs[0]
        assert log.provider == "mock"
        assert log.success is True


class TestRealLLMService:
    """测试 RealLLMService"""

    @pytest.mark.asyncio
    async def test_real_llm_requires_api_key(self):
        """测试真实 LLM 需要 API Key"""
        from app.services.llm_service import RealLLMService

        # 无 API Key 时应抛出异常
        with patch("app.config.settings") as mock_settings:
            mock_settings.DEFAULT_LLM_PROVIDER = "zhipu"
            mock_settings.get_llm_config = MagicMock(
                return_value={
                    "api_key": None,
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "model": "glm-4",
                }
            )

            with pytest.raises(ValueError, match="API Key 未配置"):
                RealLLMService(provider="zhipu")


# ============ TitleAgent Tests ============


class TestTitleAgent:
    """测试 TitleAgent"""

    @pytest.mark.asyncio
    async def test_title_agent_with_mock(self):
        """测试 TitleAgent 使用 mock LLM"""
        from app.agents import TitleAgent, TitleAgentInput

        agent = TitleAgent(use_mock=True)

        input_data = TitleAgentInput(
            topic="自媒体爆款文章写作技巧",
            style="专业",
            count=5,
        )

        output = await agent.execute(input_data)

        assert output.titles is not None
        assert len(output.titles) >= 3
        assert all(t.title for t in output.titles)

    @pytest.mark.asyncio
    async def test_title_agent_stream_callback(self):
        """测试 TitleAgent 流式回调"""
        from app.agents import TitleAgent, TitleAgentInput

        agent = TitleAgent(use_mock=True)

        # 收集流式回调内容
        stream_chunks = []

        async def callback(chunk):
            stream_chunks.append(chunk)

        input_data = TitleAgentInput(
            topic="测试选题",
            style="轻松",
            count=3,
        )

        output = await agent.execute(input_data, stream_callback=callback)

        assert len(stream_chunks) > 0
        assert output.raw_response == "".join(stream_chunks)

    @pytest.mark.asyncio
    async def test_title_agent_parse_response(self):
        """测试 TitleAgent 响应解析"""
        from app.agents import TitleAgent

        agent = TitleAgent(use_mock=True)

        # 测试标准格式解析
        response = """
标题1: 测试标题一
推荐理由: 这是一理由
风格标签: 吸引眼球, 数据驱动

标题2: 测试标题二
推荐理由: 另一个理由
风格标签: 情感共鸣
"""
        titles = agent._parse_response(response)

        assert len(titles) == 2
        assert titles[0].title == "测试标题一"
        assert titles[0].reasoning == "这是一理由"
        assert len(titles[0].style_tags) == 2

    @pytest.mark.asyncio
    async def test_title_agent_simple_parse(self):
        """测试 TitleAgent 简单解析"""
        from app.agents import TitleAgent

        agent = TitleAgent(use_mock=True)

        # 测试简单格式解析（备用方案）
        response = """
标题1: 简单标题一
标题2: 简单标题二
标题3: 简单标题三
"""
        titles = agent._simple_parse(response)

        assert len(titles) == 3
        assert titles[0].title == "简单标题一"

    @pytest.mark.asyncio
    async def test_title_agent_properties(self):
        """测试 TitleAgent 属性"""
        from app.agents import TitleAgent

        agent = TitleAgent(use_mock=True)

        assert agent.name == "TitleAgent"
        assert "标题" in agent.description


class TestTitleAgentInputOutput:
    """测试 TitleAgent 输入输出结构"""

    def test_title_agent_input_validation(self):
        """测试输入验证"""
        from app.agents import TitleAgentInput
        from pydantic import ValidationError

        # 正常输入
        input_data = TitleAgentInput(
            topic="测试选题",
            style="专业",
            count=5,
        )
        assert input_data.topic == "测试选题"
        assert input_data.count == 5

        # 边界测试
        input_data2 = TitleAgentInput(topic="短选题", count=3)
        assert input_data2.count == 3

        # 超出范围测试
        with pytest.raises(ValidationError):
            TitleAgentInput(topic="测试", count=10)  # count 最大 5

    def test_title_option(self):
        """测试 TitleOption 结构"""
        from app.agents import TitleOption

        option = TitleOption(
            title="测试标题",
            reasoning="测试理由",
            style_tags=["标签1", "标签2"],
        )

        assert option.title == "测试标题"
        assert len(option.style_tags) == 2


# ============ BaseAgent Tests ============


class TestBaseAgent:
    """测试 BaseAgent"""

    def test_base_agent_load_template(self):
        """测试 Prompt 模板加载"""
        from app.agents import TitleAgent

        agent = TitleAgent(use_mock=True)

        # 加载模板
        template = agent.load_prompt_template("title_generation")

        assert "{{topic}}" in template
        assert "{{style}}" in template

    def test_base_agent_fill_template(self):
        """测试模板变量填充"""
        from app.agents import TitleAgent

        agent = TitleAgent(use_mock=True)

        template = "选题: {{topic}}, 风格: {{style}}"
        filled = agent.fill_prompt_template(
            template,
            {"topic": "测试选题", "style": "专业"},
        )

        assert filled == "选题: 测试选题, 风格: 专业"


# ============ Integration Tests ============


class TestAgentIntegration:
    """智能体集成测试"""

    @pytest.mark.asyncio
    async def test_full_title_generation_flow(self):
        """测试完整的标题生成流程"""
        from app.agents import create_title_agent, TitleAgentInput

        # 使用 mock 进行完整流程测试
        agent = create_title_agent(use_mock=True)

        input_data = TitleAgentInput(
            topic="如何打造自媒体爆款文章",
            style="专业",
            extra_description="面向自媒体新手",
            count=5,
        )

        output = await agent.execute(input_data)

        # 验证输出
        assert len(output.titles) >= 3

        # 验证每个标题
        for title in output.titles:
            assert title.title
            assert len(title.title) >= 10  # 标题长度合理

        # 验证日志
        log = agent.get_last_call_log()
        assert log is not None
        assert log["success"] is True


# ============ Real LLM Tests (Optional) ============


class TestRealLLMIntegration:
    """
    真实 LLM 集成测试

    注意：这些测试需要配置真实的 API Key
    默认跳过，可通过 --run-real-llm 参数启用
    """

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要真实 API Key")
    async def test_real_zhipu_call(self):
        """测试真实智谱 GLM 调用"""
        from app.services.llm_service import RealLLMService

        # 需要在 .env 中配置 ZHIPU_API_KEY
        service = RealLLMService(provider="zhipu")

        response = await service.call(prompt="请生成一个自媒体文章标题")

        assert response is not None
        assert len(response) > 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要真实 API Key")
    async def test_real_qianwen_call(self):
        """测试真实千问调用"""
        from app.services.llm_service import RealLLMService

        # 需要在 .env 中配置 QIANWEN_API_KEY
        service = RealLLMService(provider="qianwen")

        response = await service.call(prompt="请生成一个自媒体文章标题")

        assert response is not None
        assert len(response) > 0


# ============ SSE Integration Tests ============


class TestSSEIntegration:
    """SSE 与智能体集成测试"""

    @pytest.mark.asyncio
    async def test_sse_manager_title_events(self):
        """测试 SSE 标题事件发送"""
        from app.utils.sse_manager import sse_manager

        task_id = "test-task-123"

        # 模拟连接
        async with sse_manager.create_connection(task_id) as conn:
            # 发送标题片段
            success = await sse_manager.send_title_chunk(
                task_id=task_id,
                content="测试标题片段",
                index=0,
                progress=10,
            )
            assert success

            # 发送标题完成
            success = await sse_manager.send_title_complete(
                task_id=task_id,
                titles=["标题1", "标题2"],
                progress=20,
            )
            assert success


# ============ 运行测试 ============


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])