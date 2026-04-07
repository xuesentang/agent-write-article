"""
路由子模块初始化
"""

from app.api.routes.health import router as health_router

__all__ = ["health_router"]