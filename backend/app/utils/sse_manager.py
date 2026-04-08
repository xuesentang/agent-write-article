"""
SSE 连接管理器
管理 Server-Sent Events 连接，支持按 task_id 管理连接
"""

import asyncio
import json
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager

from app.schemas.sse import (
    SSEEventData,
    SSEEventType,
    SSEStage,
    StatusEventData,
    TitleChunkEventData,
    TitleCompleteEventData,
    OutlineChunkEventData,
    OutlineCompleteEventData,
    ContentChunkEventData,
    ContentCompleteEventData,
    ImageProgressEventData,
    ImageCompleteEventData,
    ErrorEventData,
    DoneEventData,
)


class SSEConnection:
    """
    单个 SSE 连接

    封装单个 SSE 连接的消息队列和状态管理。
    """

    def __init__(self, task_id: str, timeout: int = 1800):
        """
        初始化 SSE 连接

        Args:
            task_id: 任务 ID
            timeout: 连接超时时间（秒），默认 30 分钟
        """
        self.task_id = task_id
        self.timeout = timeout
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        self.event_counter = 0

    async def send(self, event_data: SSEEventData) -> int:
        """
        发送事件到消息队列

        Args:
            event_data: 事件数据

        Returns:
            事件序号
        """
        if not self.is_active:
            return -1

        self.event_counter += 1
        self.last_activity = datetime.now()
        await self.message_queue.put((self.event_counter, event_data))
        return self.event_counter

    async def receive(self) -> AsyncGenerator[str, None]:
        """
        从消息队列接收事件（生成器）

        Yields:
            SSE 格式的事件字符串
        """
        while self.is_active:
            try:
                # 等待消息，带超时
                event_id, event_data = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=30.0,  # 30 秒超时（用于心跳）
                )
                yield event_data.to_sse_format(event_id)
            except asyncio.TimeoutError:
                # 超时，发送心跳
                heartbeat = SSEEventData(
                    event=SSEEventType.HEARTBEAT,
                    message="heartbeat",
                    timestamp=datetime.now().isoformat(),
                )
                yield heartbeat.to_sse_format()

    def close(self):
        """关闭连接"""
        self.is_active = False


class SSEManager:
    """
    SSE 连接管理器

    管理所有 SSE 连接，支持：
    - 按 task_id 创建和管理连接
    - 发送不同类型的事件
    - 连接超时和断开处理
    """

    def __init__(self):
        """初始化 SSE 管理器"""
        # task_id -> SSEConnection 映射
        self.connections: Dict[str, SSEConnection] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def create_connection(self, task_id: str, timeout: int = 1800):
        """
        创建 SSE 连接（上下文管理器）

        使用方式：
            async with sse_manager.create_connection(task_id) as conn:
                async for event in conn.receive():
                    yield event

        Args:
            task_id: 任务 ID
            timeout: 连接超时时间（秒）

        Yields:
            SSEConnection 实例
        """
        conn = SSEConnection(task_id, timeout)

        async with self._lock:
            # 如果已存在连接，先关闭旧连接
            if task_id in self.connections:
                old_conn = self.connections[task_id]
                old_conn.close()
                print(f"[SSE] 关闭旧连接: task_id={task_id}")

            self.connections[task_id] = conn
            print(f"[SSE] 创建连接: task_id={task_id}")

        try:
            yield conn
        finally:
            async with self._lock:
                if task_id in self.connections:
                    conn.close()
                    del self.connections[task_id]
                    print(f"[SSE] 断开连接: task_id={task_id}")

    async def get_connection(self, task_id: str) -> Optional[SSEConnection]:
        """
        获取指定任务的连接

        Args:
            task_id: 任务 ID

        Returns:
            SSEConnection 实例或 None
        """
        return self.connections.get(task_id)

    async def send_event(
        self,
        task_id: str,
        event_type: SSEEventType,
        data: any = None,
        stage: Optional[SSEStage] = None,
        progress: int = 0,
        message: Optional[str] = None,
    ) -> bool:
        """
        发送 SSE 事件

        Args:
            task_id: 任务 ID
            event_type: 事件类型
            data: 事件数据
            stage: 当前阶段
            progress: 进度百分比
            message: 人类可读的消息

        Returns:
            是否发送成功
        """
        conn = await self.get_connection(task_id)
        if not conn:
            print(f"[SSE] 连接不存在: task_id={task_id}")
            return False

        event_data = SSEEventData(
            event=event_type,
            stage=stage,
            data=data,
            progress=progress,
            message=message,
        )

        event_id = await conn.send(event_data)
        print(f"[SSE] 发送事件: task_id={task_id}, event={event_type.value}, id={event_id}")
        return event_id > 0

    # ============ 便捷方法：发送特定类型事件 ============

    async def send_status(
        self, task_id: str, status: str, message: str, progress: int = 0
    ) -> bool:
        """发送状态变更事件"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.STATUS,
            data=StatusEventData(status=status, message=message).model_dump(),
            progress=progress,
            message=message,
        )

    async def send_title_chunk(
        self, task_id: str, content: str, index: int, progress: int = 0
    ) -> bool:
        """发送标题生成片段"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.TITLE_CHUNK,
            stage=SSEStage.TITLE,
            data=TitleChunkEventData(content=content, index=index).model_dump(),
            progress=progress,
        )

    async def send_title_complete(
        self, task_id: str, titles: list, progress: int = 20
    ) -> bool:
        """发送标题生成完成"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.TITLE_COMPLETE,
            stage=SSEStage.TITLE,
            data=TitleCompleteEventData(titles=titles).model_dump(),
            progress=progress,
            message="标题生成完成",
        )

    async def send_outline_chunk(
        self, task_id: str, content: str, progress: int = 0
    ) -> bool:
        """发送大纲生成片段"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.OUTLINE_CHUNK,
            stage=SSEStage.OUTLINE,
            data=OutlineChunkEventData(content=content).model_dump(),
            progress=progress,
        )

    async def send_outline_complete(
        self, task_id: str, outline: dict, progress: int = 40
    ) -> bool:
        """发送大纲生成完成"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.OUTLINE_COMPLETE,
            stage=SSEStage.OUTLINE,
            data=OutlineCompleteEventData(outline=outline).model_dump(),
            progress=progress,
            message="大纲生成完成",
        )

    async def send_content_chunk(
        self, task_id: str, content: str, progress: int = 0
    ) -> bool:
        """发送正文生成片段"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.CONTENT_CHUNK,
            stage=SSEStage.CONTENT,
            data=ContentChunkEventData(content=content).model_dump(),
            progress=progress,
        )

    async def send_content_complete(
        self, task_id: str, content: str, word_count: int, image_count: int = 0, progress: int = 60
    ) -> bool:
        """发送正文生成完成"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.CONTENT_COMPLETE,
            stage=SSEStage.CONTENT,
            data=ContentCompleteEventData(
                content=content, word_count=word_count, image_count=image_count
            ).model_dump(),
            progress=progress,
            message="正文生成完成",
        )

    async def send_image_progress(
        self,
        task_id: str,
        position: str,
        status: str,
        provider: Optional[str] = None,
        progress: int = 0,
    ) -> bool:
        """发送配图生成进度"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_PROGRESS,
            stage=SSEStage.IMAGE,
            data=ImageProgressEventData(
                position=position, status=status, provider=provider
            ).model_dump(),
            progress=progress,
        )

    async def send_image_complete(
        self, task_id: str, position: str, url: str, source: str, progress: int = 0
    ) -> bool:
        """发送配图生成完成"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_COMPLETE,
            stage=SSEStage.IMAGE,
            data=ImageCompleteEventData(
                position=position, url=url, source=source
            ).model_dump(),
            progress=progress,
        )

    async def send_error(
        self,
        task_id: str,
        code: str,
        message: str,
        details: Optional[str] = None,
    ) -> bool:
        """发送错误事件"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.ERROR,
            data=ErrorEventData(
                code=code, message=message, details=details
            ).model_dump(),
            message=message,
        )

    async def send_done(self, task_id: str, article_id: str) -> bool:
        """发送任务完成事件"""
        return await self.send_event(
            task_id=task_id,
            event_type=SSEEventType.DONE,
            data=DoneEventData(article_id=article_id).model_dump(),
            progress=100,
            message="文章生成完成",
        )

    def get_connection_count(self) -> int:
        """获取当前连接数量"""
        return len(self.connections)

    def get_active_tasks(self) -> list:
        """获取所有活跃任务的 task_id 列表"""
        return list(self.connections.keys())


# 全局 SSE 管理器实例
sse_manager = SSEManager()