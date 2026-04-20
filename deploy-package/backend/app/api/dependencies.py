"""
依赖注入模块
管理共享资源和依赖项
"""

from fastapi import Depends
from typing import Generator

from app.config import settings


# TODO: 后续添加数据库会话、Redis 连接等依赖项


def get_settings():
    """获取配置"""
    return settings