"""
智能体模块初始化
五大智能体协作系统
"""

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from app.agents.title_agent import (
    TitleAgent,
    TitleAgentInput,
    TitleAgentOutput,
    TitleOption,
    create_title_agent,
)
from app.agents.outline_agent import (
    OutlineAgent,
    OutlineAgentInput,
    OutlineAgentOutput,
    OutlineStructure,
    Section,
    create_outline_agent,
    MOCK_OUTLINE_RESPONSE,
)
from app.agents.content_agent import (
    ContentAgent,
    ContentAgentInput,
    ContentAgentOutput,
    ImagePlaceholder,
    create_content_agent,
    MOCK_CONTENT_RESPONSE,
)
from app.agents.image_analyzer_agent import (
    ImageAnalyzerAgent,
    ImageAnalyzerInput,
    ImageAnalyzerOutput,
    PlaceholderParseResult,
    PlaceholderParseError,
    create_image_analyzer_agent,
    EXAMPLE_CONTENT_WITH_PLACEHOLDERS,
    EXAMPLE_CONTENT_NO_PLACEHOLDERS,
    EXAMPLE_CONTENT_INVALID_PLACEHOLDER,
)
from app.agents.image_generator_agent import (
    ImageGeneratorAgent,
    ImageGeneratorInput,
    ImageGeneratorOutput,
    create_image_generator_agent,
)

__all__ = [
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    # TitleAgent
    "TitleAgent",
    "TitleAgentInput",
    "TitleAgentOutput",
    "TitleOption",
    "create_title_agent",
    # OutlineAgent
    "OutlineAgent",
    "OutlineAgentInput",
    "OutlineAgentOutput",
    "OutlineStructure",
    "Section",
    "create_outline_agent",
    "MOCK_OUTLINE_RESPONSE",
    # ContentAgent
    "ContentAgent",
    "ContentAgentInput",
    "ContentAgentOutput",
    "ImagePlaceholder",
    "create_content_agent",
    "MOCK_CONTENT_RESPONSE",
    # ImageAnalyzerAgent
    "ImageAnalyzerAgent",
    "ImageAnalyzerInput",
    "ImageAnalyzerOutput",
    "PlaceholderParseResult",
    "PlaceholderParseError",
    "create_image_analyzer_agent",
    "EXAMPLE_CONTENT_WITH_PLACEHOLDERS",
    "EXAMPLE_CONTENT_NO_PLACEHOLDERS",
    "EXAMPLE_CONTENT_INVALID_PLACEHOLDER",
    # ImageGeneratorAgent
    "ImageGeneratorAgent",
    "ImageGeneratorInput",
    "ImageGeneratorOutput",
    "create_image_generator_agent",
]