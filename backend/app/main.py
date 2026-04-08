"""
FastAPI 应用入口
自媒体爆款文章生成器后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import health_router, task_router, article_router, sse_router
from app.utils.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    await init_db()
    yield
    # Shutdown
    print("👋 应用关闭中...")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="自媒体爆款文章生成器 - 多智能体协作流式生成系统",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",  # Vite 默认端口
        "http://localhost:3000",  # 备用端口
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api", tags=["健康检查"])
app.include_router(task_router, prefix="/api", tags=["任务管理"])
app.include_router(article_router, prefix="/api", tags=["文章管理"])
app.include_router(sse_router, prefix="/api", tags=["SSE 流式推送"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎来到 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }