"""
应用配置管理
使用 pydantic-settings 从环境变量加载配置
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    # 应用基础配置
    APP_NAME: str = "自媒体爆款文章生成器"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/article.db"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # LLM API 配置 - DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # LLM API 配置 - 智谱
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-4.7"

    # LLM API 配置 - 千问
    QIANWEN_API_KEY: Optional[str] = None
    QIANWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QIANWEN_MODEL: str = "qwen-plus"

    # 默认 LLM
    DEFAULT_LLM_PROVIDER: str = "deepseek"

    # 腾讯云 COS 配置
    COS_SECRET_ID: Optional[str] = None
    COS_SECRET_KEY: Optional[str] = None
    COS_BUCKET: Optional[str] = None
    COS_REGION: str = "ap-shanghai"
    COS_UPLOAD_PATH: str = "article-images/"

    # 配图服务配置
    PEXELS_API_KEY: Optional[str] = None
    ICONIFY_API_URL: str = "https://api.iconify.design"
    SEEDREAM_API_KEY: Optional[str] = None
    SEEDREAM_BASE_URL: str = "https://api.seedream.ai/v1"
    SEEDREAM_ENDPOINT_ID: Optional[str] = None

    # 前端 URL
    FRONTEND_URL: str = "http://localhost:5173"

    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """获取指定 LLM 提供者的配置"""
        provider = provider or self.DEFAULT_LLM_PROVIDER

        configs = {
            "deepseek": {
                "api_key": self.DEEPSEEK_API_KEY,
                "base_url": self.DEEPSEEK_BASE_URL,
                "model": self.DEEPSEEK_MODEL,
            },
            "zhipu": {
                "api_key": self.ZHIPU_API_KEY,
                "base_url": self.ZHIPU_BASE_URL,
                "model": self.ZHIPU_MODEL,
            },
            "qianwen": {
                "api_key": self.QIANWEN_API_KEY,
                "base_url": self.QIANWEN_BASE_URL,
                "model": self.QIANWEN_MODEL,
            },
        }

        return configs.get(provider, configs[self.DEFAULT_LLM_PROVIDER])


# 全局配置实例
settings = Settings()