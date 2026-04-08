"""
路由子模块初始化
"""

from app.api.routes.health import router as health_router
from app.api.routes.task import router as task_router
from app.api.routes.article import router as article_router
from app.api.routes.sse import router as sse_router

__all__ = ["health_router", "task_router", "article_router", "sse_router"]