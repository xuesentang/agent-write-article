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

# TODO: 后续添加其他智能体类
# from app.agents.outline_agent import OutlineAgent
# from app.agents.content_agent import ContentAgent
# from app.agents.image_analyzer_agent import ImageAnalyzerAgent
# from app.agents.image_generator_agent import ImageGeneratorAgent

__all__ = [
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    "TitleAgent",
    "TitleAgentInput",
    "TitleAgentOutput",
    "TitleOption",
    "create_title_agent",
]