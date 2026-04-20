# 自媒体爆款文章生成器 - 项目解读文档

> 本文档旨在帮助第一次接触此项目的开发者快速理解项目的整体架构、核心设计理念和各模块职责，便于后续开发和维护。

---

## 一、项目概览

### 1.1 项目名称

**自媒体爆款文章生成器**（Agent Write Article）

### 1.2 一句话描述

这是一个基于 AI 多智能体协作的文章生成系统，用户只需输入一个选题和文章风格，系统就能自动完成标题、大纲、正文和配图的全流程生成，并通过 SSE（Server-Sent Events）实时推送每一步的进度。

### 1.3 核心价值

对于自媒体创作者，这个系统解决了"不知道写什么标题"、"不知道如何规划结构"、"不知道怎么写正文"、"不知道配什么图"这四个痛点，通过 AI 智能体协作完成从选题到成稿的全过程。

### 1.4 技术栈总览

| 层级 | 技术选型 | 作用 |
|------|----------|------|
| **前端** | Vue 3 + Vite + TypeScript | 用户交互界面 |
| **前端 UI 库** | Ant Design Vue | 页面组件库 |
| **前端状态** | Pinia | 全局状态管理 |
| **前端 HTTP** | Axios | 后端接口调用 |
| **后端框架** | FastAPI | 异步 Web API 服务 |
| **后端 ORM** | SQLAlchemy 2.0（异步） | 数据库操作 |
| **数据库** | SQLite | 存储任务、文章数据 |
| **缓存/消息** | Redis | SSE 连接管理辅助 |
| **AI 服务（文本）** | DeepSeek / 智谱 GLM / 千问 | 标题、大纲、正文生成 |
| **AI 服务（图片）** | Seedream 5.0 | 文章配图生成 |
| **图库服务** | Pexels | 免费图片搜索 |
| **对象存储** | 腾讯云 COS | 图片持久化存储 |

---

## 二、核心业务流程

### 2.1 文章生成的五大步骤

整个文章生成流程是 **流水线式** 的，每个步骤由一个独立的智能体负责：

```
用户输入选题和风格
        ↓
┌──────────────────────────────────────────────────┐
│ 第一步：TitleAgent - 生成 3-5 个爆款标题           │
│         用户从中选择一个满意的标题                  │
├──────────────────────────────────────────────────┤
│ 第二步：OutlineAgent - 根据选定标题生成文章大纲     │
│         大纲为 JSON 结构，支持用户修改后重新优化    │
├──────────────────────────────────────────────────┤
│ 第三步：ContentAgent - 根据标题+大纲生成正文        │
│         输出 Markdown 格式，包含配图占位符          │
├──────────────────────────────────────────────────┤
│ 第四步：ImageAnalyzerAgent - 解析正文配图占位符     │
│         生成结构化的图片任务列表                   │
├──────────────────────────────────────────────────┤
│ 第五步：ImageGeneratorAgent - 并行生成所有配图      │
│         上传图片到 COS，替换占位符，合并图文        │
└──────────────────────────────────────────────────┘
        ↓
    最终成品：一篇完整的、图文并茂的 Markdown + HTML 文章
```

### 2.2 任务状态流转

每个生成任务都有一个明确的状态机，确保流程可控：

```
CREATED（已创建）
   ↓
TITLE_GENERATING（标题生成中）
   ↓
TITLE_READY（标题就绪，等待用户选择）
   ↓
OUTLINE_GENERATING（大纲生成中）
   ↓
OUTLINE_READY（大纲就绪，等待用户确认）
   ↓
CONTENT_GENERATING（正文生成中）
   ↓
CONTENT_READY（正文完成，等待配图）
   ↓
IMAGE_GENERATING（配图生成中）
   ↓
COMPLETED（全部完成）

任何阶段都可能跳转到 FAILED（失败）
```

### 2.3 SSE 实时推送机制

为了让用户知道进度，系统使用 SSE 技术在每个步骤完成后向浏览器推送消息：

- **标题阶段**: 推送标题片段 → 推送标题完成
- **大纲阶段**: 推送大纲片段 → 推送大纲完成
- **正文阶段**: 推送正文片段 → 推送正文完成
- **图片阶段**: 推送每张图片进度 → 推送全部完成
- **完成**: 推送 `done` 事件，携带最终文章内容

---

## 三、项目目录结构

### 3.1 顶级目录

```
agent-write-article2/
├── frontend/                 # 前端项目（Vue 3）
├── backend/                  # 后端项目（FastAPI）
├── deploy-package/           # 生产部署包
├── .env.example             # 环境变量模板
├── docker-compose.yml       # 开发环境 Docker 配置
├── docker-compose.prod.yml  # 生产环境 Docker 配置
├── nginx.conf               # Nginx 配置
└── README.md                # 项目说明
```

### 3.2 后端目录详解

```
backend/
├── app/
│   ├── agents/              # 【核心】五大智能体
│   │   ├── base_agent.py          # 智能体基类，统一接口
│   │   ├── title_agent.py         # Agent1: 标题生成
│   │   ├── outline_agent.py       # Agent2: 大纲生成
│   │   ├── content_agent.py       # Agent3: 正文生成
│   │   ├── image_analyzer_agent.py # Agent4: 图片分析
│   │   └── image_generator_agent.py # Agent5: 图片生成
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── health.py          # 健康检查接口
│   │       ├── task.py            # 任务管理接口（CRUD）
│   │       ├── article.py         # 文章管理接口
│   │       └── sse.py             # SSE 连接接口
│   │
│   ├── image/               # 图片服务层
│   │   ├── providers/
│   │   │   ├── pexels_service.py      # Pexels 图片搜索
│   │   │   ├── seedream_service.py    # Seedream AI 绘图
│   │   │   ├── picsum_service.py      # Picsum 随机图片
│   │   │   └── iconify_service.py     # Iconify 图标服务
│   │   ├── base_provider.py           # 图片提供者基类
│   │   └── strategy.py                # 图片服务策略（多提供者调度）
│   │
│   ├── models/              # 数据库模型（SQLAlchemy ORM）
│   │   ├── base.py                  # 基础模型
│   │   ├── task.py                  # 任务表模型
│   │   ├── article.py               # 文章表模型
│   │   └── user.py                  # 用户表模型（预留）
│   │
│   ├── schemas/             # Pydantic 数据验证模型
│   │   ├── task.py                  # 任务输入输出 Schema
│   │   ├── article.py               # 文章 Schema
│   │   ├── image.py                 # 图片相关 Schema
│   │   ├── response.py              # 统一响应格式
│   │   └── sse.py                   # SSE 事件 Schema
│   │
│   ├── services/            # 业务服务层
│   │   ├── llm_service.py           # LLM 调用服务（支持多提供者）
│   │   ├── task_repository.py       # 任务数据库操作
│   │   ├── article_repository.py    # 文章数据库操作
│   │   └── base_repository.py       # 基础数据库操作
│   │
│   ├── utils/               # 工具类
│   │   ├── database.py              # 数据库连接管理
│   │   ├── redis_client.py          # Redis 客户端
│   │   ├── sse_manager.py           # SSE 连接管理器
│   │   └── cos_uploader.py          # 腾讯云 COS 上传
│   │
│   ├── config.py            # 应用配置（环境变量管理）
│   └── main.py              # FastAPI 应用入口
│
├── prompts/                 # Prompt 模板文件
│   ├── title_generation.md          # 标题生成 Prompt
│   ├── outline_generation.md        # 大纲生成 Prompt
│   ├── outline_optimization.md      # 大纲优化 Prompt
│   └── content_generation.md        # 正文生成 Prompt
│
├── scripts/                 # 工具脚本
│   ├── init_db.py                   # 数据库初始化
│   └── verify_*.py                  # 各种验证测试脚本
│
├── tests/                   # 测试文件
│   ├── conftest.py                  # 测试配置
│   ├── test_agents.py               # 智能体测试
│   ├── test_api.py                  # API 测试
│   └── test_image_agents.py         # 图片智能体测试
│
├── requirements.txt         # Python 依赖
├── pytest.ini               # 测试配置
├── alembic.ini              # 数据库迁移配置
└── Dockerfile               # 后端 Docker 构建文件
```

### 3.3 前端目录详解

```
frontend/
├── src/
│   ├── api/
│   │   ├── http.ts                  # Axios 封装
│   │   ├── sse.ts                   # SSE 客户端封装
│   │   ├── index.ts                 # API 接口汇总
│   │   └── generated/
│   │       └── schema.d.ts          # OpenAPI 自动生成的类型定义
│   │
│   ├── assets/
│   │   └── main.css                 # 全局样式
│   │
│   ├── components/
│   │   └── Layout.vue               # 页面布局组件
│   │
│   ├── composables/
│   │   ├── index.ts
│   │   └── useSSE.ts                # SSE 通信 Hook
│   │
│   ├── router/
│   │   └── index.ts                 # 路由配置
│   │
│   ├── stores/
│   │   ├── index.ts
│   │   └── task.ts                  # 任务状态管理（Pinia）
│   │
│   ├── types/
│   │   └── index.d.ts               # TypeScript 类型定义
│   │
│   ├── views/
│   │   ├── Home.vue                 # 首页（创建文章入口）
│   │   ├── Create.vue               # 创建文章页（核心流程页）
│   │   ├── Result.vue               # 结果展示页
│   │   ├── History.vue              # 历史记录页
│   │   ├── About.vue                # 关于页
│   │   ├── SSETest.vue              # SSE 测试页
│   │   └── NotFound.vue             # 404 页
│   │
│   ├── App.vue                      # 根组件
│   └── main.ts                      # 应用入口
│
├── public/
│   └── vite.svg
├── index.html                       # HTML 模板
├── package.json                     # 前端依赖
├── vite.config.ts                   # Vite 配置
└── tsconfig.json                    # TypeScript 配置
```

---

## 四、后端核心模块详解

### 4.1 智能体架构（Agents）

**设计理念**：每个智能体是一个独立的类，继承自 `BaseAgent`，实现统一的 `execute()` 方法。

#### 4.1.1 BaseAgent（智能体基类）

```python
# 位置: backend/app/agents/base_agent.py
```

**职责**：
- 定义智能体的统一接口：`execute(input_data, stream_callback)`
- 封装 LLM 调用：`call_llm()`（同步）和 `call_llm_stream()`（异步）
- 提供 Prompt 模板加载：`load_prompt_template()`
- 提供 Prompt 变量填充：`fill_prompt_template()`

**关键方法**：
| 方法名 | 作用 |
|--------|------|
| `execute()` | 抽象方法，子类必须实现，执行具体任务 |
| `call_llm()` | 调用 LLM 获取完整响应 |
| `call_llm_stream()` | 流式调用 LLM，逐个返回文本片段 |
| `load_prompt_template()` | 从 prompts 目录加载 Markdown 模板 |
| `fill_prompt_template()` | 用 `{{变量名}}` 语法填充模板 |

#### 4.1.2 TitleAgent（标题生成智能体）

```python
# 位置: backend/app/agents/title_agent.py
```

**职责**：根据用户输入的选题，生成 3-5 个爆款标题方案。

**输入**：
```python
TitleAgentInput:
  - topic: 用户选题（必填）
  - style: 文章风格（默认"专业"）
  - extra_description: 补充描述（可选）
  - count: 标题数量（默认 5，范围 3-5）
```

**输出**：
```python
TitleAgentOutput:
  - titles: List[TitleOption]  # 标题列表
  - raw_response: 原始 LLM 响应
```

**工作流程**：
1. 加载 `prompts/title_generation.md` 模板
2. 填充选题、风格等变量
3. 调用 LLM（temperature=0.8，创意模式）
4. 使用正则表达式解析 LLM 响应，提取标题、推荐理由、风格标签
5. 如果正则解析失败，降级为简单提取

#### 4.1.3 OutlineAgent（大纲生成智能体）

```python
# 位置: backend/app/agents/outline_agent.py
```

**职责**：根据选定标题生成结构化的文章大纲（支持 JSON 格式）。

**输入**：
```python
OutlineAgentInput:
  - selected_title: 用户选定的标题
  - topic: 原始选题
  - style: 文章风格
  - target_length: 目标字数（500-10000）
  - extra_description: 补充描述
  - optimize_mode: 是否为优化模式
  - user_modifications: 用户修改建议（优化模式）
  - current_outline: 当前大纲（优化模式）
```

**输出**：
```python
OutlineAgentOutput:
  - outline: OutlineStructure  # 结构化大纲
  - estimated_length: 预估总字数
```

**两种模式**：
- **生成模式**: 从零开始生成大纲，使用 `outline_generation.md` 模板
- **优化模式**: 根据用户修改建议优化现有大纲，使用 `outline_optimization.md` 模板

**解析策略**（优先级从高到低）：
1. 提取 JSON 代码块中的内容
2. 直接提取 JSON 对象
3. 降级为 Markdown 标题解析
4. 如果全部失败，返回默认大纲

#### 4.1.4 ContentAgent（正文生成智能体）

```python
# 位置: backend/app/agents/content_agent.py
```

**职责**：根据标题和大纲生成完整的 Markdown 正文。

**输入**：
```python
ContentAgentInput:
  - selected_title: 选定的标题
  - outline: 确认后的文章大纲（字典格式）
  - style: 文章风格
  - extra_context: 额外上下文（可选）
```

**输出**：
```python
ContentAgentOutput:
  - content: Markdown 正文
  - image_placeholders: List[ImagePlaceholder]  # 配图占位符
  - word_count: 字数统计
```

**配图占位符格式**：
```markdown
![IMAGE_PLACEHOLDER](image_1|关键词1、关键词2、关键词3)
```

**关键功能**：
- 将大纲字典转换为可读文本格式（`_outline_to_text()`）
- 从正文中提取配图占位符信息（`_extract_image_placeholders()`）
- 计算正文字数，排除占位符（`_count_words()`）

#### 4.1.5 ImageAnalyzerAgent（图片分析智能体）

```python
# 位置: backend/app/agents/image_analyzer_agent.py
```

**职责**：解析正文中的 `IMAGE_PLACEHOLDER` 占位符，生成结构化的图片任务列表。

**特点**：这是唯一一个 **不调用 LLM** 的智能体，纯靠正则解析。

**输入**：
```python
ImageAnalyzerInput:
  - content: Markdown 正文内容
```

**输出**：
```python
ImageAnalyzerOutput:
  - tasks: List[ImageTask]  # 图片任务列表
  - totalCount: 任务总数
  - contentHash: 正文内容 hash
  - parseErrors: 解析错误列表
```

**核心功能**：
- 正则匹配占位符，提取编号和关键词
- 根据关键词推断图片类型（photo/diagram/icon/illustration）
- 提取占位符前一个自然段作为上下文（用于增强图片生成效果）
- 处理重复占位符、格式不完整等错误情况

**图片类型推断规则**：
```python
图标关键词: '图标', 'icon', 'logo', '标志', '符号', '装饰'  → ICON
图表关键词: '图表', '流程图', 'diagram', '架构', '关系图'   → DIAGRAM
插画关键词: '插画', '插图', '手绘', '卡通'                   → ILLUSTRATION
其他默认: photo（照片）
```

#### 4.1.6 ImageGeneratorAgent（图片生成智能体）

```python
# 位置: backend/app/agents/image_generator_agent.py
```

**职责**：接收图片任务列表，并行执行所有任务，上传图片到 COS，合并图文。

**核心特点**：
- **并行执行**: 使用 `asyncio.gather()` 同时发起所有图片请求
- **容错设计**: `return_exceptions=True`，单图失败不影响其他图片
- **无兜底策略**: 目前仅使用 Seedream，没有 fallback 服务
- **图文合并**: 将成功的图片 URL 替换回正文，失败的占位符删除

**输入**：
```python
ImageGeneratorInput:
  - tasks: 图片任务列表
  - content: 原始正文内容
  - taskId: 文章生成任务 ID
```

**输出**：
```python
ImageGeneratorOutput:
  - results: 图片结果列表
  - mergedContent: 合并后的 Markdown 正文
  - mergedHtml: 合并后的 HTML 富文本
  - totalCount / successCount / failedCount / skippedCount
```

**工作流程**：
1. 发送任务开始事件（SSE）
2. 并行执行所有图片任务（使用 asyncio.gather）
3. 每个任务：尝试 Seedream → 上传 COS → 发送完成事件
4. 图文合并（替换占位符为真实图片 URL）
5. Markdown 转 HTML（使用 markdown 库）
6. 发送全部完成事件（SSE）

#### 4.1.7 LLM 服务层

```python
# 位置: backend/app/services/llm_service.py
```

**职责**：统一封装多个 LLM 提供者的调用逻辑。

**支持的提供者**：
- DeepSeek（默认）
- 智谱 GLM
- 千问

**功能**：
- 根据配置动态切换 LLM 提供者
- 支持同步和流式调用
- 内置异常处理和重试逻辑
- 支持 Mock 模式（测试用）

### 4.2 数据库设计

#### 4.2.1 表结构

**Task 表（任务表）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) UUID | 任务唯一标识 |
| user_id | String(36) | 用户 ID（预留） |
| topic | String(500) | 用户输入的选题 |
| style | String(50) | 文章风格 |
| extra_description | Text | 用户补充描述 |
| status | Enum(TaskStatus) | 当前状态 |
| status_message | String(200) | 状态描述消息 |
| progress | String(5) | 进度百分比 |
| error_message | Text | 错误信息 |
| stage_times | JSON | 各阶段完成时间 |
| created_at / updated_at | DateTime | 时间戳 |

**Article 表（文章表）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) UUID | 文章唯一标识 |
| task_id | String(36) | 关联任务 ID |
| selected_title | String(200) | 用户选定的标题 |
| title_options | JSON | 标题方案列表 |
| outline | JSON | 结构化大纲 |
| content | Text | Markdown 正文 |
| images | JSON | 配图信息列表 |
| final_output | Text | 最终合并内容 |
| final_html | Text | 最终 HTML 富文本 |
| word_count | Integer | 字数统计 |
| created_at / updated_at | DateTime | 时间戳 |

**User 表（用户表，预留）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) UUID | 用户唯一标识 |
| username | String(100) | 用户名 |
| email | String(200) | 邮箱 |

#### 4.2.2 数据库操作架构

```
BaseRepository[Model]          # 基础 CRUD 操作
    ├── ArticleRepository      # 文章特有操作
    └── TaskRepository         # 任务特有操作
```

**BaseRepository 提供的方法**：
- `create()` - 创建记录
- `get()` - 根据 ID 查询
- `get_multi()` - 批量查询（分页）
- `update()` - 更新记录
- `delete()` - 删除记录
- `count()` - 统计数量

### 4.3 SSE 推送机制

#### 4.3.1 架构设计

```
SSEManager（管理器）
    └── 维护 task_id → SSEConnection 映射
    └── 管理所有活跃连接的生命周期
    └── 发送各种类型的事件

SSEConnection（单个连接）
    └── 使用 asyncio.Queue 作为消息队列
    └── 60 秒心跳机制
    └── 30 分钟超时
```

#### 4.3.2 事件类型

| 事件类型 | 阶段 | 说明 |
|----------|------|------|
| `status` | - | 任务状态变更 |
| `title_chunk` | title | 标题生成片段 |
| `title_complete` | title | 标题生成完成 |
| `outline_chunk` | outline | 大纲生成片段 |
| `outline_complete` | outline | 大纲生成完成 |
| `content_chunk` | content | 正文生成片段 |
| `content_complete` | content | 正文生成完成 |
| `image_task_start` | image | 图片任务开始 |
| `image_progress` | image | 单张图片进度 |
| `image_complete` | image | 单张图片完成 |
| `image_all_complete` | image | 所有图片完成 |
| `error` | - | 错误信息 |
| `done` | - | 任务完成 |
| `heartbeat` | - | 心跳 |

#### 4.3.3 SSE 数据格式

```
event: 事件类型
data: {"event":"事件类型","data":{...},"progress":50,"message":"..."}
id: 1
```

### 4.4 API 接口设计

#### 4.4.1 统一响应格式

所有接口都使用统一的响应格式：

```python
# 成功响应
{
  "code": 0,
  "message": "操作成功",
  "data": {...}
}

# 错误响应
{
  "code": "1001",
  "message": "参数错误",
  "data": None
}

# 分页响应
{
  "code": 0,
  "message": "操作成功",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

#### 4.4.2 接口分类

| 路由前缀 | 说明 | 主要接口 |
|----------|------|----------|
| `/api` | 健康检查 | `GET /api/health`, `GET /api/health/full` |
| `/api/tasks` | 任务管理 | 创建、查询、更新、删除任务 |
| `/api/articles` | 文章管理 | 查询、导出、标题选择、大纲更新 |
| `/api/sse/connect/{task_id}` | SSE 连接 | 建立 SSE 流 |
| `/api/sse/test/{task_id}` | SSE 测试 | 模拟推送测试事件 |

---

## 五、前端核心模块详解

### 5.1 页面结构

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | `/` | 首页，展示系统介绍和入口 |
| Create | `/create` | **核心页面**，用户输入选题、选择风格，触发文章生成流程 |
| Result | `/result/:taskId` | 文章结果展示页 |
| History | `/history` | 历史记录列表 |
| SSETest | `/sse-test` | SSE 通信测试页面 |
| About | `/about` | 关于页面 |

### 5.2 核心功能模块

#### 5.2.1 SSE 客户端（useSSE）

```typescript
// 位置: frontend/src/composables/useSSE.ts
```

**职责**：封装 EventSource API，管理 SSE 连接的生命周期。

**功能**：
- 自动建立和断开连接
- 监听各种 SSE 事件类型
- 维护消息队列和进度状态
- 处理连接断开和重连

#### 5.2.2 任务状态管理（task store）

```typescript
// 位置: frontend/src/stores/task.ts
```

**职责**：使用 Pinia 管理全局任务状态。

**管理的数据**：
- 当前任务信息
- 任务进度百分比
- SSE 事件历史
- 文章生成结果

#### 5.2.3 HTTP 封装

```typescript
// 位置: frontend/src/api/http.ts
```

**功能**：
- 封装 Axios，设置默认 baseURL 和超时时间
- 自动添加 token（预留）
- 统一错误处理

### 5.3 关键技术点

- **SSE 通信**: 使用原生 `EventSource` API 建立长连接
- **Markdown 渲染**: 使用 `markdown-it` 库将 Markdown 转换为 HTML
- **代码高亮**: 使用 `highlight.js` 对代码块进行语法高亮
- **组件库**: 全部使用 Ant Design Vue 组件，保持 UI 一致性

---

## 六、图片服务架构

### 6.1 设计模式：策略模式

图片服务采用 **策略模式** 设计，支持动态切换不同的图片提供者。

```python
ImageServiceStrategy（策略类）
    ├── 注册多个 ImageProvider
    ├── 根据图片类型选择合适的提供者
    ├── 支持优先级调度
    └── 支持可用性检查
```

### 6.2 图片提供者

| 服务 | 类型 | 说明 |
|------|------|------|
| Seedream | AI 生成 | 火山引擎 Seedream 5.0，AI 绘图服务 |
| Pexels | 图库搜索 | 免费高清图片搜索 |
| Picsum | 随机图片 | Lorem Picsum 随机图片服务 |
| Iconify | 图标服务 | 开源图标库，仅用于图标/装饰 |

### 6.3 图片处理流程

```
正文中的占位符
    ↓
ImageAnalyzerAgent 解析
    ↓
生成 ImageTask 列表
    ↓
ImageGeneratorAgent 并行执行
    ↓
每个任务：
  1. 调用 Seedream 生成图片
  2. 上传到腾讯云 COS
  3. 返回永久 URL
    ↓
替换占位符为真实图片 URL
    ↓
输出最终文章
```

### 6.4 对象存储

- **服务提供商**: 腾讯云 COS（Cloud Object Storage）
- **存储路径**: `article-images/{task_id}/{placeholder_id}.{ext}`
- **目的**: 将 AI 生成的图片持久化存储，避免临时 URL 失效

---

## 七、部署架构

### 7.1 开发环境

```
本地机器
├── 后端: uvicorn app.main:app --reload --port 8000
└── 前端: npm run dev (localhost:5173)
```

### 7.2 生产环境

```
Nginx（反向代理）
├── /api/* → FastAPI 后端 (localhost:8000)
└── /* → 前端静态文件

Docker 容器
├── backend: FastAPI + SQLite + Redis
├── frontend: Vue 3 静态文件
└── redis: Redis 服务
```

### 7.3 Docker 配置

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 开发环境配置 |
| `docker-compose.prod.yml` | 生产环境配置 |
| `backend/Dockerfile` | 后端镜像构建 |
| `nginx.conf` | Nginx 反向代理配置 |
| `.dockerignore` | Docker 构建忽略文件 |

---

## 八、配置管理

### 8.1 环境变量（.env）

所有配置通过环境变量管理，使用 pydantic-settings 自动加载。

**必填项**：
```bash
DEEPSEEK_API_KEY=xxx           # DeepSeek API Key
PEXELS_API_KEY=xxx             # Pexels 图库 API Key
COS_SECRET_ID=xxx              # 腾讯云 COS Secret ID
COS_SECRET_KEY=xxx             # 腾讯云 COS Secret Key
COS_BUCKET=xxx                 # COS 存储桶名称
SEEDREAM_API_KEY=xxx           # Seedream AI 绘图 API Key
SEEDREAM_ENDPOINT_ID=xxx       # Seedream 端点 ID
```

**可选项**：
```bash
DEFAULT_LLM_PROVIDER=qianwen   # 默认 LLM 提供者 (deepseek/zhipu/qianwen)
ZHIPU_API_KEY=xxx              # 智谱 GLM API Key
QIANWEN_API_KEY=xxx            # 千问 API Key
REDIS_HOST=localhost           # Redis 地址
REDIS_PORT=6379                # Redis 端口
```

### 8.2 LLM 多提供者支持

系统支持同时配置多个 LLM 提供者，通过 `DEFAULT_LLM_PROVIDER` 切换：

```python
# config.py 中的 get_llm_config() 方法
configs = {
    "deepseek": {...},
    "zhipu": {...},
    "qianwen": {...},
}
```

---

## 九、测试体系

### 9.1 后端测试

使用 pytest 进行测试，测试文件位于 `backend/tests/`。

| 测试文件 | 说明 |
|----------|------|
| `test_agents.py` | 智能体单元测试 |
| `test_api.py` | API 接口集成测试 |
| `test_image_agents.py` | 图片智能体测试 |
| `conftest.py` | 测试配置和 fixture |

### 9.2 前端测试

```bash
npm run lint      # ESLint 代码检查
npm run build     # 构建检查（包含 TypeScript 类型检查）
```

### 9.3 SSE 测试

系统提供专门的 SSE 测试端点：
- 后端：`GET /api/sse/test/{task_id}`
- 前端：访问 `/sse-test` 页面进行可视化测试

---

## 十、开发规范

### 10.1 Python 代码规范

- **命名规范**: 使用 snake_case（变量、函数）、PascalCase（类）
- **类型提示**: 所有函数必须有类型注解
- **文档字符串**: 每个类、方法、函数必须有 docstring
- **异常处理**: 关键操作必须捕获异常并记录日志

### 10.2 前端代码规范

- **命名规范**: 使用 camelCase（变量、函数）、PascalCase（组件）
- **TypeScript**: 所有变量和函数必须有类型注解
- **组件风格**: 使用 Vue 3 Composition API（`<script setup>`）
- **样式管理**: 使用 scoped 样式，避免全局污染

### 10.3 Git 提交规范

建议的提交消息格式：
```
<type>: <description>

type 可选值:
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- test: 测试相关
- chore: 构建/工具调整
```

---

## 十一、当前开发状态

### 11.1 已完成功能

- [x] 项目初始化
- [x] 后端基础架构（Router → Service → Database）
- [x] 前端基础架构（Vue 3 + Ant Design Vue）
- [x] 数据库模型设计（Task / Article / User）
- [x] CRUD 操作接口
- [x] 健康检查接口
- [x] SSE 数据协议设计
- [x] SSE 连接管理器（后端）
- [x] SSE 客户端封装（前端）
- [x] SSE 测试端点和测试页面
- [x] 五大智能体完整实现
- [x] 图片服务层（多提供者策略）
- [x] 腾讯云 COS 上传
- [x] 图文合并功能

### 11.2 待完善功能

根据 README 标记，以下功能标记为未完成（可能部分已实现但需完善）：
- [ ] 智能体测试完善
- [ ] 配图服务完善
- [ ] 完整业务流程端到端测试

---

## 十二、常见问题与解决方案

### 12.1 LLM 调用失败

**原因**：API Key 配置错误或网络问题。
**解决**：
1. 检查 `.env` 文件中的 API Key 是否正确
2. 确认 `DEFAULT_LLM_PROVIDER` 与实际配置的提供者一致
3. 查看日志中的错误信息

### 12.2 SSE 连接断开

**原因**：长时间无消息或网络中断。
**解决**：
1. 系统内置 60 秒心跳机制
2. 前端应处理 `onerror` 事件，实现自动重连
3. 检查 Nginx 配置中的 `proxy_read_timeout` 设置

### 12.3 图片生成失败

**原因**：Seedream 服务不可用或 COS 上传失败。
**解决**：
1. 检查 `SEEDREAM_API_KEY` 和 `SEEDREAM_ENDPOINT_ID` 配置
2. 检查腾讯云 COS 配置（Secret ID/Key/Bucket）
3. 单图失败不影响其他图片，系统会自动跳过失败任务

### 12.4 数据库文件位置

```
backend/data/article.db  # 开发环境
```

如需重置数据库，删除此文件后重启后端服务即可。

---

## 十三、后续优化建议

### 13.1 架构层面

1. **增加消息队列**: 当前 SSE 使用内存队列，重启后端会丢失连接。可考虑使用 Redis 作为持久化消息队列
2. **增加重试机制**: LLM 调用失败时，可加入自动重试逻辑
3. **引入 Celery**: 对于耗时的图片生成任务，可以使用 Celery 进行异步任务管理
4. **增加限流**: 防止恶意请求耗尽 API 配额

### 13.2 功能层面

1. **用户系统**: 完善用户注册、登录、权限管理
2. **模板系统**: 提供多种文章模板，用户可选择不同类型的模板
3. **历史记录增强**: 增加搜索、筛选、收藏功能
4. **导出功能增强**: 支持导出为 Word、PDF 等格式
5. **编辑功能**: 允许用户在生成后手动修改文章内容

### 13.3 性能层面

1. **增加缓存**: 对于相同的选题，可以缓存历史结果
2. **并行优化**: 标题、大纲、正文生成目前是串行，可考虑部分并行
3. **图片预生成**: 提前生成常用场景的配图
4. **数据库优化**: 数据量增大后，从 SQLite 迁移到 PostgreSQL 或 MySQL

---

## 十四、快速上手指南

### 14.1 首次运行步骤

```bash
# 1. 配置环境变量
cd backend
cp .env.example .env
# 编辑 .env，填入 API Keys

# 2. 启动后端
python -m venv ../venv
../venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 启动前端（新终端）
cd frontend
npm install
npm run dev

# 4. 访问应用
# 前端: http://localhost:5173
# 后端 API 文档: http://localhost:8000/docs
```

### 14.2 开发建议

1. **先理解智能体架构**: 五大智能体是核心，理解 `BaseAgent` 的设计思想
2. **掌握 SSE 流程**: 前后端通过 SSE 通信，理解消息推送机制
3. **熟悉数据流转**: 从用户输入到最终文章生成，数据如何流转
4. **使用 API 文档**: FastAPI 自动生成 Swagger 文档，方便调试接口

---

## 十五、附录

### 15.1 关键文件索引

| 文件 | 路径 | 说明 |
|------|------|------|
| 后端入口 | `backend/app/main.py` | FastAPI 应用入口 |
| 配置管理 | `backend/app/config.py` | 环境变量管理 |
| 智能体基类 | `backend/app/agents/base_agent.py` | 智能体统一接口 |
| 任务模型 | `backend/app/models/task.py` | 任务表 ORM 模型 |
| 文章模型 | `backend/app/models/article.py` | 文章表 ORM 模型 |
| SSE 管理 | `backend/app/utils/sse_manager.py` | SSE 连接管理器 |
| LLM 服务 | `backend/app/services/llm_service.py` | LLM 调用封装 |
| 前端入口 | `frontend/src/main.ts` | Vue 应用入口 |
| SSE 客户端 | `frontend/src/composables/useSSE.ts` | SSE 通信 Hook |
| 任务状态 | `frontend/src/stores/task.ts` | Pinia 状态管理 |

### 15.2 常用命令

```bash
# 后端
uvicorn app.main:app --reload --port 8000  # 启动开发服务器
pytest                                      # 运行测试
python scripts/init_db.py                   # 初始化数据库

# 前端
npm run dev                                 # 启动开发服务器
npm run build                               # 生产构建
npm run lint                                # 代码检查

# Docker
docker-compose up -d                        # 启动所有服务
docker-compose down                         # 停止所有服务
```

---

**文档版本**: v1.0  
**最后更新**: 2026-04-20  
**维护者**: AI 编程助手
