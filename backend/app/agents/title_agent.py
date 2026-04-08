"""
智能体 1: TitleAgent (标题生成)
根据用户选题和文章风格生成爆款标题方案
"""

import logging
import re
from typing import Optional, Callable, List
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput


logger = logging.getLogger(__name__)


# ============ 输入输出数据结构 ============


class TitleAgentInput(AgentInput):
    """TitleAgent 输入数据"""

    topic: str = Field(..., min_length=1, max_length=500, description="用户输入的选题")
    style: str = Field(default="专业", max_length=50, description="文章风格")
    extra_description: Optional[str] = Field(
        default=None, max_length=1000, description="用户补充描述"
    )
    count: int = Field(default=5, ge=3, le=5, description="生成标题数量")


class TitleOption(BaseModel):
    """单个标题方案"""

    title: str = Field(..., description="标题内容")
    reasoning: str = Field(default="", description="推荐理由")
    style_tags: List[str] = Field(default_factory=list, description="风格标签")


class TitleAgentOutput(AgentOutput):
    """TitleAgent 输出数据"""

    titles: List[TitleOption] = Field(default_factory=list, description="生成的标题列表")
    raw_response: Optional[str] = Field(default=None, description="原始 LLM 响应")


# ============ TitleAgent 实现 ============


class TitleAgent(BaseAgent):
    """
    标题生成智能体

    功能：
    - 根据选题和风格生成 3-5 个爆款标题
    - 通过 SSE 流式推送标题方案
    - 返回结构化的标题数据

    输入：
    - topic: 用户选题
    - style: 文章风格
    - extra_description: 补充描述（可选）
    - count: 标题数量

    输出：
    - titles: 标题列表
    """

    def __init__(
        self,
        llm_service=None,
        use_mock: bool = False,
        llm_provider: Optional[str] = None,
    ):
        super().__init__(llm_service, use_mock, llm_provider)
        self._template_name = "title_generation"

    @property
    def name(self) -> str:
        return "TitleAgent"

    @property
    def description(self) -> str:
        return "根据选题和风格生成爆款标题方案"

    async def execute(
        self,
        input_data: TitleAgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> TitleAgentOutput:
        """
        执行标题生成任务

        Args:
            input_data: 标题生成输入数据
            stream_callback: SSE 流式回调函数

        Returns:
            TitleAgentOutput: 生成的标题方案
        """
        logger.info(
            f"[TitleAgent] 开始生成标题: topic={input_data.topic[:30]}..., style={input_data.style}"
        )

        # 1. 加载 Prompt 模板
        try:
            template = self.load_prompt_template(self._template_name)
        except FileNotFoundError:
            logger.warning("[TitleAgent] Prompt 模板不存在，使用默认模板")
            template = self._default_prompt_template()

        # 2. 填充模板变量
        prompt = self.fill_prompt_template(
            template,
            {
                "topic": input_data.topic,
                "style": input_data.style,
                "extra_description": input_data.extra_description or "无",
                "count": input_data.count,
            },
        )

        # 3. 调用 LLM（带流式回调）
        response = await self.call_llm(
            prompt=prompt,
            stream_callback=stream_callback,
            temperature=0.8,  # 标题生成需要更多创意
            max_tokens=1500,
        )

        # 4. 解析响应
        titles = self._parse_response(response)

        logger.info(f"[TitleAgent] 标题生成完成，共 {len(titles)} 个标题")

        return TitleAgentOutput(
            titles=titles,
            raw_response=response,
        )

    def _default_prompt_template(self) -> str:
        """默认 Prompt 模板（当文件不存在时使用）"""
        return """
你是一位自媒体爆款标题专家，请根据以下信息生成 {{count}} 个高质量的爆款标题：

选题：{{topic}}
文章风格：{{style}}
补充描述：{{extra_description}}

请按以下格式输出每个标题：
标题N: [标题内容]
推荐理由: [简短理由]
风格标签: [标签1, 标签2]

要求：
1. 标题长度 15-30 字
2. 与内容高度相关，不标题党
3. 根据文章风格调整标题风格
4. 使用爆款标题技巧（数字、对比、痛点、好奇等）

请开始生成标题。
"""

    def _parse_response(self, response: str) -> List[TitleOption]:
        """
        解析 LLM 响应，提取标题方案

        Args:
            response: LLM 响应文本

        Returns:
            标题方案列表
        """
        titles = []

        # 使用正则解析标题块
        # 格式: 标题N: xxx  推荐理由: xxx  风格标签: xxx
        pattern = r"标题\d+[:：]\s*(.+?)\s*推荐理由[:：]\s*(.+?)\s*风格标签[:：]\s*(.+?)(?=标题\d+|$)"

        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            title = match[0].strip()
            reasoning = match[1].strip()
            style_tags_str = match[2].strip()

            # 解析风格标签
            style_tags = [
                tag.strip()
                for tag in re.split(r"[,，、\s]+", style_tags_str)
                if tag.strip()
            ]

            titles.append(
                TitleOption(
                    title=title,
                    reasoning=reasoning,
                    style_tags=style_tags,
                )
            )

        # 如果正则解析失败，尝试简单提取
        if not titles:
            logger.warning("[TitleAgent] 正则解析失败，尝试简单提取")
            titles = self._simple_parse(response)

        return titles

    def _simple_parse(self, response: str) -> List[TitleOption]:
        """
        简单解析响应（备用方案）

        提取以"标题"开头的行作为标题
        """
        titles = []
        lines = response.split("\n")

        current_title = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测标题行
            if re.match(r"^标题\d+[:：]", line):
                # 提取标题内容
                title_match = re.search(r"标题\d+[:：]\s*(.+)", line)
                if title_match:
                    current_title = title_match.group(1).strip()
                    titles.append(
                        TitleOption(
                            title=current_title,
                            reasoning="",
                            style_tags=[],
                        )
                    )

        return titles


# ============ 工厂函数 ============


def create_title_agent(
    use_mock: bool = False,
    llm_provider: Optional[str] = None,
) -> TitleAgent:
    """
    创建 TitleAgent 实例

    Args:
        use_mock: 是否使用 mock LLM
        llm_provider: LLM 提供者

    Returns:
        TitleAgent 实例
    """
    return TitleAgent(use_mock=use_mock, llm_provider=llm_provider)