"""
智能体 3: ContentAgent (正文生成)
根据标题和大纲生成完整 Markdown 正文，包含配图占位符
"""

import logging
import re
from typing import Optional, Callable, List
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput


logger = logging.getLogger(__name__)


# ============ 输入输出数据结构 ============


class ContentAgentInput(AgentInput):
    """ContentAgent 输入数据"""

    selected_title: str = Field(..., min_length=1, max_length=200, description="选定的标题")
    outline: dict = Field(..., description="确认后的文章大纲")
    style: str = Field(default="专业", max_length=50, description="文章风格")
    extra_context: Optional[str] = Field(
        default=None, max_length=1000, description="额外上下文信息"
    )


class ImagePlaceholder(BaseModel):
    """配图占位符信息"""

    position: str = Field(..., description="位置标识，如 image_1, image_2")
    section_id: str = Field(..., description="所属段落 ID")
    keywords: List[str] = Field(default_factory=list, description="配图描述关键词")
    image_type: str = Field(default="photo", description="图片类型建议: photo/diagram/icon")


class ContentAgentOutput(AgentOutput):
    """ContentAgent 输出数据"""

    content: str = Field(..., description="Markdown 格式正文内容")
    image_placeholders: List[ImagePlaceholder] = Field(
        default_factory=list, description="配图占位符列表"
    )
    word_count: int = Field(default=0, description="字数统计")
    raw_response: Optional[str] = Field(default=None, description="原始 LLM 响应")


# ============ ContentAgent 实现 ============


class ContentAgent(BaseAgent):
    """
    正文生成智能体

    功能：
    - 根据标题和确认大纲生成完整 Markdown 正文
    - 在适当位置插入配图占位符
    - 流式输出正文内容

    输入：
    - selected_title: 选定的标题
    - outline: 确认后的文章大纲
    - style: 文章风格
    - extra_context: 额外上下文（可选）

    输出：
    - content: Markdown 正文（包含配图占位符）
    - image_placeholders: 配图占位符信息列表
    - word_count: 字数统计
    """

    def __init__(
        self,
        llm_service=None,
        use_mock: bool = False,
        llm_provider: Optional[str] = None,
    ):
        super().__init__(llm_service, use_mock, llm_provider)
        self._template_name = "content_generation"

    @property
    def name(self) -> str:
        return "ContentAgent"

    @property
    def description(self) -> str:
        return "根据标题和大纲生成完整 Markdown 正文"

    async def execute(
        self,
        input_data: ContentAgentInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> ContentAgentOutput:
        """
        执行正文生成任务

        Args:
            input_data: 正文生成输入数据
            stream_callback: SSE 流式回调函数

        Returns:
            ContentAgentOutput: 生成的正文内容
        """
        logger.info(
            f"[ContentAgent] 开始生成正文: title={input_data.selected_title[:30]}..., "
            f"style={input_data.style}"
        )

        # 1. 加载 Prompt 模板
        try:
            template = self.load_prompt_template(self._template_name)
        except FileNotFoundError:
            logger.warning("[ContentAgent] Prompt 模板不存在，使用默认模板")
            template = self._default_prompt_template()

        # 2. 将大纲转换为可读格式
        outline_text = self._outline_to_text(input_data.outline)

        # 3. 填充模板变量
        prompt = self.fill_prompt_template(
            template,
            {
                "selected_title": input_data.selected_title,
                "outline": outline_text,
                "style": input_data.style,
                "extra_context": input_data.extra_context or "无",
            },
        )

        # 4. 调用 LLM（带流式回调）
        response = await self.call_llm(
            prompt=prompt,
            stream_callback=stream_callback,
            temperature=0.7,
            max_tokens=8000,  # 正文生成需要更长的输出
        )

        # 5. 提取配图占位符信息
        image_placeholders = self._extract_image_placeholders(response)

        # 6. 计算字数（排除配图占位符）
        word_count = self._count_words(response)

        logger.info(
            f"[ContentAgent] 正文生成完成，共 {word_count} 字，"
            f"包含 {len(image_placeholders)} 个配图占位符"
        )

        return ContentAgentOutput(
            content=response,
            image_placeholders=image_placeholders,
            word_count=word_count,
            raw_response=response,
        )

    def _default_prompt_template(self) -> str:
        """默认生成 Prompt 模板"""
        return """
你是一位专业的自媒体文章撰稿专家。请根据以下信息撰写一篇高质量的 Markdown 格式文章：

选定标题：{{selected_title}}

文章大纲：
{{outline}}

文章风格：{{style}}

额外上下文：{{extra_context}}

请严格按照以下要求撰写正文：

1. **格式要求**：
   - 使用标准 Markdown 格式
   - 标题使用 # ## ### 符号
   - 每个段落之间保持合理的结构层次

2. **内容要求**：
   - 根据大纲逐段展开内容
   - 内容要丰富、有深度，不要泛泛而谈
   - 每个段落要紧扣主题，逻辑清晰
   - 根据文章风格调整语言风格

3. **配图要求**：
   - 在每个重要段落后，判断是否需要配图
   - 如需配图，插入占位符，格式为：![IMAGE_PLACEHOLDER](image_N|配图描述关键词)
   - 例如：![IMAGE_PLACEHOLDER](image_1|科技创新、人工智能、未来趋势)
   - 配图描述关键词用中文逗号分隔，3-5个关键词
   - image_N 中的 N 从 1 开始递增

4. **字数要求**：
   - 正文总字数控制在 2000-3000 字
   - 每个段落要有足够的内容支撑观点

请开始撰写正文，直接输出 Markdown 内容，不需要任何前言或解释。
"""

    def _outline_to_text(self, outline: dict) -> str:
        """
        将大纲字典转换为可读文本格式

        Args:
            outline: 大纲结构字典

        Returns:
            可读的大纲文本
        """
        if not outline or "sections" not in outline:
            return "暂无大纲"

        text_lines = []

        def process_section(section: dict, level: int = 0):
            indent = "  " * level

            title = section.get("title", "")
            key_points = section.get("key_points", [])
            estimated_length = section.get("estimated_length", 0)

            # 添加段落标题
            text_lines.append(f"{indent}{'#' * (level + 1)} {title}")

            # 添加要点提示
            if key_points:
                points_text = ", ".join(key_points)
                text_lines.append(f"{indent}  要点：{points_text}")

            if estimated_length:
                text_lines.append(f"{indent}  预估字数：{estimated_length}")

            text_lines.append("")  # 空行分隔

            # 处理子段落
            subsections = section.get("subsections", [])
            if subsections:
                for sub in subsections:
                    process_section(sub, level + 1)

        for section in outline.get("sections", []):
            process_section(section, 0)

        return "\n".join(text_lines)

    def _extract_image_placeholders(self, content: str) -> List[ImagePlaceholder]:
        """
        从正文内容中提取配图占位符信息

        Args:
            content: Markdown 正文内容

        Returns:
            配图占位符信息列表
        """
        placeholders = []

        # 正则匹配：![IMAGE_PLACEHOLDER](image_N|关键词)
        pattern = r"!\[IMAGE_PLACEHOLDER\]\(image_(\d+)\|([^)]+)\)"

        matches = re.findall(pattern, content)

        for match in matches:
            image_num = match[0]
            keywords_str = match[1]

            # 解析关键词
            keywords = [
                kw.strip()
                for kw in keywords_str.replace("，", ",").split(",")
                if kw.strip()
            ]

            placeholders.append(
                ImagePlaceholder(
                    position=f"image_{image_num}",
                    section_id=f"section_{image_num}",  # 简化处理，后续由 ImageAnalyzerAgent 精确定位
                    keywords=keywords,
                    image_type="photo",  # 默认图片类型
                )
            )

        logger.info(f"[ContentAgent] 提取到 {len(placeholders)} 个配图占位符")

        return placeholders

    def _count_words(self, content: str) -> int:
        """
        计算正文字数（排除配图占位符）

        Args:
            content: 正文内容

        Returns:
            字数
        """
        # 移除配图占位符
        clean_content = re.sub(r"!\[IMAGE_PLACEHOLDER\]\([^)]+\)", "", content)

        # 移除 Markdown 标记符号
        clean_content = re.sub(r"[#*_`\[\]]", "", clean_content)

        # 计算中文字符和英文单词
        chinese_chars = len(re.findall(r"[^\x00-\xff]", clean_content))
        english_words = len(re.findall(r"\b[a-zA-Z]+\b", clean_content))

        return chinese_chars + english_words


# ============ 工厂函数 ============


def create_content_agent(
    use_mock: bool = False,
    llm_provider: Optional[str] = None,
) -> ContentAgent:
    """
    创建 ContentAgent 实例

    Args:
        use_mock: 是否使用 mock LLM
        llm_provider: LLM 提供者

    Returns:
        ContentAgent 实例
    """
    return ContentAgent(use_mock=use_mock, llm_provider=llm_provider)


# ============ Mock 响应数据 ============


MOCK_CONTENT_RESPONSE = """
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