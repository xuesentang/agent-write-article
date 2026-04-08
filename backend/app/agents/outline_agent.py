"""
智能体 2: OutlineAgent (大纲生成)
根据选定标题生成结构化文章大纲，支持优化模式
"""

import json
import logging
import re
from typing import Optional, Callable, List
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput


logger = logging.getLogger(__name__)


# ============ 输入输出数据结构 ============


class OutlineAgentInput(AgentInput):
    """OutlineAgent 输入数据"""

    selected_title: str = Field(..., min_length=1, max_length=200, description="用户选择的标题")
    topic: str = Field(..., min_length=1, max_length=500, description="原始选题")
    style: str = Field(default="专业", max_length=50, description="文章风格")
    target_length: int = Field(default=2000, ge=500, le=10000, description="目标字数")
    extra_description: Optional[str] = Field(default=None, max_length=1000, description="用户补充描述")
    user_modifications: Optional[str] = Field(
        default=None, max_length=2000, description="用户修改建议（大纲优化时传入）"
    )
    current_outline: Optional[dict] = Field(
        default=None, description="当前大纲结构（大纲优化时传入）"
    )
    optimize_mode: bool = Field(default=False, description="是否为优化模式")


class Section(BaseModel):
    """大纲段落结构"""

    id: str = Field(..., description="段落唯一标识")
    title: str = Field(..., description="段落标题")
    level: int = Field(..., ge=1, le=5, description="层级深度")
    key_points: Optional[List[str]] = Field(default=None, description="要点列表")
    estimated_length: Optional[int] = Field(None, description="预估字数")
    subsections: Optional[List["Section"]] = Field(default=None, description="子段落列表")


class OutlineStructure(BaseModel):
    """完整大纲结构"""

    sections: List[Section] = Field(..., description="段落列表")


class OutlineAgentOutput(AgentOutput):
    """OutlineAgent 输出数据"""

    outline: OutlineStructure = Field(..., description="生成的文章大纲")
    estimated_length: int = Field(..., description="预估总字数")
    raw_response: Optional[str] = Field(default=None, description="原始 LLM 响应")


# ============ OutlineAgent 实现 ============


class OutlineAgent(BaseAgent):
    """
    大纲生成智能体

    功能：
    - 根据选定标题生成结构化文章大纲
    - 通过 SSE 流式推送大纲内容
    - 支持优化模式：根据用户修改建议优化现有大纲

    输入：
    - selected_title: 用户选择的标题
    - topic: 原始选题
    - style: 文章风格
    - target_length: 目标字数
    - extra_description: 补充描述
    - user_modifications: 用户修改建议（优化模式）
    - current_outline: 当前大纲（优化模式）

    输出：
    - outline: 结构化大纲
    - estimated_length: 预估字数
    """

    def __init__(
        self,
        llm_service=None,
        use_mock: bool = False,
        llm_provider: Optional[str] = None,
    ):
        super().__init__(llm_service, use_mock, llm_provider)
        self._template_name = "outline_generation"
        self._optimize_template_name = "outline_optimization"

    @property
    def name(self) -> str:
        return "OutlineAgent"

    @property
    def description(self) -> str:
        return "根据选定标题生成结构化文章大纲"

    async def execute(
        self,
        input_data: OutlineAgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> OutlineAgentOutput:
        """
        执行大纲生成任务

        Args:
            input_data: 大纲生成输入数据
            stream_callback: SSE 流式回调函数

        Returns:
            OutlineAgentOutput: 生成的文章大纲
        """
        if input_data.optimize_mode:
            logger.info(
                f"[OutlineAgent] 开始优化大纲: title={input_data.selected_title[:30]}..."
            )
            return await self._execute_optimize(input_data, stream_callback)
        else:
            logger.info(
                f"[OutlineAgent] 开始生成大纲: title={input_data.selected_title[:30]}..., "
                f"style={input_data.style}, length={input_data.target_length}"
            )
            return await self._execute_generate(input_data, stream_callback)

    async def _execute_generate(
        self,
        input_data: OutlineAgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> OutlineAgentOutput:
        """执行大纲生成（非优化模式）"""

        # 1. 加载 Prompt 模板
        try:
            template = self.load_prompt_template(self._template_name)
        except FileNotFoundError:
            logger.warning("[OutlineAgent] Prompt 模板不存在，使用默认模板")
            template = self._default_prompt_template()

        # 2. 填充模板变量
        prompt = self.fill_prompt_template(
            template,
            {
                "selected_title": input_data.selected_title,
                "topic": input_data.topic,
                "style": input_data.style,
                "target_length": input_data.target_length,
                "extra_description": input_data.extra_description or "无",
            },
        )

        # 3. 调用 LLM（带流式回调）
        response = await self.call_llm(
            prompt=prompt,
            stream_callback=stream_callback,
            temperature=0.7,
            max_tokens=3000,
        )

        # 4. 解析响应
        outline = self._parse_response(response)
        estimated_length = self._calculate_total_length(outline)

        logger.info(
            f"[OutlineAgent] 大纲生成完成，共 {len(outline.sections)} 个段落，"
            f"预估 {estimated_length} 字"
        )

        return OutlineAgentOutput(
            outline=outline,
            estimated_length=estimated_length,
            raw_response=response,
        )

    async def _execute_optimize(
        self,
        input_data: OutlineAgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> OutlineAgentOutput:
        """执行大纲优化"""

        # 1. 加载优化 Prompt 模板
        try:
            template = self.load_prompt_template(self._optimize_template_name)
        except FileNotFoundError:
            logger.warning("[OutlineAgent] 优化模板不存在，使用默认模板")
            template = self._default_optimize_template()

        # 2. 填充模板变量
        current_outline_json = json.dumps(
            input_data.current_outline, ensure_ascii=False, indent=2
        )

        prompt = self.fill_prompt_template(
            template,
            {
                "current_outline": current_outline_json,
                "user_modifications": input_data.user_modifications,
                "selected_title": input_data.selected_title,
                "style": input_data.style,
            },
        )

        # 3. 调用 LLM（带流式回调）
        response = await self.call_llm(
            prompt=prompt,
            stream_callback=stream_callback,
            temperature=0.6,  # 优化需要更保守
            max_tokens=3000,
        )

        # 4. 解析响应
        outline = self._parse_response(response)
        estimated_length = self._calculate_total_length(outline)

        logger.info(
            f"[OutlineAgent] 大纲优化完成，共 {len(outline.sections)} 个段落，"
            f"预估 {estimated_length} 字"
        )

        return OutlineAgentOutput(
            outline=outline,
            estimated_length=estimated_length,
            raw_response=response,
        )

    def _default_prompt_template(self) -> str:
        """默认生成 Prompt 模板"""
        return """
你是一位专业的文章结构规划专家。请根据以下信息生成一份结构化的文章大纲：

选定标题：{{selected_title}}
原始选题：{{topic}}
文章风格：{{style}}
目标字数：{{target_length}}
补充描述：{{extra_description}}

请按以下 JSON 格式输出大纲：
```json
{
  "sections": [
    {
      "id": "section_1",
      "title": "一、引言",
      "level": 1,
      "key_points": ["背景介绍", "问题引出"],
      "estimated_length": 300
    },
    ...
  ]
}
```

请开始生成大纲。
"""

    def _default_optimize_template(self) -> str:
        """默认优化 Prompt 模板"""
        return """
请根据用户修改建议优化现有大纲：

当前大纲：
{{current_outline}}

用户修改建议：
{{user_modifications}}

选定标题：{{selected_title}}
文章风格：{{style}}

请输出优化后的完整大纲 JSON 结构。
"""

    def _parse_response(self, response: str) -> OutlineStructure:
        """
        解析 LLM 响应，提取大纲结构

        Args:
            response: LLM 响应文本

        Returns:
            结构化大纲
        """
        # 尝试从响应中提取 JSON
        json_str = self._extract_json(response)

        if json_str:
            try:
                outline_dict = json.loads(json_str)
                return self._convert_to_outline(outline_dict)
            except json.JSONDecodeError as e:
                logger.warning(f"[OutlineAgent] JSON 解析失败: {e}")

        # JSON 解析失败，尝试 Markdown 解析
        logger.warning("[OutlineAgent] JSON 解析失败，尝试 Markdown 解析")
        return self._parse_markdown_outline(response)

    def _extract_json(self, response: str) -> Optional[str]:
        """
        从响应中提取 JSON 字符串

        支持提取：
        1. Markdown 代码块中的 JSON
        2. 直接嵌入的 JSON 对象
        """
        # 尝试提取代码块中的 JSON
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(code_block_pattern, response)

        for match in matches:
            # 清理匹配内容
            json_str = match.strip()
            if json_str.startswith("{") and json_str.endswith("}"):
                return json_str

        # 尝试直接提取 JSON 对象
        json_pattern = r"\{[\s\S]*\"sections\"[\s\S]*\}"
        match = re.search(json_pattern, response)
        if match:
            return match.group(0)

        return None

    def _convert_to_outline(self, outline_dict: dict) -> OutlineStructure:
        """
        将字典转换为 OutlineStructure 对象

        Args:
            outline_dict: 大纲字典

        Returns:
            OutlineStructure 对象
        """
        sections = []

        for section_data in outline_dict.get("sections", []):
            section = self._create_section(section_data)
            sections.append(section)

        return OutlineStructure(sections=sections)

    def _create_section(self, section_data: dict) -> Section:
        """
        创建单个 Section 对象

        Args:
            section_data: 段落数据字典

        Returns:
            Section 对象
        """
        subsections = None
        if section_data.get("subsections"):
            subsections = [
                self._create_section(sub) for sub in section_data["subsections"]
            ]

        return Section(
            id=section_data.get("id", f"section_{len(section_data)}"),
            title=section_data.get("title", ""),
            level=section_data.get("level", 1),
            key_points=section_data.get("key_points"),
            estimated_length=section_data.get("estimated_length"),
            subsections=subsections,
        )

    def _parse_markdown_outline(self, response: str) -> OutlineStructure:
        """
        从 Markdown 格式解析大纲（备用方案）

        Args:
            response: LLM 响应文本

        Returns:
            OutlineStructure 对象
        """
        sections = []
        lines = response.split("\n")
        section_counter = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测标题行
            if re.match(r"^#+\s", line):
                # 提取标题层级和内容
                match = re.match(r"^(\#+)\s+(.+)", line)
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip()

                    section_counter += 1
                    sections.append(
                        Section(
                            id=f"section_{section_counter}",
                            title=title,
                            level=level,
                            key_points=[],
                            estimated_length=300,
                        )
                    )

            # 检测数字标题行（如"一、引言"、"二、核心观点"）
            elif re.match(r"^[一二三四五六七八九十]+[、.]", line):
                match = re.match(r"^[一二三四五六七八九十]+[、.]\s*(.+)", line)
                if match:
                    title = match.group(1).strip()

                    section_counter += 1
                    sections.append(
                        Section(
                            id=f"section_{section_counter}",
                            title=title,
                            level=1,
                            key_points=[],
                            estimated_length=500,
                        )
                    )

        # 如果没有解析到任何段落，创建默认大纲
        if not sections:
            logger.warning("[OutlineAgent] Markdown 解析失败，使用默认大纲")
            sections = [
                Section(id="section_1", title="引言", level=1, key_points=["背景介绍"], estimated_length=300),
                Section(id="section_2", title="核心内容", level=1, key_points=["主要内容"], estimated_length=1000),
                Section(id="section_3", title="总结", level=1, key_points=["总结要点"], estimated_length=300),
            ]

        return OutlineStructure(sections=sections)

    def _calculate_total_length(self, outline: OutlineStructure) -> int:
        """
        计算大纲预估总字数

        Args:
            outline: 大纲结构

        Returns:
            预估总字数
        """
        total = 0

        for section in outline.sections:
            if section.estimated_length:
                total += section.estimated_length
            else:
                # 默认估算
                total += 400 if section.level == 1 else 200

            # 计算子段落
            if section.subsections:
                for sub in section.subsections:
                    if sub.estimated_length:
                        total += sub.estimated_length
                    else:
                        total += 200

        return total


# ============ 工厂函数 ============


def create_outline_agent(
    use_mock: bool = False,
    llm_provider: Optional[str] = None,
) -> OutlineAgent:
    """
    创建 OutlineAgent 实例

    Args:
        use_mock: 是否使用 mock LLM
        llm_provider: LLM 提供者

    Returns:
        OutlineAgent 实例
    """
    return OutlineAgent(use_mock=use_mock, llm_provider=llm_provider)


# ============ Mock 响应数据 ============


MOCK_OUTLINE_RESPONSE = """
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