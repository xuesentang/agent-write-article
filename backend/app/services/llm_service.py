"""
LLM 调用服务
统一的 LLM 调用封装，支持多种 LLM 提供者
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator, Callable
from datetime import datetime
from abc import ABC, abstractmethod

from openai import AsyncOpenAI
from app.config import settings


logger = logging.getLogger(__name__)


class LLMCallLog:
    """LLM 调用日志记录"""

    def __init__(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        latency_ms: Optional[float] = None,
        retry_count: int = 0,
    ):
        self.provider = provider
        self.model = model
        self.prompt = prompt
        self.response = response
        self.success = success
        self.error = error
        self.latency_ms = latency_ms
        self.retry_count = retry_count
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt[:500] + "..." if len(self.prompt) > 500 else self.prompt,
            "response": self.response[:500] + "..." if self.response and len(self.response) > 500 else self.response,
            "success": self.success,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
        }


class LLMServiceBase(ABC):
    """LLM 服务基类"""

    @abstractmethod
    async def call(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> str:
        """调用 LLM"""
        pass

    @abstractmethod
    async def call_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM"""
        pass


class MockLLMService(LLMServiceBase):
    """
    Mock LLM 服务
    用于测试和开发，直接返回固定字符串
    """

    def __init__(self, mock_response: Optional[str] = None):
        self.mock_response = mock_response or self._default_mock_response()
        self.call_logs: list[LLMCallLog] = []

    def _default_mock_response(self) -> str:
        """默认 mock 响应"""
        return """
标题1: 深度解析：自媒体爆款文章的3个核心秘诀
推荐理由: 使用数字和"深度解析"突出专业性，吸引想要学习的读者
风格标签: 数据驱动, 专业权威

标题2: 为什么你的文章没人看？答案可能让你意外
推荐理由: 反问句引发好奇，"意外"制造悬念感
风格标签: 痛点解决, 好奇悬念

标题3: 每个自媒体人都要知道的写作真相
推荐理由: 使用"每个"制造共鸣感，"真相"引发探索欲
风格标签: 情感共鸣, 权威背书

标题4: 从0到10万粉：我的自媒体逆袭之路
推荐理由: 具体数据展示成果，"逆袭"传递励志情绪
风格标签: 数据驱动, 情感共鸣

标题5: 30天写出爆款文章，方法竟然这么简单
推荐理由: 时间承诺+意外转折，突出可操作性
风格标签: 教程风格, 好奇悬念
"""

    async def call(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> str:
        """Mock 调用，返回固定响应"""
        start_time = datetime.now()

        # 模拟延迟
        await asyncio.sleep(0.1)

        # 模拟流式输出（分块发送）
        if stream_callback:
            chunks = self._split_response(self.mock_response)
            for chunk in chunks:
                stream_callback(chunk)
                await asyncio.sleep(0.05)  # 模拟流式延迟

        latency = (datetime.now() - start_time).total_seconds() * 1000

        # 记录日志
        log = LLMCallLog(
            provider="mock",
            model="mock-model",
            prompt=prompt,
            response=self.mock_response,
            success=True,
            latency_ms=latency,
        )
        self.call_logs.append(log)
        logger.info(f"[MockLLM] 调用成功, latency={latency:.2f}ms")

        return self.mock_response

    async def call_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Mock 流式调用"""
        chunks = self._split_response(self.mock_response)
        for chunk in chunks:
            if stream_callback:
                stream_callback(chunk)
            yield chunk
            await asyncio.sleep(0.05)

    def _split_response(self, response: str, chunk_size: int = 20) -> list[str]:
        """将响应分成小块"""
        chunks = []
        for i in range(0, len(response), chunk_size):
            chunks.append(response[i:i + chunk_size])
        return chunks


class RealLLMService(LLMServiceBase):
    """
    真实 LLM 服务
    使用 OpenAI SDK 调用智谱/千问等兼容 API
    """

    def __init__(self, provider: str = None, max_retries: int = 2):
        """
        初始化 LLM 服务

        Args:
            provider: LLM 提供者 (zhipu/qianwen/deepseek)
            max_retries: 最大重试次数
        """
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.max_retries = max_retries
        self.call_logs: list[LLMCallLog] = []

        # 获取配置
        config = settings.get_llm_config(self.provider)
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]

        if not self.api_key:
            raise ValueError(f"LLM API Key 未配置: {self.provider}")

        # 初始化 OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def call(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """
        调用 LLM（支持重试）

        Args:
            prompt: 输入提示词
            stream_callback: 流式回调函数
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 响应文本
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            start_time = datetime.now()

            try:
                if stream_callback:
                    # 流式调用
                    response_text = ""
                    stream = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )

                    async for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            response_text += content
                            stream_callback(content)

                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    log = LLMCallLog(
                        provider=self.provider,
                        model=self.model,
                        prompt=prompt,
                        response=response_text,
                        success=True,
                        latency_ms=latency,
                        retry_count=retry_count,
                    )
                    self.call_logs.append(log)
                    logger.info(f"[{self.provider}] 流式调用成功, latency={latency:.2f}ms")
                    return response_text

                else:
                    # 非流式调用
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    response_text = response.choices[0].message.content
                    latency = (datetime.now() - start_time).total_seconds() * 1000

                    log = LLMCallLog(
                        provider=self.provider,
                        model=self.model,
                        prompt=prompt,
                        response=response_text,
                        success=True,
                        latency_ms=latency,
                        retry_count=retry_count,
                    )
                    self.call_logs.append(log)
                    logger.info(f"[{self.provider}] 调用成功, latency={latency:.2f}ms")
                    return response_text

            except Exception as e:
                last_error = str(e)
                retry_count += 1
                latency = (datetime.now() - start_time).total_seconds() * 1000

                logger.warning(
                    f"[{self.provider}] 调用失败 (retry {retry_count}/{self.max_retries}): {e}"
                )

                if retry_count <= self.max_retries:
                    # 等待后重试
                    await asyncio.sleep(1 * retry_count)

        # 所有重试都失败
        log = LLMCallLog(
            provider=self.provider,
            model=self.model,
            prompt=prompt,
            success=False,
            error=last_error,
            retry_count=retry_count,
        )
        self.call_logs.append(log)
        logger.error(f"[{self.provider}] 调用最终失败: {last_error}")
        raise RuntimeError(f"LLM 调用失败，重试 {self.max_retries} 次后仍然失败: {last_error}")

    async def call_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM

        Args:
            prompt: 输入提示词
            stream_callback: 流式回调函数
            temperature: 温度参数
            max_tokens: 最大 token 数

        Yields:
            响应文本片段
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        if stream_callback:
                            stream_callback(content)
                        yield content

                return  # 成功完成，退出

            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.warning(
                    f"[{self.provider}] 流式调用失败 (retry {retry_count}/{self.max_retries}): {e}"
                )

                if retry_count <= self.max_retries:
                    await asyncio.sleep(1 * retry_count)

        raise RuntimeError(f"LLM 流式调用失败: {last_error}")


def get_llm_service(use_mock: bool = False, provider: str = None) -> LLMServiceBase:
    """
    获取 LLM 服务实例

    Args:
        use_mock: 是否使用 mock 服务
        provider: LLM 提供者 (zhipu/qianwen/deepseek)

    Returns:
        LLM 服务实例
    """
    if use_mock:
        return MockLLMService()
    return RealLLMService(provider=provider)