"""
智能体 4: ImageAnalyzerAgent (图片分析)
解析正文中的 IMAGE_PLACEHOLDER 占位符，生成结构化图片任务列表
"""

import hashlib
import logging
import re
import uuid
from typing import Optional, Callable, List, Tuple

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from app.schemas.image import (
    ImageType,
    ImageProvider,
    ImageTaskStatus,
    ImageTask,
    ImageAnalyzerInput,
    ImageAnalyzerOutput,
)


logger = logging.getLogger(__name__)


# ============ 占位符解析数据结构 ============


class PlaceholderParseResult(BaseModel):
    """单个占位符解析结果"""

    position: int = Field(..., description="位置索引")
    placeholderId: str = Field(..., description="占位符ID")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    rawText: str = Field(..., description="原始占位符文本")
    isValid: bool = Field(default=True, description="是否格式有效")
    errorMessage: Optional[str] = Field(None, description="错误信息")
    context: Optional[str] = Field(None, description="占位符前一个自然段的上下文内容")


class PlaceholderParseError(BaseModel):
    """占位符解析错误"""

    position: int = Field(..., description="错误位置")
    rawText: str = Field(..., description="原始文本")
    errorMessage: str = Field(..., description="错误描述")
    errorType: str = Field(default="format_error", description="错误类型")


# ============ ImageAnalyzerAgent 实现 ============


class ImageAnalyzerAgent(BaseAgent):
    """
    图片分析智能体

    功能：
    - 解析 Markdown 正文中的 IMAGE_PLACEHOLDER 占位符
    - 生成结构化图片任务列表
    - 保证占位符顺序与正文顺序一致
    - 处理格式错误并返回可识别错误

    输入：
    - content: Markdown 格式正文内容
    - imagePlaceholders: ContentAgent 提取的占位符列表（可选辅助）

    输出：
    - tasks: 结构化图片任务列表
    - totalCount: 任务总数
    - contentHash: 正文内容 hash
    - parseErrors: 解析错误列表（如有）
    """

    # 占位符正则表达式
    # 格式: ![IMAGE_PLACEHOLDER](image_N|关键词1、关键词2、关键词3)
    PLACEHOLDER_PATTERN = r'!\[IMAGE_PLACEHOLDER\]\(image_(\d+)\|([^)]+)\)'

    # 关键词分隔符（支持中文逗号和英文逗号）
    KEYWORD_DELIMITERS = ['，', ',', '、']

    def __init__(self):
        """初始化图片分析智能体"""
        logger.info("[ImageAnalyzerAgent] 初始化开始")
        # ImageAnalyzerAgent 不需要 LLM，纯解析逻辑
        super().__init__(llm_service=None, use_mock=True)
        logger.info("[ImageAnalyzerAgent] 初始化完成")

    @property
    def name(self) -> str:
        return "ImageAnalyzerAgent"

    @property
    def description(self) -> str:
        return "解析正文中的 IMAGE_PLACEHOLDER 占位符，生成图片任务列表"

    async def execute(
        self,
        input_data: ImageAnalyzerInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> ImageAnalyzerOutput:
        """
        执行图片分析任务

        Args:
            input_data: 图片分析输入数据
            stream_callback: 流式回调函数（暂不使用）

        Returns:
            ImageAnalyzerOutput: 分析结果
        """
        logger.info(
            f"[ImageAnalyzerAgent] 开始分析正文，内容长度: {len(input_data.content)}"
        )

        # 1. 计算正文 hash（用于校验）
        content_hash = self._compute_content_hash(input_data.content)

        # 2. 解析所有占位符
        parse_results, parse_errors = self._parse_all_placeholders(input_data.content)

        # 3. 转换为图片任务列表
        tasks = self._convert_to_tasks(parse_results)

        # 4. 按位置排序
        tasks = sorted(tasks, key=lambda t: t.position)

        # 5. 生成输出
        output = ImageAnalyzerOutput(
            tasks=tasks,
            totalCount=len(tasks),
            contentHash=content_hash,
            parseErrors=parse_errors if parse_errors else None,
        )

        logger.info(
            f"[ImageAnalyzerAgent] 分析完成，共 {len(tasks)} 个图片任务，"
            f"{len(parse_errors)} 个解析错误"
        )

        return output

    def _compute_content_hash(self, content: str) -> str:
        """
        计算正文内容的 hash

        Args:
            content: 正文内容

        Returns:
            SHA256 hash 前缀（16位）
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _parse_all_placeholders(
        self, content: str
    ) -> Tuple[List[PlaceholderParseResult], List[dict]]:
        """
        解析正文中的所有占位符

        Args:
            content: 正文内容

        Returns:
            (解析结果列表, 解析错误列表)
        """
        results = []
        errors = []

        # 查找所有匹配的占位符
        matches = re.findall(self.PLACEHOLDER_PATTERN, content)

        # 同时获取所有匹配的原始文本（用于位置计算）
        full_matches = list(re.finditer(self.PLACEHOLDER_PATTERN, content))

        for idx, (image_num, keywords_str) in enumerate(matches):
            # 计算位置（从1开始）
            position = idx + 1

            # 解析关键词
            keywords = self._parse_keywords(keywords_str)

            # 推断图片类型
            image_type = self._infer_image_type(keywords)

            # 获取原始文本
            raw_text = full_matches[idx].group(0) if idx < len(full_matches) else ""

            # 提取占位符前一个自然段的上下文
            match_obj = full_matches[idx] if idx < len(full_matches) else None
            context = self._extract_preceding_paragraph(content, match_obj) if match_obj else None

            # 验证占位符ID格式
            placeholder_id = f"image_{image_num}"

            # 检查是否有重复的 placeholderId
            existing_ids = [r.placeholderId for r in results]
            if placeholder_id in existing_ids:
                error = PlaceholderParseError(
                    position=position,
                    rawText=raw_text,
                    errorMessage=f"重复的占位符ID: {placeholder_id}",
                    errorType="duplicate_id"
                )
                errors.append(error.model_dump())
                logger.warning(f"[ImageAnalyzerAgent] 发现重复占位符ID: {placeholder_id}")

            result = PlaceholderParseResult(
                position=position,
                placeholderId=placeholder_id,
                keywords=keywords,
                rawText=raw_text,
                isValid=True,
                context=context,
            )
            results.append(result)

        # 检查是否有格式不完整的占位符（如缺少关键词等）
        invalid_pattern = r'!\[IMAGE_PLACEHOLDER\]\([^|)]+\)'
        invalid_matches = list(re.finditer(invalid_pattern, content))

        for match in invalid_matches:
            # 检查是否已经被正确匹配
            matched_text = match.group(0)
            if not re.match(self.PLACEHOLDER_PATTERN, matched_text):
                error = PlaceholderParseError(
                    position=len(results) + len(errors) + 1,
                    rawText=matched_text,
                    errorMessage="占位符格式不完整，缺少关键词",
                    errorType="incomplete_format"
                )
                errors.append(error.model_dump())
                logger.warning(f"[ImageAnalyzerAgent] 发现格式不完整占位符: {matched_text}")

        return results, errors

    def _extract_preceding_paragraph(self, content: str, match_obj: re.Match) -> Optional[str]:
        """
        提取占位符前一个自然段的上下文内容

        以空行（连续两个换行符 \n\n）作为自然段分隔，
        取占位符所在位置之前的最后一个自然段。

        Args:
            content: 正文内容
            match_obj: 正则匹配对象

        Returns:
            前一个自然段的文本内容，如无则返回 None
        """
        if not match_obj:
            return None

        placeholder_start = match_obj.start()

        # 取占位符之前的全部内容
        before = content[:placeholder_start]

        # 按空行（\n\n）分割为自然段
        # 用正则分割以兼容 \r\n 等换行符
        paragraphs = re.split(r'\n\s*\n', before)

        # 过滤掉空段
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return None

        # 取最后一个自然段作为上下文
        context = paragraphs[-1]

        # 清理 markdown 标题标记（# 开头的行），保留纯文本
        lines = context.split('\n')
        clean_lines = []
        for line in lines:
            # 移除 markdown 标题标记
            cleaned = re.sub(r'^#{1,6}\s+', '', line)
            # 移除加粗/斜体标记
            cleaned = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', cleaned)
            clean_lines.append(cleaned)

        context = ' '.join(clean_lines).strip()

        # 限制长度，避免过长（取前 500 字）
        if len(context) > 500:
            context = context[:500]

        return context if context else None

    def _parse_keywords(self, keywords_str: str) -> List[str]:
        """
        解析关键词字符串

        支持中文逗号(，)、英文逗号(,)、顿号(、)分隔

        Args:
            keywords_str: 关键词字符串

        Returns:
            关键词列表
        """
        # 统一替换分隔符为英文逗号
        normalized = keywords_str
        for delimiter in ['，', '、']:
            normalized = normalized.replace(delimiter, ',')

        # 分割并清理
        keywords = [kw.strip() for kw in normalized.split(',') if kw.strip()]

        return keywords

    def _infer_image_type(self, keywords: List[str]) -> ImageType:
        """
        根据关键词推断图片类型

        Args:
            keywords: 关键词列表

        Returns:
            推断的图片类型
        """
        # 关键词类型推断规则
        icon_keywords = ['图标', 'icon', 'logo', '标志', '符号', '装饰']
        diagram_keywords = ['图表', '流程图', 'diagram', '架构', '关系图', '数据可视化']
        illustration_keywords = ['插画', '插图', '手绘', '卡通', 'illustration']

        # 转为小写便于匹配
        keywords_lower = [kw.lower() for kw in keywords]

        # 匹配规则
        for kw in keywords_lower:
            if any(icon_word in kw for icon_word in icon_keywords):
                return ImageType.ICON
            if any(diagram_word in kw for diagram_word in diagram_keywords):
                return ImageType.DIAGRAM
            if any(ill_word in kw for ill_word in illustration_keywords):
                return ImageType.ILLUSTRATION

        # 默认为照片类型（正文主图）
        return ImageType.PHOTO

    def _convert_to_tasks(
        self, parse_results: List[PlaceholderParseResult]
    ) -> List[ImageTask]:
        """
        将解析结果转换为图片任务列表

        Args:
            parse_results: 占位符解析结果列表

        Returns:
            图片任务列表
        """
        tasks = []

        for result in parse_results:
            # 根据图片类型确定服务提供商
            preferred_providers, fallback_providers = self._select_providers(
                self._infer_image_type(result.keywords)
            )

            # 生成任务描述
            description = self._generate_description(result.keywords, result.position)

            task = ImageTask(
                taskId=str(uuid.uuid4()),
                placeholderId=result.placeholderId,
                position=result.position,
                keywords=result.keywords,
                description=description,
                imageType=self._infer_image_type(result.keywords),
                preferredProviders=preferred_providers,
                fallbackProviders=fallback_providers,
                retryCount=0,
                maxRetries=2,
                status=ImageTaskStatus.PENDING,
                rawPlaceholderText=result.rawText,
                context=result.context,
            )
            tasks.append(task)

        return tasks

    def _select_providers(
        self, image_type: ImageType
    ) -> Tuple[List[ImageProvider], List[ImageProvider]]:
        """
        根据图片类型选择服务提供商

        简化为仅使用 Seedream 生成，Picsum 兜底

        Args:
            image_type: 图片类型

        Returns:
            (首选提供商列表, 备选提供商列表)
        """
        # 所有类型统一：Seedream 优先，Picsum 兜底
        return (
            [ImageProvider.SEEDREAM],
            [ImageProvider.PICSUM]
        )

    def _generate_description(self, keywords: List[str], position: int) -> str:
        """
        生成图片用途描述

        Args:
            keywords: 关键词列表
            position: 位置索引

        Returns:
            描述文本
        """
        keywords_text = '、'.join(keywords[:3]) if keywords else '配图'
        return f"第{position}张配图，主题：{keywords_text}"


# ============ 工厂函数 ============


def create_image_analyzer_agent() -> ImageAnalyzerAgent:
    """
    创建 ImageAnalyzerAgent 实例

    Returns:
        ImageAnalyzerAgent 实例
    """
    return ImageAnalyzerAgent()


# ============ 示例输入输出 ============


EXAMPLE_CONTENT_WITH_PLACEHOLDERS = """
# 自媒体爆款文章的3个核心秘诀

在当今数字化时代，自媒体已经成为信息传播的重要渠道。

![IMAGE_PLACEHOLDER](image_1|自媒体、内容创作、数字化时代)

## 一、选题：爆款的第一步

选题是文章能否成为爆款的基础。

![IMAGE_PLACEHOLDER](image_2|热点追踪、热搜榜、趋势分析)

## 二、内容质量：爆款的根本

![IMAGE_PLACEHOLDER](image_3|内容创作、信息价值、知识增量)

## 三、传播技巧：爆款的助推器

![IMAGE_PLACEHOLDER](image_4|标题技巧、传播策略、用户吸引)

## 总结

希望这篇文章能帮助你更好地理解爆款文章的创作逻辑！
"""

EXAMPLE_CONTENT_NO_PLACEHOLDERS = """
# 简单文章标题

这是一篇简单的文章，没有配图需求。

正文内容只有纯文字描述，不需要任何图片。

## 第一段

详细说明第一段的内容。

## 第二段

继续展开论述。
"""

EXAMPLE_CONTENT_INVALID_PLACEHOLDER = """
# 测试文章

这里有正常的占位符：
![IMAGE_PLACEHOLDER](image_1|科技、创新)

这里有格式错误的占位符（缺少关键词）：
![IMAGE_PLACEHOLDER](image_2)

这里有另一个正常的占位符：
![IMAGE_PLACEHOLDER](image_3|测试、验证)
"""

# 示例输出（正常情况）
EXAMPLE_OUTPUT_NORMAL = {
    "tasks": [
        {
            "taskId": "550e8400-e29b-41d4-a716-446655440000",
            "placeholderId": "image_1",
            "position": 1,
            "keywords": ["自媒体", "内容创作", "数字化时代"],
            "description": "第1张配图，主题：自媒体、内容创作、数字化时代",
            "imageType": "photo",
            "preferredProviders": ["pexels", "seedream"],
            "fallbackProviders": ["picsum"],
            "status": "pending"
        },
        {
            "taskId": "550e8400-e29b-41d4-a716-446655440001",
            "placeholderId": "image_2",
            "position": 2,
            "keywords": ["热点追踪", "热搜榜", "趋势分析"],
            "description": "第2张配图，主题：热点追踪、热搜榜、趋势分析",
            "imageType": "photo",
            "preferredProviders": ["pexels", "seedream"],
            "fallbackProviders": ["picsum"],
            "status": "pending"
        }
    ],
    "totalCount": 4,
    "contentHash": "a1b2c3d4e5f6g7h8",
    "parseErrors": None
}

# 示例输出（无占位符）
EXAMPLE_OUTPUT_EMPTY = {
    "tasks": [],
    "totalCount": 0,
    "contentHash": "x1y2z3a4b5c6d7e8",
    "parseErrors": None
}

# 示例输出（有格式错误）
EXAMPLE_OUTPUT_WITH_ERRORS = {
    "tasks": [
        {
            "taskId": "...",
            "placeholderId": "image_1",
            "position": 1,
            "keywords": ["科技", "创新"],
            "description": "第1张配图，主题：科技、创新",
            "imageType": "photo",
            "preferredProviders": ["pexels", "seedream"],
            "fallbackProviders": ["picsum"],
            "status": "pending"
        },
        {
            "taskId": "...",
            "placeholderId": "image_3",
            "position": 2,
            "keywords": ["测试", "验证"],
            "description": "第2张配图，主题：测试、验证",
            "imageType": "photo",
            "preferredProviders": ["pexels", "seedream"],
            "fallbackProviders": ["picsum"],
            "status": "pending"
        }
    ],
    "totalCount": 2,
    "contentHash": "...",
    "parseErrors": [
        {
            "position": 2,
            "rawText": "![IMAGE_PLACEHOLDER](image_2)",
            "errorMessage": "占位符格式不完整，缺少关键词",
            "errorType": "incomplete_format"
        }
    ]
}