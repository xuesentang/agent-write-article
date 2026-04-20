"""
数据库初始化脚本
手动执行此脚本创建数据库表结构
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.database import init_db, close_db


async def main():
    """初始化数据库"""
    print("=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)

    print("\n开始创建数据库表...")

    try:
        await init_db()
        print("\n✅ 数据库初始化成功!")
        print("\n创建的表:")
        print("  - users    (用户表)")
        print("  - tasks    (任务表)")
        print("  - articles (文章表)")
        print("\n数据库文件位置: backend/data/article.db")
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        sys.exit(1)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())