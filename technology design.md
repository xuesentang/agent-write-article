自媒体爆款文章生成器 - 技术方案文档

  1. 技术栈选型

  1.1 前端技术栈

  ┌─────────────────┬────────────────────────────┬──────────────────────────────────────────┐
  │      技术       │            选型            │                   理由                   │
  ├─────────────────┼────────────────────────────┼──────────────────────────────────────────┤
  │ 框架            │ Vue 3 + Vite               │ 轻量高效，SSE 原生支持好，学习曲线平缓   │
  ├─────────────────┼────────────────────────────┼──────────────────────────────────────────┤
  │ UI 组件库       │ Element Plus               │ 成熟稳定，提供进度条、消息提示等常用组件 │
  ├─────────────────┼────────────────────────────┼──────────────────────────────────────────┤
  │ 状态管理        │ Pinia                      │ Vue 3 官方推荐，简洁直观                 │
  ├─────────────────┼────────────────────────────┼──────────────────────────────────────────┤
  │ Markdown 渲染   │ markdown-it + highlight.js │ 正文预览需要渲染 Markdown 内容           │
  ├─────────────────┼────────────────────────────┼──────────────────────────────────────────┤
  │ HTTP/SSE 客户端 │ 原生 EventSource + Axios   │ SSE 用原生 API，HTTP 请求用 Axios        │
  └─────────────────┴────────────────────────────┴──────────────────────────────────────────┘

  1.2 后端技术栈

  ┌──────────┬───────────────────┬──────────────────────────────────────────────────────┐
  │   技术   │       选型        │                         理由                         │
  ├──────────┼───────────────────┼──────────────────────────────────────────────────────┤
  │ 框架     │ FastAPI           │ Python 原生异步支持，SSE 实现简单，自动生成 API 文档 │
  ├──────────┼───────────────────┼──────────────────────────────────────────────────────┤
  │ LLM SDK  │ openai (兼容模式) │ DeepSeek/智谱/千问均兼容 OpenAI API 格式，统一调用层 │
  ├──────────┼───────────────────┼──────────────────────────────────────────────────────┤
  │ 任务队列 │ Celery + Redis    │ 异步任务处理，图片生成等耗时操作解耦                 │
  ├──────────┼───────────────────┼──────────────────────────────────────────────────────┤
  │ ORM      │ SQLAlchemy 2.0    │ 异步支持完善，与 FastAPI 配合良好                    │
  ├──────────┼───────────────────┼──────────────────────────────────────────────────────┤
  │ 图片处理 │ Pillow            │ 图片格式转换、压缩等处理                             │
  └──────────┴───────────────────┴──────────────────────────────────────────────────────┘

  1.3 数据存储

  ┌────────────┬────────────┬─────────────────────────────────────────────────┐
  │    存储    │    选型    │                      理由                       │
  ├────────────┼────────────┼─────────────────────────────────────────────────┤
  │ 关系数据库 │ SQLite     │ 用户已指定；个人/小团队场景，零配置，足够支撑   │
  ├────────────┼────────────┼─────────────────────────────────────────────────┤
  │ 缓存/队列  │ Redis      │ 任务状态缓存、Celery 消息队列、SSE 连接状态管理 │
  ├────────────┼────────────┼─────────────────────────────────────────────────┤
  │ 对象存储   │ 腾讯云 COS │ 用户已指定；存储生成的图片，CDN 加速访问        │
  └────────────┴────────────┴─────────────────────────────────────────────────┘

  1.4 AI 服务接入

  ┌──────────────┬────────────────────────────────┬─────────────────┐
  │     服务     │              用途              │    接入方式     │
  ├──────────────┼────────────────────────────────┼─────────────────┤
  │ DeepSeek     │ 主要 LLM（标题/大纲/正文生成） │ OpenAI 兼容 API │
  ├──────────────┼────────────────────────────────┼─────────────────┤
  │ 智谱 GLM     │ 备用 LLM                       │ OpenAI 兼容 API │
  ├──────────────┼────────────────────────────────┼─────────────────┤
  │ 千问         │ 备用 LLM                       │ OpenAI 兼容 API │
  ├──────────────┼────────────────────────────────┼─────────────────┤
  │ Seedream 5.0 │ AI 文生图                      │ 独立 API        │
  └──────────────┴────────────────────────────────┴─────────────────┘

  ---
  2. 项目目录结构设计

  article-generator/
  ├── frontend/                          # 前端项目
  │   ├── src/
  │   │   ├── api/                       # API 调用层
  │   │   │   ├── sse.js                 # SSE 连接管理
  │   │   │   └── http.js                # HTTP 请求封装
  │   │   ├── components/
  │   │   │   ├── TitleSelector.vue      # 标题选择组件
  │   │   │   ├── OutlineEditor.vue      # 大纲编辑组件
  │   │   │   ├── ContentViewer.vue      # 正文预览组件（流式渲染）
  │   │   │   └── ProgressIndicator.vue  # 进度指示组件
  │   │   ├── stores/                    # Pinia 状态管理
  │   │   │   ├── task.js                # 任务状态
  │   │   │   └── article.js             # 文章内容
  │   │   ├── views/
  │   │   │   ├── Home.vue               # 首页（选题输入）
  │   │   │   ├── Create.vue             # 创作流程页
  │   │   │   └── Result.vue             # 结果展示页
  │   │   └── utils/
  │   │       └── markdown.js            # Markdown 解析工具
  │   ├── package.json
  │   └── vite.config.js
  │
  ├── backend/                           # 后端项目
  │   ├── app/
  │   │   ├── main.py                    # FastAPI 入口
  │   │   ├── config.py                  # 配置管理
  │   │   ├── api/
  │   │   │   ├── __init__.py
  │   │   │   ├── routes/
  │   │   │   │   ├── task.py            # 任务管理接口
  │   │   │   │   ├── sse.py             # SSE 流式接口
  │   │   │   │   └── article.py         # 文章 CRUD 接口
  │   │   │   └── dependencies.py        # 依赖注入
  │   │   ├── services/
  │   │   │   ├── user_service.py        # 用户服务
  │   │   │   ├── article_service.py     # 文章服务
  │   │   │   ├── stats_service.py       # 统计服务
  │   │   │   └── llm_service.py         # LLM 调用封装
  │   │   ├── agents/                    # 五大智能体
  │   │   │   ├── __init__.py
  │   │   │   ├── base_agent.py          # 智能体基类
  │   │   │   ├── title_agent.py         # 智能体1：标题生成
  │   │   │   ├── outline_agent.py       # 智能体2：大纲生成
  │   │   │   ├── content_agent.py       # 智能体3：正文生成
  │   │   │   ├── image_analyzer_agent.py # 智能体4：配图分析
  │   │   │   └── image_generator_agent.py # 智能体5：配图生成
  │   │   ├── image/                     # 配图服务层
  │   │   │   ├── __init__.py
  │   │   │   ├── strategy.py            # ImageServiceStrategy 总管
  │   │   │   ├── base_provider.py       # 配图服务基类
  │   │   │   └── providers/
  │   │   │       ├── pexels.py          # Pexels 图库
  │   │   │       ├── mermaid.py          # Mermaid 图表
  │   │   │       ├── iconify.py          # Iconify 图标
  │   │   │       ├── svg_diagram.py      # SVG 矢量图
  │   │   │       ├── seedream.py         # Seedream AI 绘图
  │   │   │       └── picsum.py           # Picsum 兜底
  │   │   ├── models/                    # 数据模型
  │   │   │   ├── __init__.py
  │   │   │   ├── user.py
  │   │   │   ├── task.py
  │   │   │   └── article.py
  │   │   ├── schemas/                   # Pydantic 模型
  │   │   │   ├── __init__.py
  │   │   │   ├── task.py
  │   │   │   ├── article.py
  │   │   │   └── sse.py                 # SSE 数据结构
  │   │   └── utils/
  │   │       ├── cos_client.py          # 腾讯云 COS 客户端
  │   │       └── redis_client.py        # Redis 客户端
  │   ├── alembic/                       # 数据库迁移
  │   ├── tests/
  │   ├── requirements.txt
  │   └── .env.example
  │
  └── docker-compose.yml                 # 本地开发环境编排

  ---
  3. 核心数据模型设计

  3.1 任务状态模型

  ┌─────────────────────────────────────────────────────────────────┐
  │                          Task 任务表                             │
  ├─────────────────────────────────────────────────────────────────┤
  │ id: UUID (PK)                                                    │
  │ user_id: UUID (FK)                                               │
  │ topic: String                     # 用户输入的选题              │
  │ style: String                     # 文章风格                    │
  │ extra_description: Text           # 用户补充描述                │
  │ status: Enum                      # 任务状态                    │
  │   - CREATED                       # 已创建，等待开始             │
  │   - TITLE_GENERATING              # 标题生成中                   │
  │   - TITLE_READY                   # 标题方案就绪                 │
  │   - OUTLINE_GENERATING            # 大纲生成中                   │
  │   - OUTLINE_READY                 # 大纲就绪，待确认             │
  │   - CONTENT_GENERATING            # 正文生成中                   │
  │   - IMAGE_GENERATING              # 配图生成中                   │
  │   - COMPLETED                     # 已完成                       │
  │   - FAILED                        # 失败                         │
  │ created_at: DateTime                                             │
  │ updated_at: DateTime                                             │
  └─────────────────────────────────────────────────────────────────┘

  3.2 文章内容模型

  ┌─────────────────────────────────────────────────────────────────┐
  │                        Article 文章表                           │
  ├─────────────────────────────────────────────────────────────────┤
  │ id: UUID (PK)                                                    │
  │ task_id: UUID (FK)                                               │
  │ selected_title: String            # 用户选择的标题              │
  │ title_options: JSON               # 标题方案列表                │
  │ outline: JSON                     # 文章大纲（结构化）          │
  │ content: Text                     # Markdown 正文               │
  │ images: JSON                       # 配图信息列表                │
  │   [                                                              │
  │     {                                                            │
  │       "position": "after_paragraph_2",                          │
  │       "url": "https://cos.xxx/img1.jpg",                        │
  │       "source": "pexels",                                       │
  │       "keywords": ["科技", "创新"]                               │
  │     }                                                            │
  │   ]                                                              │
  │ final_output: Text               # 最终合并的完整内容           │
  │ created_at: DateTime                                             │
  │ updated_at: DateTime                                             │
  └─────────────────────────────────────────────────────────────────┘

  3.3 大纲结构示例 (JSON Schema)

  {
    "sections": [
      {
        "id": "section_1",
        "title": "引言",
        "level": 1,
        "key_points": ["背景介绍", "问题引出"],
        "estimated_length": 200
      },
      {
        "id": "section_2",
        "title": "核心观点",
        "level": 1,
        "subsections": [
          {
            "id": "section_2_1",
            "title": "观点一",
            "level": 2,
            "key_points": ["论据1", "论据2"]
          }
        ]
      }
    ]
  }

  3.4 Redis 缓存结构

  task:{task_id}:sse_channel    # SSE 消息通道
  task:{task_id}:progress       # 当前进度信息
  task:{task_id}:partial_content # 流式生成的内容片段缓存

  ---
  4. SSE 流式推送数据协议设计

  4.1 基础消息格式

  event: {事件类型}
  data: {JSON 数据}
  id: {消息序号}


  4.2 事件类型定义

  ┌──────────────────┬──────────────┬──────────────────────────────────────────────────────────────┐
  │     事件类型     │     说明     │                           数据结构                           │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ status           │ 任务状态变更 │ {"status": "TITLE_GENERATING", "message": "正在生成标题..."} │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ title_chunk      │ 标题生成片段 │ {"content": "爆款标题", "index": 0}                          │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ title_complete   │ 标题生成完成 │ {"titles": ["标题1", "标题2", "标题3"]}                      │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ outline_chunk    │ 大纲生成片段 │ {"content": "## 引言\n"}                                     │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ outline_complete │ 大纲生成完成 │ {"outline": {...结构化大纲...}}                              │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ content_chunk    │ 正文生成片段 │ {"content": "这是正文内容..."}                               │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ image_progress   │ 配图生成进度 │ {"position": "para_2", "status": "generating"}               │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ image_complete   │ 单张配图完成 │ {"position": "para_2", "url": "https://..."}                 │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ error            │ 错误信息     │ {"code": "LLM_ERROR", "message": "模型调用失败"}             │
  ├──────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
  │ done             │ 任务完成     │ {"article_id": "xxx"}                                        │
  └──────────────────┴──────────────┴──────────────────────────────────────────────────────────────┘

  4.3 完整 SSE 流示例

  event: status
  data: {"status": "TITLE_GENERATING", "message": "正在分析选题..."}
  id: 1

  event: title_chunk
  data: {"content": "如何", "index": 0}
  id: 2

  event: title_chunk
  data: {"content": "在30天内", "index": 0}
  id: 3

  event: title_complete
  data: {"titles": ["如何在30天内打造爆款自媒体账号", "自媒体新人必看：快速涨粉秘籍",
  "从0到10万粉丝：我的自媒体成长之路"]}
  id: 4

  event: status
  data: {"status": "TITLE_READY", "message": "请选择标题"}
  id: 5

  --- 用户选择标题后 ---

  event: status
  data: {"status": "OUTLINE_GENERATING", "message": "正在生成大纲..."}
  id: 6

  event: outline_chunk
  data: {"content": "## 一、引言\n"}
  id: 7

  event: outline_chunk
  data: {"content": "自媒体时代的机遇与挑战\n"}
  id: 8

  ...

  event: outline_complete
  data: {"outline": {"sections": [...]}}
  id: N

  --- 用户确认大纲后 ---

  event: status
  data: {"status": "CONTENT_GENERATING", "message": "正在撰写正文..."}
  id: N+1

  event: content_chunk
  data: {"content": "在当今数字化时代..."}
  id: N+2

  ...

  event: status
  data: {"status": "IMAGE_GENERATING", "message": "正在生成配图..."}
  id: M

  event: image_progress
  data: {"position": "para_2", "status": "generating", "provider": "pexels"}
  id: M+1

  event: image_complete
  data: {"position": "para_2", "url": "https://cos.xxx/img1.jpg", "source": "pexels"}
  id: M+2

  event: done
  data: {"article_id": "uuid-here"}
  id: END

  ---
  5. 五个智能体接口定义

  5.1 智能体基类

  class BaseAgent:
      """智能体基类"""

      @abstractmethod
      async def execute(self, input_data: dict, stream_callback: Callable) -> AgentOutput:
          """
          执行智能体任务

          Args:
              input_data: 输入数据
              stream_callback: 流式回调函数，用于推送中间结果

          Returns:
              AgentOutput: 智能体输出结果
          """
          pass

  5.2 智能体 1: TitleAgent (标题生成)

  class TitleAgentInput:
      topic: str              # 用户输入的选题
      style: str              # 文章风格 (专业/轻松/幽默/深度...)
      extra_description: str  # 用户补充描述（可选）
      count: int = 5          # 生成标题数量，默认 5 个

  class TitleAgentOutput:
      titles: List[TitleOption]

  class TitleOption:
      title: str              # 标题内容
      reasoning: str          # 推荐理由（内部使用，可选返回给前端）
      style_tags: List[str]   # 风格标签 ["吸引眼球", "数据驱动", "情感共鸣"]

  # 接口签名
  async def execute(input: TitleAgentInput, stream_callback: Callable[[str], None]) -> TitleAgentOutput

  5.3 智能体 2: OutlineAgent (大纲生成)

  class OutlineAgentInput:
      selected_title: str     # 用户选择的标题
      topic: str              # 原始选题
      style: str              # 文章风格
      target_length: int      # 目标字数（可选）
      user_modifications: str # 用户修改建议（大纲调整时传入）

  class OutlineAgentOutput:
      outline: OutlineStructure
      estimated_length: int   # 预估总字数

  class OutlineStructure:
      sections: List[Section]

  class Section:
      id: str                 # 段落唯一标识
      title: str              # 段落标题
      level: int               # 层级 (1=一级标题, 2=二级标题...)
      key_points: List[str]    # 要点提示
      estimated_length: int    # 预估字数
      subsections: List[Section]  # 子段落

  # 接口签名
  async def execute(input: OutlineAgentInput, stream_callback: Callable[[str], None]) -> OutlineAgentOutput

  5.4 智能体 3: ContentAgent (正文生成)

  class ContentAgentInput:
      outline: OutlineStructure   # 文章大纲
      selected_title: str         # 选定的标题
      style: str                  # 文章风格
      extra_context: str          # 额外上下文（可选）

  class ContentAgentOutput:
      content: str              # Markdown 格式正文
      image_placeholders: List[ImagePlaceholder]

  class ImagePlaceholder:
      position: str            # 位置标识 "after_section_2", "after_para_5"
      section_id: str          # 所属段落 ID
      keywords: List[str]      # 建议的关键词
      image_type: str          # 图片类型建议 "photo", "diagram", "icon"

  # 接口签名
  async def execute(input: ContentAgentInput, stream_callback: Callable[[str], None]) -> ContentAgentOutput

  5.5 智能体 4: ImageAnalyzerAgent (配图分析)

  class ImageAnalyzerInput:
      content: str                       # Markdown 正文
      image_placeholders: List[ImagePlaceholder]  # 智能体3输出的占位符

  class ImageAnalyzerOutput:
      image_requests: List[ImageRequest]

  class ImageRequest:
      position: str             # 位置标识
      section_id: str           # 所属段落
      image_type: str           # 图片类型
      search_keywords: List[str] # 搜索关键词
      prompt: str               # AI 绘图提示词（文生图时使用）
      priority: int             # 优先级 1-5
      provider_hint: str        # 建议的配图服务 "pexels图库提供免费图片（API KEY已配置）", "seedream 5.0模型AI生成图片（API KEY已配置）", "mermaid"...

  # 接口签名
  async def execute(input: ImageAnalyzerInput) -> ImageAnalyzerOutput
  # 注意：此智能体不需要流式输出，快速分析后返回结果

  5.6 智能体 5: ImageGeneratorAgent (配图生成)

  class ImageGeneratorInput:
      image_requests: List[ImageRequest]  # 配图需求列表

  class ImageGeneratorOutput:
      generated_images: List[GeneratedImage]

  class GeneratedImage:
      position: str            # 对应的位置
      url: str                 # 图片 URL (COS 地址)
      source: str              # 来源服务 "pexels", "seedream"...
      metadata: dict           # 元数据（尺寸、格式等）

  # 接口签名
  async def execute(
      input: ImageGeneratorInput,
      progress_callback: Callable[[str, str, str], None]  # (position, status, provider)
  ) -> ImageGeneratorOutput

  # 注意：此智能体支持并行处理多张图片

  ---
  6. 关键风险点提示

  6.1 技术风险

  ┌──────────────┬────────────────────────────────────┬─────────────────────────────────────────────────────────────┐
  │    风险点    │                描述                │                          缓解措施                           │
  ├──────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
  │ LLM 调用超时 │ DeepSeek                           │ 设置合理超时时间(30-60s)，实现重试机制，准备多 LLM          │
  │              │ 等服务可能因高峰期响应慢或超时     │ 服务降级方案                                                │
  ├──────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
  │ 流式连接中断 │ SSE 连接可能因网络不稳定断开       │ 实现心跳检测，断线自动重连，服务端保存中间状态支持断点续传  │
  ├──────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
  │ 图片生成失败 │ Seedream 等 AI 绘图服务可能失败    │ 多服务降级策略，Picsum 兜底保证流程不中断                   │
  ├──────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
  │ 并发资源竞争 │ 多用户同时使用时 Redis 连接池、LLM │ 配置合理的连接池大小，API 调用限流，队列排队机制            │
  │              │  API 配额可能不足                  │                                                             │
  └──────────────┴────────────────────────────────────┴─────────────────────────────────────────────────────────────┘

  6.2 业务风险

  ┌────────────────┬───────────────────────────────────────┬──────────────────────────────────────────────────────┐
  │     风险点     │                 描述                  │                       缓解措施                       │
  ├────────────────┼───────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ 内容质量不稳定 │ AI 生成的标题/大纲/正文质量参差不齐   │ 提供多选项供用户选择，支持重新生成，引入内容审核机制 │
  ├────────────────┼───────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ 版权图片风险   │ Pexels 等图库的图片使用需遵守授权条款 │ 在最终输出中标注图片来源和授权信息，引导用户合规使用 │
  ├────────────────┼───────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ 生成内容敏感   │ AI 可能生成敏感或不当内容             │ 接入内容审核 API，敏感词过滤，提供内容报告机制       │
  └────────────────┴───────────────────────────────────────┴──────────────────────────────────────────────────────┘

  6.3 架构风险

  ┌──────────────┬────────────────────────────────────────────┬─────────────────────────────────────────────────────┐
  │    风险点    │                    描述                    │                      缓解措施                       │
  ├──────────────┼────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ SQLite       │ SQLite                                     │ 使用 WAL 模式，考虑未来迁移                         │
  │ 并发限制     │ 写并发能力有限，多用户同时写入可能阻塞     │ PostgreSQL，写入操作队列化                          │
  ├──────────────┼────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ 单点故障     │ 所有服务单机部署，无高可用                 │ 核心服务无状态化设计，定期数据备份，制定恢复预案    │
  ├──────────────┼────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ 数据丢失     │ 异常情况下任务中间状态可能丢失             │ Redis 持久化(RDB+AOF)，定期同步到                   │
  │              │                                            │ SQLite，任务恢复机制                                │
  └──────────────┴────────────────────────────────────────────┴─────────────────────────────────────────────────────┘

  6.4 用户体验风险

  ┌──────────────┬───────────────────────────────────────────┬──────────────────────────────────────────────────┐
  │    风险点    │                   描述                    │                     缓解措施                     │
  ├──────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 长时间等待   │ 全流程可能耗时 2-5 分钟，用户可能失去耐心 │ 实时进度反馈，预计剩余时间显示，支持后台运行通知 │
  ├──────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 流式显示抖动 │ 内容流式渲染时可能出现排版抖动            │ 前端使用虚拟滚动，预占位渲染，平滑过渡动画       │
  ├──────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 移动端适配   │ 复杂的编辑和预览界面在移动端体验可能不佳  │ 响应式设计，移动端简化交互，核心功能优先         │
  └──────────────┴───────────────────────────────────────────┴──────────────────────────────────────────────────┘

  ---
  附录：技术选型决策记录

  A. 为什么选择 FastAPI 而非 Flask/Django

  ┌──────────┬─────────────┬───────────────┬─────────────┐
  │  对比项  │   FastAPI   │     Flask     │   Django    │
  ├──────────┼─────────────┼───────────────┼─────────────┤
  │ 异步支持 │ ✅ 原生支持 │ ❌ 需扩展     │ ⚠️ 有限支持 │
  ├──────────┼─────────────┼───────────────┼─────────────┤
  │ SSE 实现 │ ✅ 简单     │ ⚠️ 需手动处理 │ ⚠️ 较复杂   │
  ├──────────┼─────────────┼───────────────┼─────────────┤
  │ API 文档 │ ✅ 自动生成 │ ❌ 需手动     │ ⚠️ 需配置   │
  ├──────────┼─────────────┼───────────────┼─────────────┤
  │ 学习曲线 │ 中等        │ 低            │ 高          │
  ├──────────┼─────────────┼───────────────┼─────────────┤
  │ 性能     │ 高          │ 中            │ 中          │
  └──────────┴─────────────┴───────────────┴─────────────┘

  结论：SSE 和异步是本项目核心需求，FastAPI 天然契合。

  B. 为什么选择 Vue 3 而非 React

  考虑到用户熟悉的开发语言是 Python，Vue 的学习曲线更平缓，且组合式 API 与 Python 的思维方式更接近。React 的 JSX 语法对
  Python 开发者来说需要适应成本。

  C. Celery 是否必需

  对于个人/小团队使用场景，如果并发量确实很低，可以考虑简化：
  - 使用 FastAPI 后台任务替代 Celery
  - 图片生成直接在 SSE 流中处理

  建议初期先实现简化版，根据实际负载决定是否引入 Celery。

  ---
  文档版本: v1.0
  创建日期: 2026-04-07
