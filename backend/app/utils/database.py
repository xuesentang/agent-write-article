"""
数据库配置和会话管理
使用 SQLAlchemy 异步引擎连接 SQLite
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings
from app.models import Base


# 数据库文件目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 异步引擎配置
# SQLite 使用 aiosqlite 作为异步驱动
# echo=True 在开发模式下打印 SQL 语句，便于调试
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # SQLite 特定配置
    connect_args={"check_same_thread": False},  # 允许多线程访问
)

# 异步会话工厂
# expire_on_commit=False 防止对象在提交后过期，避免额外查询
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # 手动控制 flush
)


async def init_db():
    """
    初始化数据库

    创建所有表结构。SQLite 会自动创建数据库文件。
    使用 WAL 模式提高并发性能。
    自动检测并添加新字段（兼容已有数据库）。
    """
    async with engine.begin() as conn:
        # 设置 SQLite WAL 模式（写前日志），提高并发性能
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # 设置同步模式为 NORMAL，平衡性能和安全
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        # 设置缓存大小（负数表示 KB）
        await conn.execute(text("PRAGMA cache_size=-64000"))

        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

        # 自动迁移：检测并添加 final_html 字段
        try:
            result = await conn.execute(text("PRAGMA table_info(articles)"))
            columns = [row[1] for row in result.fetchall()]
            if 'final_html' not in columns:
                await conn.execute(text(
                    "ALTER TABLE articles ADD COLUMN final_html TEXT"
                ))
                print("✅ 已添加 final_html 字段到 articles 表")
        except Exception as e:
            print(f"⚠️ 自动迁移 final_html 字段时出错（可能字段已存在）: {e}")

    print("✅ 数据库初始化完成")


async def close_db():
    """
    关闭数据库连接

    在应用关闭时调用，释放所有连接资源。
    """
    await engine.dispose()
    print("✅ 数据库连接已关闭")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（上下文管理器）

    使用方式：
        async with get_db_session() as session:
            result = await session.execute(...)

    自动处理事务：成功时提交，失败时回滚。
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：获取数据库会话

    使用方式：
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    注意：此函数返回生成器，需要在路由中使用 Depends。
    """
    async with get_db_session() as session:
        yield session


async def check_db_health() -> dict:
    """
    检查数据库健康状态

    返回数据库连接信息和基本统计。
    用于健康检查接口。
    """
    try:
        async with get_db_session() as session:
            # 执行简单查询测试连接
            result = await session.execute(text("SELECT 1"))
            result.fetchone()

            # 获取表记录数统计
            task_count = await session.execute(text("SELECT COUNT(*) FROM tasks"))
            article_count = await session.execute(text("SELECT COUNT(*) FROM articles"))

            return {
                "status": "healthy",
                "connected": True,
                "tables": {
                    "tasks": task_count.scalar() or 0,
                    "articles": article_count.scalar() or 0,
                },
                "database_type": "SQLite",
                "journal_mode": "WAL",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }