# 自媒体爆款文章生成器

> 基于 AI 多智能体协作的文章生成系统，通过 SSE 流式推送实时展示创作进度

## 📋 项目简介

本项目通过五大智能体协作，依次完成标题、大纲、正文和配图的生成：
- **TitleAgent**: 生成多个爆款标题方案
- **OutlineAgent**: 根据选定标题生成结构化大纲
- **ContentAgent**: 流式生成 Markdown 正文
- **ImageAnalyzerAgent**: 分析正文确定配图需求
- **ImageGeneratorAgent**: 并行生成文章配图

## 🛠 技术栈

### 前端
- Vue 3 + Vite + TypeScript
- Ant Design Vue (UI 组件库)
- Pinia (状态管理)
- Axios (HTTP 请求)
- 原生 EventSource (SSE 连接)

### 后端
- FastAPI (异步 Web 框架)
- SQLAlchemy 2.0 (异步 ORM)
- Redis (缓存 / 消息队列)
- SQLite (数据库)
- OpenAI SDK (LLM 调用)

### AI 服务
- DeepSeek / 智谱 GLM / 千问 (LLM)
- Seedream 5.0 (AI 绘图)
- Pexels (图库搜索)

## 📁 目录结构

```
agent-write-article2/
├── frontend/                 # 前端项目
│   ├── src/
│   │   ├── api/             # API 封装 (HTTP + SSE)
│   │   ├── components/      # Vue 组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── views/           # 页面视图
│   │   └── router/          # 路由配置
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                  # 后端项目
│   ├── app/
│   │   ├── api/routes/      # API 路由
│   │   ├── services/        # 业务服务层
│   │   ├── agents/          # 五大智能体
│   │   ├── image/           # 配图服务层
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # Pydantic 模型
│   │   └── utils/           # 工具类
│   ├── tests/               # 测试文件
│   ├── requirements.txt
│   └── main.py
│
├── .env.example             # 环境变量模板
├── .gitignore
└── README.md
```

## 🚀 快速启动

### 1. 环境准备

确保已安装：
- Python 3.10+
- Node.js 18+
- Redis (可选，用于缓存)

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv ../writearticle-venv

# 激活虚拟环境 (Windows)
..\writearticle-venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
copy .env.example .env

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 3. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

- 前端: http://localhost:5173
- 后端 API 文档: http://localhost:8000/docs
- 后端 ReDoc: http://localhost:8000/redoc

## 🔧 配置说明

### 后端环境变量 (.env)

| 变量 | 说明 | 必填 |
|------|------|------|
| DEEPSEEK_API_KEY | DeepSeek API Key | ✅ |
| ZHIPU_API_KEY | 智谱 GLM API Key | 可选 |
| QIANWEN_API_KEY | 千问 API Key | 可选 |
| DEFAULT_LLM_PROVIDER | 默认 LLM 提供者 | deepseek |
| PEXELS_API_KEY | Pexels 图库 API Key | ✅ |
| COS_SECRET_ID | 腾讯云 COS Secret ID | ✅ |
| COS_SECRET_KEY | 腾讯云 COS Secret Key | ✅ |

## 📡 SSE 数据协议

项目使用 SSE (Server-Sent Events) 实现实时推送：

```
event: status
data: {"status": "TITLE_GENERATING", "message": "正在生成标题..."}
id: 1

event: title_chunk
data: {"content": "爆款标题", "index": 0}
id: 2

event: title_complete
data: {"titles": ["标题1", "标题2", "标题3"]}
id: 3
```

### 事件类型

| 事件 | 说明 |
|------|------|
| `status` | 任务状态变更 |
| `title_chunk` | 标题生成片段 |
| `title_complete` | 标题生成完成 |
| `outline_chunk` | 大纲生成片段 |
| `outline_complete` | 大纲生成完成 |
| `content_chunk` | 正文生成片段 |
| `image_progress` | 配图生成进度 |
| `image_complete` | 单张配图完成 |
| `error` | 错误信息 |
| `done` | 任务完成 |

## 🧪 测试

### 后端测试

```bash
cd backend
pytest
```

### 前端测试

```bash
cd frontend
npm run lint
```

## 📝 开发进度

- [x] 项目初始化
- [x] 后端基础架构 (Router → Service → Database)
- [x] 前端基础架构 (Vue 3 + Ant Design Vue)
- [x] SSE 数据协议设计
- [ ] 智能体实现
- [ ] 配图服务实现
- [ ] 完整业务流程

## 📄 License

MIT