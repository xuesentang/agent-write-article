一、ImageAnalyzerAgent 职责边界

  1.1 核心职责

  解析 ContentAgent 输出的正文内容，生成结构化的图片任务列表。

  1.2 IMAGE_PLACEHOLDER 解析逻辑

  根据 ContentAgent 已实现的占位符格式：
  ![IMAGE_PLACEHOLDER](image_1|自媒体、内容创作、数字化时代)

  解析流程：
  1. 使用正则 r'!\[IMAGE_PLACEHOLDER\]\(image_(\d+)\|([^)]+)\)' 提取所有占位符
  2. 提取 position（如 image_1）、keywords（中文逗号分隔）
  3. 根据关键词推断 imageType（photo/diagram/icon）
  4. 根据位置计算 positionIndex（用于后续排序）

  1.3 图片任务数据结构

  class ImageTask(BaseModel):
      """单个图片任务"""

      taskId: str = Field(..., description="任务唯一ID，UUID")
      placeholderId: str = Field(..., description="占位符ID，如 image_1")
      position: str = Field(..., description="在正文中的位置标识")
      positionIndex: int = Field(..., description="排序索引，从1开始")
      keywords: List[str] = Field(..., description="配图关键词")
      description: str = Field(default="", description="配图描述")
      imageType: str = Field(default="photo", description="图片类型: photo/diagram/icon/decorative")
      preferredProviders: List[str] = Field(default=["pexels"], description="首选服务列表")
      fallbackProviders: List[str] = Field(default=["picsum"], description="兜底服务列表")
      retryCount: int = Field(default=0, description="已重试次数")
      maxRetries: int = Field(default=2, description="最大重试次数")
      status: str = Field(default="pending", description="状态: pending/processing/completed/failed")

  1.4 输入输出

  class ImageAnalyzerInput(AgentInput):
      """ImageAnalyzer 输入"""
      content: str  # 正文内容
      image_placeholders: List[ImagePlaceholder]  # ContentAgent 提取的占位符列表

  class ImageAnalyzerOutput(AgentOutput):
      """ImageAnalyzer 输出"""
      tasks: List[ImageTask]  # 图片任务列表
      totalTasks: int  # 任务总数
      contentHash: str  # 正文内容hash（用于校验）

  ---
  二、ImageServiceStrategy 设计

  2.1 总管职责

  根据任务类型、关键词、可用性、失败重试状态选择具体图片服务。

  2.2 服务提供商优先级和适用场景

  ┌─────────────────┬───────────────┬───────────────────────┬──────────────────────────┐
  │      服务       │   适用场景    │        优先级         │           限制           │
  ├─────────────────┼───────────────┼───────────────────────┼──────────────────────────┤
  │ PexelsService   │ 正文主图      │ 最高（首选）          │ 仅用于 photo 类型        │
  ├─────────────────┼───────────────┼───────────────────────┼──────────────────────────┤
  │ SeedreamService │ 定制化主题图  │ 中等（photo/diagram） │ 需要 API Key，可能较慢   │
  ├─────────────────┼───────────────┼───────────────────────┼──────────────────────────┤
  │ IconifyService  │ 仅图标/装饰类 │ 仅限 decorative/icon  │ 禁止用于正文主图         │
  ├─────────────────┼───────────────┼───────────────────────┼──────────────────────────┤
  │ PicsumService   │ 兜底随机图    │ 最低（兜底）          │ 无需 API，但图片质量随机 │
  └─────────────────┴───────────────┴───────────────────────┴──────────────────────────┘

  2.3 选择策略逻辑

  class ImageServiceStrategy:
      """图片服务策略"""

      def select_provider(self, task: ImageTask) -> str:
          """
          根据任务选择提供商

          规则：
          1. imageType == "photo" → 优先 Pexels → 失败降级 Seedream → 最终 Picsum
          2. imageType == "diagram" → 优先 Seedream → 失败 Picsum
          3. imageType == "icon" → 仅 Iconify（若失败，转为 decorative 用 Picsum）
          4. imageType == "decorative" → Iconify → Picsum

          失败重试时：
          - 从 preferredProviders 列表中移除已失败的 provider
          - 降级到 fallbackProviders
          """
          pass

  2.4 失败降级流程

  任务开始 → 选择 preferredProviders[0] → 调用服务
      ↓
  成功 → 返回结果
      ↓
  失败 → retryCount += 1
      ↓
  retryCount < maxRetries → 选择 preferredProviders[retryCount]
      ↓
  retryCount >= maxRetries → 降级到 fallbackProviders
      ↓
  所有 fallback 都失败 → 返回 Picsum（强制兜底，永不失败）

  ---
  三、ImageGeneratorAgent 职责边界

  3.1 核心职责

  执行单个图片任务，调用 ImageServiceStrategy 获取图片，上传 COS，返回结果。

  3.2 执行流程

  ImageGeneratorAgent.execute(task):
      1. 选择 provider = strategy.select_provider(task)
      2. 调用 provider_service.search_image(keywords) 获取图片 URL
      3. 下载图片到临时目录
      4. 上传到腾讯云 COS
      5. 删除临时文件
      6. 返回 ImageResult

  3.3 COS 上传设计

  class COSUploader:
      """腾讯云 COS 上传服务"""

      def __init__(self):
          # 从 settings 读取配置
          self.secret_id = settings.COS_SECRET_ID
          self.secret_key = settings.COS_SECRET_KEY
          self.bucket = settings.COS_BUCKET
          self.region = settings.COS_REGION
          self.upload_path = settings.COS_UPLOAD_PATH

      async def upload(self, local_path: str, cos_key: str) -> str:
          """
          上传图片到 COS

          Returns:
              COS 访问 URL
          """
          pass

  ⚠️ 中断点 1：COS 配置确认
  当前 .env.example 中 COS 配置为占位符，实际开发时需要确认：
  - 你是否有腾讯云 COS 账号？
  - 是否已创建 Bucket？
  - COS_SECRET_ID / SECRET_KEY 是否已获取？

  请确认后再继续。

  3.4 统一返回结果

  class ImageResult(BaseModel):
      """单个图片生成结果"""

      taskId: str  # 任务ID
      placeholderId: str  # 占位符ID，用于替换
      url: str  # 最终 COS URL
      cosKey: str  # COS 存储路径
      width: int  # 图片宽度
      height: int  # 图片高度
      sourceProvider: str  # 实际使用的服务（pexels/seedream/iconify/picsum）
      status: str  # success/failed
      errorMessage: Optional[str] = None

  ---
  四、并行处理和错误处理策略

  4.1 并行执行方案

  使用 asyncio.gather() 并行执行多个图片任务：

  async def execute_all(tasks: List[ImageTask]) -> List[ImageResult]:
      """
      并行执行所有图片任务

      使用 asyncio.gather(return_exceptions=True) 确保单图失败不阻塞整体
      """
      results = await asyncio.gather(
          *[self._execute_single_task(task) for task in tasks],
          return_exceptions=True  # 关键：异常不会中断其他任务
      )

      # 处理结果，将异常转为 ImageResult(status=failed)
      return self._process_results(results, tasks)

  4.2 单图失败处理

  硬性规则：单图失败绝不阻塞整体流程。

  async def _execute_single_task(self, task: ImageTask) -> ImageResult:
      """执行单个任务（带重试和兜底）"""

      try:
          # 尝试 preferred providers
          for provider in task.preferredProviders:
              result = await self._try_provider(task, provider)
              if result:
                  return result

          # 降级到 fallback providers
          for provider in task.fallbackProviders:
              result = await self._try_provider(task, provider)
              if result:
                  return result

          # 强制兜底：Picsum（永不失败）
          return await self._picsum_fallback(task)

      except Exception as e:
          # 最终兜底：返回占位图 URL（或跳过此图片）
          return ImageResult(
              taskId=task.taskId,
              placeholderId=task.placeholderId,
              url="",  # 空URL表示无图
              status="failed",
              errorMessage=str(e)
          )

  4.3 SSE 进度推送事件设计

  现有 SSE 已定义的事件：
  - ImageProgressEventData: position, status, provider
  - ImageCompleteEventData: position, url, source

  建议新增事件：
  class ImageTaskStartEventData(BaseModel):
      """图片任务开始"""
      taskId: str
      placeholderId: str
      totalTasks: int
      currentTaskIndex: int

  class ImageAllCompleteEventData(BaseModel):
      """所有图片任务完成"""
      totalTasks: int
      successCount: int
      failedCount: int
      results: List[ImageResult]

  4.4 SSE 推送时机

  任务开始 → send_image_task_start
      ↓
  单个任务开始 → send_image_progress(status="generating", provider="pexels")
      ↓
  单个任务完成 → send_image_complete(url=..., source=...)
      ↓
  所有任务完成 → send_image_all_complete

  ---
  五、图文合并方案

  5.1 替换策略

  核心：保证顺序正确，使用 placeholderId 作为唯一标识。

  def merge_images_into_content(
      content: str,
      results: List[ImageResult]
  ) -> str:
      """
      将图片URL替换回正文中的 IMAGE_PLACEHOLDER

      流程：
      1. 按 positionIndex 排序 results
      2. 遍历 results，用 placeholderId 匹配正文中的占位符
      3. 替换格式：
         ![IMAGE_PLACEHOLDER](image_1|关键词) → ![配图描述](图片URL)
      4. 如果 url 为空（失败），删除该占位符
      """

      # 按 positionIndex 排序
      sorted_results = sorted(results, key=lambda r: r.positionIndex)

      for result in sorted_results:
          # 匹配占位符
          pattern = f'![IMAGE_PLACEHOLDER]({result.placeholderId}|[^)]+)'

          if result.url:
              # 替换为真实图片
              replacement = f'![配图-{result.sourceProvider}]({result.url})'
          else:
              # 失败则删除占位符
              replacement = ''

          content = re.sub(pattern, replacement, content)

      return content

  5.2 顺序保证机制

  双重校验：
  1. positionIndex 用于排序（从 ContentAgent 解析时确定）
  2. placeholderId 用于匹配（唯一标识，如 image_1）

  风险点：如果正文中出现相同 placeholderId 的重复占位符，可能导致错误替换。

  建议：ContentAgent 生成占位符时，使用 UUID 或严格递增序号。

  ---
  六、需要澄清和确认的问题

  ⚠️ 中断点汇总

  ┌─────┬──────────────┬────────────────────────────────────────────────────────┐
  │  #  │     问题     │                       需确认内容                       │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 1   │ COS 配置     │ 是否有腾讯云 COS 账号、Bucket、API Key？               │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 2   │ Pexels API   │ 是否已获取 Pexels API Key？                            │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 3   │ Seedream API │ Seedream 是什么服务？是否需要付费？API Key 获取方式？  │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 4   │ Picsum 兜底  │ Picsum 图片质量随机，是否接受作为最终兜底？            │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 5   │ Iconify 限制 │ 是否确认 Iconify 仅用于图标/装饰，不用于正文主图？     │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 6   │ 图片尺寸     │ 正文配图的推荐尺寸（如 1200x800）？是否需要统一尺寸？  │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 7   │ 失败处理     │ 图片全部失败时，是保留占位符还是删除？                 │
  ├─────┼──────────────┼────────────────────────────────────────────────────────┤
  │ 8   │ SSE 事件新增 │ 是否同意新增 ImageTaskStart 和 ImageAllComplete 事件？ │
  └─────┴──────────────┴────────────────────────────────────────────────────────┘

  ---
  七、模块分层架构图

  ┌─────────────────────────────────────────────────────────┐
  │                    Agent 层                              │
  │  ┌──────────────────┐    ┌──────────────────────────┐  │
  │  │ ImageAnalyzerAgent│    │ ImageGeneratorAgent      │  │
  │  │ - 解析占位符      │    │ - 执行图片任务           │  │
  │  │ - 生成任务列表    │    │ - 调用 Strategy          │  │
  │  └──────────────────┘    │ - 上传 COS               │  │
  │                          │ - 返回结果                │  │
  │                          └──────────────────────────┘  │
  └─────────────────────────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │                   Strategy 层                            │
  │  ┌──────────────────────────────────────────────────┐  │
  │  │           ImageServiceStrategy                    │  │
  │  │  - 选择 Provider                                   │  │
  │  │  - 失败降级逻辑                                     │  │
  │  └──────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │                   Service 层                             │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
  │  │Pexels    │ │Seedream  │ │Iconify   │ │Picsum    │   │
  │  │Service   │ │Service   │ │Service   │ │Service   │   │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
  │  ┌──────────────────────────────────────────────────┐  │
  │  │               COSUploader                          │  │
  │  └──────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │                   Schema 层                              │
  │  ImageTask, ImageResult, ImageAnalyzerInput/Output      │
  └─────────────────────────────────────────────────────────┘

  ---
  设计方案输出完成。请逐一确认上述 8 个中断点，确认后我再继续下一步开发。