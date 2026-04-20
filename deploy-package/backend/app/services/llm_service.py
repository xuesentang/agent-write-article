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
    用于测试和开发，根据 prompt 内容智能返回不同的 mock 响应
    """

    def __init__(self, mock_response: Optional[str] = None):
        self.mock_response = mock_response
        self.call_logs: list[LLMCallLog] = []

    def _get_mock_response(self, prompt: str) -> str:
        """
        根据 prompt 内容智能返回 mock 响应

        Args:
            prompt: 输入提示词

        Returns:
            对应的 mock 响应
        """
        # 如果设置了自定义响应，直接返回
        if self.mock_response:
            return self.mock_response

        # 根据 prompt 关键词判断返回类型
        if "正文" in prompt or "content" in prompt.lower() or "撰写" in prompt or "IMAGE_PLACEHOLDER" in prompt:
            return self._mock_content_response()
        elif "大纲" in prompt or "outline" in prompt.lower() or "sections" in prompt:
            return self._mock_outline_response()
        elif "标题" in prompt or "title" in prompt.lower():
            return self._mock_title_response()
        else:
            return self._mock_title_response()

    def _mock_content_response(self) -> str:
        """正文生成 mock 响应"""
        return """
# 自媒体爆款文章的3个核心秘诀

在当今数字化时代，自媒体已经成为信息传播和个人品牌塑造的重要渠道。无论是微信公众号、抖音、小红书还是其他平台，能够创作出爆款文章，意味着更大的曝光量、更多的粉丝增长以及更强的商业价值。

![IMAGE_PLACEHOLDER](image_1|自媒体、内容创作、数字化时代)

## 一、选题：爆款的第一步

选题是文章能否成为爆款的基础。一个好的选题，能够在众多内容中脱颖而出，吸引用户的注意力。

### 1.1 热点敏感度

保持对热点事件的敏感度是选题的关键。每天关注各大平台的热搜榜单、行业动态，第一时间捕捉热点，并结合自己的领域进行创作。

![IMAGE_PLACEHOLDER](image_2|热点追踪、热搜榜、趋势分析)

### 1.2 用户痛点挖掘

除了追逐热点，更要深入挖掘用户痛点。通过分析用户评论、搜索趋势，了解用户真正关心的问题，创作能够解决他们困惑的内容。

## 二、内容质量：爆款的根本

内容质量决定了用户是否会继续阅读、是否会分享转发。优质的内容需要具备以下特点：

### 2.1 信息增量

不要重复已经被大量传播的信息，而是要提供新的视角、新的数据、新的案例。让用户在阅读后获得真正的信息增量。

![IMAGE_PLACEHOLDER](image_3|内容创作、信息价值、知识增量)

### 2.2 结构清晰

文章结构要清晰，逻辑要流畅。使用恰当的标题层级、段落划分，让用户能够快速理解文章脉络。

### 2.3 语言风格匹配

根据文章主题和目标读者，选择合适的语言风格。专业类文章用严谨的表达，轻松类文章用活泼的语气。

## 三、传播技巧：爆款的助推器

即使内容质量很好，如果没有正确的传播策略，也很难成为爆款。

### 3.1 标题优化

标题是文章的"门面"。一个好的标题应该：
- 包含数字或对比，增加视觉冲击力
- 提出问题，引发用户好奇
- 直接点明价值，让用户知道能获得什么

![IMAGE_PLACEHOLDER](image_4|标题技巧、传播策略、用户吸引)

### 3.2 发布时间选择

选择合适的发布时间可以最大化文章的曝光。根据平台数据分析用户活跃时段，在高峰期发布内容。

### 3.3 互动引导

在文章结尾设置互动问题，鼓励用户评论、分享。活跃的评论区能够增加文章的权重，获得更多推荐。

## 总结

打造爆款文章不是偶然，而是选题、内容质量和传播技巧三个核心要素的综合运用。持续学习、不断实践，才能在自媒体领域脱颖而出。

![IMAGE_PLACEHOLDER](image_5|成功总结、自媒体成长、持续学习)

希望这篇文章能帮助你更好地理解爆款文章的创作逻辑，祝你在自媒体创作路上越走越远！
"""

    def _mock_title_response(self) -> str:
        """标题生成 mock 响应"""
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

    def _mock_outline_response(self) -> str:
        """大纲生成 mock 响应"""
        return """
```json
{
  "sections": [
    {
      "id": "section_1",
      "title": "一、引言",
      "level": 1,
      "key_points": ["自媒体时代的机遇", "为什么选题如此重要", "本文解决的问题"],
      "estimated_length": 300
    },
    {
      "id": "section_2",
      "title": "二、爆款选题的核心要素",
      "level": 1,
      "key_points": ["热点敏感度", "用户痛点", "情感共鸣"],
      "estimated_length": 500,
      "subsections": [
        {
          "id": "section_2_1",
          "title": "2.1 如何捕捉热点",
          "level": 2,
          "key_points": ["关注热点平台", "快速响应策略"],
          "estimated_length": 200
        },
        {
          "id": "section_2_2",
          "title": "2.2 用户痛点挖掘方法",
          "level": 2,
          "key_points": ["评论区分析", "搜索趋势研究"],
          "estimated_length": 200
        }
      ]
    },
    {
      "id": "section_3",
      "title": "三、实战案例分析",
      "level": 1,
      "key_points": ["成功案例复盘", "失败案例反思", "经验总结"],
      "estimated_length": 600
    },
    {
      "id": "section_4",
      "title": "四、选题工具与方法",
      "level": 1,
      "key_points": ["选题工具推荐", "选题流程梳理", "选题评估标准"],
      "estimated_length": 400
    },
    {
      "id": "section_5",
      "title": "五、总结与展望",
      "level": 1,
      "key_points": ["核心要点回顾", "未来选题趋势", "读者行动建议"],
      "estimated_length": 300
    }
  ]
}
```
"""

    async def call(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> str:
        """Mock 调用，根据 prompt 智能返回响应"""
        start_time = datetime.now()

        # 获取智能响应
        response = self._get_mock_response(prompt)

        # 模拟延迟
        await asyncio.sleep(0.1)

        # 模拟流式输出（分块发送）
        if stream_callback:
            chunks = self._split_response(response)
            for chunk in chunks:
                stream_callback(chunk)
                await asyncio.sleep(0.05)  # 模拟流式延迟

        latency = (datetime.now() - start_time).total_seconds() * 1000

        # 记录日志
        log = LLMCallLog(
            provider="mock",
            model="mock-model",
            prompt=prompt,
            response=response,
            success=True,
            latency_ms=latency,
        )
        self.call_logs.append(log)
        logger.info(f"[MockLLM] 调用成功, latency={latency:.2f}ms")

        return response

    async def call_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Mock 流式调用"""
        response = self._get_mock_response(prompt)
        chunks = self._split_response(response)
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
                            await stream_callback(content)

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