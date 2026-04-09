"""
智能体基类
定义智能体的通用接口和基础功能
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any, AsyncGenerator
from pathlib import Path
from pydantic import BaseModel

from app.services.llm_service import LLMServiceBase, get_llm_service


logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """智能体输入基类"""

    pass


class AgentOutput(BaseModel):
    """智能体输出基类"""

    pass


class BaseAgent(ABC):
    """
    智能体基类

    所有智能体都继承此基类，实现统一的接口。
    提供以下通用功能：
    - LLM 调用封装
    - Prompt 模板加载
    - 流式输出支持
    - 错误处理
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceBase] = None,
        use_mock: bool = False,
        llm_provider: Optional[str] = None,
    ):
        """
        初始化智能体

        Args:
            llm_service: LLM 服务实例（可选）
            use_mock: 是否使用 mock LLM 服务
            llm_provider: LLM 提供者 (zhipu/qianwen/deepseek)
        """
        self.llm_service = llm_service or get_llm_service(use_mock, llm_provider)
        self.prompt_dir = Path(__file__).parent.parent.parent / "prompts"
        self._last_call_log: Optional[dict] = None

    @abstractmethod
    async def execute(
        self,
        input_data: AgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> AgentOutput:
        """
        执行智能体任务

        Args:
            input_data: 输入数据
            stream_callback: 流式回调函数，用于推送中间结果

        Returns:
            AgentOutput: 智能体输出结果
        """
        pass

    def load_prompt_template(self, template_name: str) -> str:
        """
        加载 Prompt 模板

        Args:
            template_name: 模板文件名（不含扩展名）

        Returns:
            模板内容
        """
        template_path = self.prompt_dir / f"{template_name}.md"

        if not template_path.exists():
            raise FileNotFoundError(f"Prompt 模板不存在: {template_path}")

        return template_path.read_text(encoding="utf-8")

    def fill_prompt_template(
        self,
        template: str,
        variables: dict[str, Any],
    ) -> str:
        """
        填充 Prompt 模板变量

        Args:
            template: 模板内容
            variables: 变量字典

        Returns:
            填充后的 Prompt
        """
        prompt = template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            prompt = prompt.replace(placeholder, str(value) if value else "")
        return prompt

    async def call_llm(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> str:
        """
        调用 LLM

        Args:
            prompt: 输入提示词
            stream_callback: 流式回调函数
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            LLM 响应文本
        """
        logger.info(f"[{self.__class__.__name__}] 开始调用 LLM")

        try:
            response = await self.llm_service.call(
                prompt=prompt,
                stream_callback=stream_callback,
                **kwargs,
            )

            # 记录最后一次调用日志
            if hasattr(self.llm_service, "call_logs") and self.llm_service.call_logs:
                self._last_call_log = self.llm_service.call_logs[-1].to_dict()

            logger.info(f"[{self.__class__.__name__}] LLM 调用完成")
            return response

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] LLM 调用失败: {e}")
            raise

    async def call_llm_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM

        Args:
            prompt: 输入提示词
            stream_callback: 流式回调函数
            **kwargs: 其他参数

        Yields:
            LLM 响应文本片段
        """
        logger.info(f"[{self.__class__.__name__}] 开始流式调用 LLM")

        try:
            async for chunk in self.llm_service.call_stream(
                prompt=prompt,
                stream_callback=stream_callback,
                **kwargs,
            ):
                yield chunk

            logger.info(f"[{self.__class__.__name__}] 流式调用完成")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] 流式调用失败: {e}")
            raise

    def get_last_call_log(self) -> Optional[dict]:
        """
        获取最后一次 LLM 调用日志

        Returns:
            调用日志字典
        """
        return self._last_call_log

    @property
    @abstractmethod
    def name(self) -> str:
        """智能体名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """智能体描述"""
        pass