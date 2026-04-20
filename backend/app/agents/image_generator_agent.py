"""
智能体 5: ImageGeneratorAgent (图片生成)
接收 Agent4 的任务列表，并行执行图片任务，上传 COS，合并图文
"""

import asyncio
import logging
import re
import time
from typing import Optional, Callable, List

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from app.schemas.image import (
    ImageTask,
    ImageResult,
    ImageGeneratorInput,
    ImageGeneratorOutput,
    ImageTaskStatus,
    ImageProvider,
)
from app.image.strategy import ImageServiceStrategy
from app.utils.cos_uploader import create_cos_uploader
from app.utils.sse_manager import sse_manager
from app.schemas.sse import SSEEventType, SSEStage


logger = logging.getLogger(__name__)


class ImageGeneratorAgent(BaseAgent):
    """
    图片生成智能体

    功能：
    - 接收 Agent4 的图片任务列表
    - 并行执行所有图片任务
    - 容错与降级：单图失败不阻塞整体
    - 上传腾讯云 COS
    - 图文合并：替换占位符为真实图片 URL
    - SSE 进度推送

    输入：
    - tasks: 图片任务列表
    - content: 原始正文内容
    - taskId: 文章生成任务 ID（用于 SSE）

    输出：
    - results: 图片结果列表
    - mergedContent: 合并后的正文
    - totalCount/successCount/failedCount: 统计

    硬性规则：
    1. 单图失败不阻塞整体流程
    2. Iconify 仅限图标/装饰，禁止正文主图
    3. 必须上传 COS，不返回临时 URL
    4. 合并时保证正文顺序不乱
    """

    def __init__(
        self,
        strategy: Optional[ImageServiceStrategy] = None,
        cos_uploader: Optional[object] = None,
        use_mock: bool = False,
    ):
        """
        初始化图片生成智能体

        Args:
            strategy: 图片服务策略（可选，默认使用全部服务）
            cos_uploader: COS 上传服务（可选，默认使用配置）
            use_mock: 是否使用 Mock 实现（用于测试）
        """
        logger.info(f"[ImageGeneratorAgent] 初始化开始, use_mock={use_mock}")

        # 使用提供的策略或创建默认策略
        if strategy is None:
            try:
                from app.image import create_default_image_strategy
                strategy = create_default_image_strategy(use_mock)
                logger.info(f"[ImageGeneratorAgent] 图片服务策略创建成功")
            except Exception as e:
                logger.error(f"[ImageGeneratorAgent] 创建图片服务策略失败: {e}", exc_info=True)
                raise
        self.strategy = strategy

        # 使用提供的 COS 上传器或创建新实例
        if cos_uploader is None:
            try:
                from app.utils.cos_uploader import create_cos_uploader
                cos_uploader = create_cos_uploader(use_mock)
                logger.info(f"[ImageGeneratorAgent] COS 上传器创建成功, available={cos_uploader.is_available()}")
            except Exception as e:
                logger.error(f"[ImageGeneratorAgent] 创建 COS 上传器失败: {e}", exc_info=True)
                raise
        self.cos_uploader = cos_uploader

        self.use_mock = use_mock

        # 不需要 LLM，图片生成不调用 LLM
        super().__init__(llm_service=None, use_mock=True)
        logger.info(f"[ImageGeneratorAgent] 初始化完成")

    @property
    def name(self) -> str:
        return "ImageGeneratorAgent"

    @property
    def description(self) -> str:
        return "并行执行图片任务，上传 COS，合并图文"

    async def execute(
        self,
        input_data: ImageGeneratorInput,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> ImageGeneratorOutput:
        """
        执行图片生成任务

        Args:
            input_data: 图片生成输入数据
            stream_callback: 流式回调函数（暂不使用，使用 SSE）

        Returns:
            ImageGeneratorOutput: 生成结果
        """
        logger.info(
            f"[ImageGeneratorAgent] 开始执行，共 {len(input_data.tasks)} 个图片任务"
        )

        task_id = input_data.taskId
        tasks = input_data.tasks

        # 检查策略是否可用
        if self.strategy is None:
            logger.error("[ImageGeneratorAgent] 图片服务策略未初始化")
            raise ValueError("图片服务策略未初始化")

        # 检查 COS 上传器是否可用
        if self.cos_uploader is None:
            logger.error("[ImageGeneratorAgent] COS 上传器未初始化")
            raise ValueError("COS 上传器未初始化")

        available_providers = self.strategy.get_available_providers()
        logger.info(f"[ImageGeneratorAgent] 可用的图片服务: {available_providers}")
        logger.info(f"[ImageGeneratorAgent] COS 上传器可用: {self.cos_uploader.is_available()}")

        # 1. 发送任务开始事件
        logger.info(f"[ImageGeneratorAgent] 发送任务开始事件...")
        await self._send_task_start_event(task_id, tasks)

        # 2. 并行执行所有图片任务
        results = await self._execute_all_tasks_parallel(task_id, tasks)

        # 3. 图文合并（在发送完成事件前先完成合并）
        merged_content = self._merge_images_into_content(
            input_data.content, results
        )

        # 3.5 将 Markdown 转换为 HTML 富文本
        merged_html = self._convert_markdown_to_html(merged_content)

        # 4. 发送全部完成事件（携带合并后的内容和HTML）
        await self._send_all_complete_event(task_id, results, merged_content, merged_html)

        # 5. 统计结果
        success_count = sum(1 for r in results if r.status == ImageTaskStatus.COMPLETED)
        failed_count = sum(1 for r in results if r.status == ImageTaskStatus.FAILED)
        skipped_count = sum(1 for r in results if r.status == ImageTaskStatus.SKIPPED)

        output = ImageGeneratorOutput(
            results=results,
            mergedContent=merged_content,
            mergedHtml=merged_html,
            totalCount=len(results),
            successCount=success_count,
            failedCount=failed_count,
            skippedCount=skipped_count,
        )

        logger.info(
            f"[ImageGeneratorAgent] 执行完成: "
            f"total={len(results)}, success={success_count}, "
            f"failed={failed_count}, skipped={skipped_count}"
        )

        return output

    # ============ SSE 推送 ============

    async def _send_task_start_event(self, task_id: str, tasks: List[ImageTask]):
        """
        发送图片任务开始事件

        Args:
            task_id: 文章生成任务 ID
            tasks: 图片任务列表
        """
        await sse_manager.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_TASK_START,
            stage=SSEStage.IMAGE,
            data={
                "task_id": task_id,
                "total_image_tasks": len(tasks),
                "placeholders": [t.placeholderId for t in tasks],
            },
            progress=60,  # 图片阶段起始进度
            message=f"开始生成 {len(tasks)} 张图片",
        )

    async def _send_single_progress_event(
        self,
        task_id: str,
        image_task: ImageTask,
        status: str,
        provider: Optional[str] = None,
        url: Optional[str] = None,
        progress: int = 0,
    ):
        """
        发送单张图片进度事件

        Args:
            task_id: 文章生成任务 ID
            image_task: 图片任务
            status: 状态 (generating/completed/failed)
            provider: 服务提供商
            url: 图片 URL（如果已完成）
            progress: 进度百分比
        """
        data = {
            "position": image_task.placeholderId,
            "status": status,
            "provider": provider,
        }

        if url:
            data["url"] = url

        await sse_manager.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_PROGRESS,
            stage=SSEStage.IMAGE,
            data=data,
            progress=progress,
            message=f"图片 {image_task.placeholderId} {status}",
        )

    async def _send_single_complete_event(
        self,
        task_id: str,
        result: ImageResult,
        progress: int = 0,
    ):
        """
        发送单张图片完成事件

        Args:
            task_id: 文章生成任务 ID
            result: 图片结果
            progress: 进度百分比
        """
        await sse_manager.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_COMPLETE,
            stage=SSEStage.IMAGE,
            data={
                "position": result.placeholderId,
                "url": result.url,
                "source": result.sourceProvider.value,
                "status": result.status.value,
            },
            progress=progress,
            message=f"图片 {result.placeholderId} 已完成",
        )

    async def _send_all_complete_event(self, task_id: str, results: List[ImageResult], merged_content: str = "", merged_html: str = ""):
        """
        发送所有图片完成事件

        Args:
            task_id: 文章生成任务 ID
            results: 图片结果列表
            merged_content: 图文合并后的 Markdown 正文
            merged_html: 图文合并后的 HTML 富文本
        """
        success_count = sum(1 for r in results if r.status == ImageTaskStatus.COMPLETED)
        failed_count = sum(1 for r in results if r.status == ImageTaskStatus.FAILED)

        await sse_manager.send_event(
            task_id=task_id,
            event_type=SSEEventType.IMAGE_ALL_COMPLETE,
            stage=SSEStage.IMAGE,
            data={
                "task_id": task_id,
                "total_count": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": [
                    {
                        "placeholderId": r.placeholderId,
                        "url": r.url,
                        "source": r.sourceProvider.value,
                        "status": r.status.value,
                    }
                    for r in results
                ],
                "merged_content": merged_content,
                "merged_html": merged_html,
            },
            progress=80,  # 图片阶段完成进度
            message=f"图片生成完成: {success_count} 成功, {failed_count} 失败",
        )

    # ============ 并行执行 ============

    async def _execute_all_tasks_parallel(
        self,
        task_id: str,
        tasks: List[ImageTask],
    ) -> List[ImageResult]:
        """
        并行执行所有图片任务

        使用 asyncio.gather(return_exceptions=True) 确保单图失败不阻塞整体

        Args:
            task_id: 文章生成任务 ID
            tasks: 图片任务列表

        Returns:
            图片结果列表
        """
        # 按位置排序，确保顺序正确
        sorted_tasks = sorted(tasks, key=lambda t: t.position)

        # 并行执行，捕获异常
        results = await asyncio.gather(
            *[self._execute_single_task(task_id, t) for t in sorted_tasks],
            return_exceptions=True  # 关键：异常不中断其他任务
        )

        # 处理结果，将异常转为 ImageResult
        final_results = []
        for i, result in enumerate(results):
            task = sorted_tasks[i]

            if isinstance(result, Exception):
                # 异常情况：强制返回失败结果
                logger.error(
                    f"[ImageGeneratorAgent] 任务 {task.placeholderId} "
                    f"发生异常: {result}"
                )
                final_results.append(
                    ImageResult(
                        taskId=task.taskId,
                        placeholderId=task.placeholderId,
                        url="",  # 空 URL
                        cosKey="",
                        sourceProvider=ImageProvider.PICSUM,  # 标记为兜底
                        status=ImageTaskStatus.FAILED,
                        errorMessage=str(result),
                    )
                )
            elif isinstance(result, ImageResult):
                # 正常结果
                final_results.append(result)
            else:
                # 未知类型
                logger.warning(
                    f"[ImageGeneratorAgent] 任务 {task.placeholderId} "
                    f"返回未知类型: {type(result)}"
                )
                final_results.append(
                    ImageResult(
                        taskId=task.taskId,
                        placeholderId=task.placeholderId,
                        url="",
                        cosKey="",
                        sourceProvider=ImageProvider.PICSUM,
                        status=ImageTaskStatus.FAILED,
                        errorMessage="未知返回类型",
                    )
                )

        return final_results

    async def _execute_single_task(
        self,
        task_id: str,
        image_task: ImageTask,
    ) -> ImageResult:
        """
        执行单个图片任务

        流程：
        1. 发送开始事件
        2. 尝试从 preferredProviders（仅 Seedream）获取图片
        3. 上传 COS
        4. 发送完成事件
        5. 返回结果（失败则返回空 URL）

        Args:
            task_id: 文章生成任务 ID
            image_task: 图片任务

        Returns:
            图片结果
        """
        logger.info(
            f"[ImageGeneratorAgent] 开始处理任务: {image_task.placeholderId}, "
            f"keywords={image_task.keywords}, type={image_task.imageType.value}"
        )
        logger.info(
            f"[ImageGeneratorAgent] 首选服务: {image_task.preferredProviders}"
        )

        # 发送开始事件
        await self._send_single_progress_event(
            task_id=task_id,
            image_task=image_task,
            status="generating",
            provider=None,
            progress=0,
        )

        # 记录失败的服务
        failed_providers: List[ImageProvider] = []
        last_error: Optional[str] = None

        # 尝试所有首选服务（仅 Seedream）
        for provider_name in image_task.preferredProviders:
            logger.info(f"[ImageGeneratorAgent] 尝试首选服务: {provider_name.value}")
            provider = self.strategy.get_provider(provider_name)

            if not provider:
                logger.warning(f"[ImageGeneratorAgent] 服务 {provider_name.value} 未注册")
                continue

            # 检查服务可用性
            if not provider.is_available():
                logger.warning(
                    f"[ImageGeneratorAgent] 服务 {provider_name.value} 不可用"
                )
                failed_providers.append(provider_name)
                continue

            # 检查类型支持
            if not provider.supports_image_type(image_task.imageType):
                logger.warning(
                    f"[ImageGeneratorAgent] 服务 {provider_name.value} "
                    f"不支持类型 {image_task.imageType.value}"
                )
                failed_providers.append(provider_name)
                continue

            # 发送进度事件
            await self._send_single_progress_event(
                task_id=task_id,
                image_task=image_task,
                status="generating",
                provider=provider_name.value,
                progress=10,
            )

            try:
                logger.info(f"[ImageGeneratorAgent] 调用 {provider_name.value} 获取图片...")
                # 获取图片（传递上下文内容用于语义增强）
                fetch_result = await provider.fetch_image(
                    keywords=image_task.keywords,
                    image_type=image_task.imageType,
                    width=1920,
                    height=1920,
                    context=image_task.context,
                )

                logger.info(
                    f"[ImageGeneratorAgent] {provider_name.value} 返回: "
                    f"success={fetch_result.success}, url={fetch_result.url[:50] if fetch_result.url else 'None'}..."
                )

                if fetch_result.success:
                    logger.info(f"[ImageGeneratorAgent] 上传图片到 COS...")
                    # 上传 COS
                    cos_result = await self.cos_uploader.upload_from_url(
                        image_url=fetch_result.url,
                        placeholder_id=image_task.placeholderId,
                        task_id=image_task.taskId,
                        source_provider=fetch_result.provider,
                    )

                    logger.info(
                        f"[ImageGeneratorAgent] COS 上传结果: status={cos_result.status.value}, "
                        f"url={cos_result.url[:50] if cos_result.url else 'None'}..."
                    )

                    if cos_result.status == ImageTaskStatus.COMPLETED:
                        # 发送完成事件
                        await self._send_single_complete_event(
                            task_id=task_id,
                            result=cos_result,
                            progress=100,
                        )

                        logger.info(f"[ImageGeneratorAgent] 任务 {image_task.placeholderId} 完成")
                        return cos_result

                    # 上传失败，继续尝试下一个
                    last_error = cos_result.errorMessage
                    failed_providers.append(provider_name)
                    logger.warning(f"[ImageGeneratorAgent] COS 上传失败: {last_error}")

            except Exception as e:
                last_error = str(e)
                failed_providers.append(provider_name)
                logger.warning(
                    f"[ImageGeneratorAgent] 服务 {provider_name.value} "
                    f"获取失败: {e}", exc_info=True
                )

        # 最终失败：返回空结果（无兜底）
        logger.error(
            f"[ImageGeneratorAgent] 任务 {image_task.placeholderId} "
            f"失败，Seedream 服务不可用或失败: {last_error}"
        )

        result = ImageResult(
            taskId=image_task.taskId,
            placeholderId=image_task.placeholderId,
            url="",  # 空 URL，合并时会删除占位符
            cosKey="",
            sourceProvider=ImageProvider.SEEDREAM,
            status=ImageTaskStatus.FAILED,
            errorMessage=last_error or "Seedream 服务失败",
        )

        await self._send_single_complete_event(
            task_id=task_id,
            result=result,
            progress=100,
        )

        return result

    # ============ 图文合并 ============

    def _merge_images_into_content(
        self,
        content: str,
        results: List[ImageResult],
    ) -> str:
        """
        将图片 URL 替换回正文中的 IMAGE_PLACEHOLDER

        核心逻辑：
        1. 按 position 排序 results（保证顺序）
        2. 使用 placeholderId 匹配正文中的占位符
        3. 成功的图片：替换为真实 URL
        4. 失败的图片：删除占位符（url 为空）

        Args:
            content: 原始正文内容
            results: 图片结果列表

        Returns:
            合并后的正文内容
        """
        logger.info(
            f"[ImageGeneratorAgent] 开始图文合并，共 {len(results)} 个结果"
        )

        # 按位置排序（保证顺序）
        sorted_results = sorted(results, key=lambda r: results.index(r))

        merged_content = content

        for result in sorted_results:
            # 标准匹配：![IMAGE_PLACEHOLDER](image_N|关键词)
            pattern = rf'!\[IMAGE_PLACEHOLDER\]\({re.escape(result.placeholderId)}\|[^)]*\)'

            if result.url:
                # 有 URL：替换为真实图片
                replacement = f'![配图]({result.url})'
                new_content = re.sub(pattern, replacement, merged_content)
                if new_content == merged_content:
                    # 标准匹配失败，尝试更宽松的匹配
                    loose_pattern = rf'!\[IMAGE_PLACEHOLDER\]\([^)]*{re.escape(result.placeholderId)}[^)]*\)'
                    new_content = re.sub(loose_pattern, replacement, merged_content)
                    if new_content != merged_content:
                        logger.info(
                            f"[ImageGeneratorAgent] 通过宽松匹配替换占位符: "
                            f"{result.placeholderId} -> {result.url[:50]}..."
                        )
                if new_content != merged_content:
                    merged_content = new_content
                    logger.info(
                        f"[ImageGeneratorAgent] 替换占位符: "
                        f"{result.placeholderId} -> {result.url[:50]}..."
                    )
                else:
                    logger.warning(
                        f"[ImageGeneratorAgent] 占位符未匹配到: {result.placeholderId}"
                    )
            else:
                # 无 URL（失败）：删除占位符
                replacement = ''
                new_content = re.sub(pattern, replacement, merged_content)
                if new_content == merged_content:
                    # 标准匹配失败，尝试更宽松的匹配
                    loose_pattern = rf'!\[IMAGE_PLACEHOLDER\]\([^)]*{re.escape(result.placeholderId)}[^)]*\)'
                    new_content = re.sub(loose_pattern, replacement, merged_content)
                if new_content != merged_content:
                    merged_content = new_content
                    logger.warning(
                        f"[ImageGeneratorAgent] 删除失败占位符: "
                        f"{result.placeholderId}"
                    )
                else:
                    logger.warning(
                        f"[ImageGeneratorAgent] 失败占位符未匹配到: {result.placeholderId}"
                    )

        # 清理多余空行（连续3个以上换行合并为2个）
        merged_content = re.sub(r'\n{3,}', '\n\n', merged_content)

        return merged_content

    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        将 Markdown 内容转换为 HTML 富文本

        Args:
            markdown_content: Markdown 格式内容（图片占位符已替换）

        Returns:
            HTML 富文本内容
        """
        import markdown

        extensions = [
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'nl2br',
        ]

        extension_configs = {
            'codehilite': {
                'css_class': 'highlight',
                'linenums': False,
            },
        }

        html_content = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs=extension_configs,
        )

        return html_content


# ============ 工厂函数 ============


def create_image_generator_agent(
    strategy: Optional[ImageServiceStrategy] = None,
    cos_uploader: Optional[object] = None,
    use_mock: bool = False,
) -> ImageGeneratorAgent:
    """
    创建 ImageGeneratorAgent 实例

    Args:
        strategy: 图片服务策略
        cos_uploader: COS 上传服务
        use_mock: 是否使用 Mock 实现

    Returns:
        ImageGeneratorAgent 实例
    """
    return ImageGeneratorAgent(
        strategy=strategy,
        cos_uploader=cos_uploader,
        use_mock=use_mock,
    )