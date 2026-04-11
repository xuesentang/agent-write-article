---
name: fix-seedream-api-key-and-image-display
overview: 修复 Seedream API 调用失败（API Key 被错误填为 Endpoint ID）导致图片降级到 Picsum 的问题，以及确认前端图片渲染是否正常
design:
  architecture:
    framework: vue
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 28px
      weight: 700
    subheading:
      size: 18px
      weight: 600
    body:
      size: 15px
      weight: 400
  colorSystem:
    primary:
      - "#0958D9"
      - "#1677FF"
    background:
      - "#FFFFFF"
      - "#F5F5F5"
    text:
      - "#1F1F1F"
      - "#8C8C8C"
    functional:
      - "#52C41A"
      - "#FF4D4F"
      - "#FAAD14"
todos:
  - id: fix-seedream-key
    content: 修复 .env 中 SEEDREAM_API_Key 配置错误并增强 seedream_service.py 的 API Key 格式校验与预警日志
    status: completed
  - id: fix-sse-payload
    content: 修改 sse_manager.py 让 IMAGE_ALL_COMPLETE 或 done 事件携带 mergedContent/final_output
    status: completed
  - id: fix-create-vue
    content: 修复 Create.vue 在配图完成后更新 store 的 content/finalOutput 并在完成阶段展示最终内容
    status: completed
    dependencies:
      - fix-sse-payload
  - id: fix-result-vue
    content: 确保 Result.vue 中 markdown-content 的图片样式正确渲染（img 标签可见且有合理尺寸）
    status: completed
    dependencies:
      - fix-sse-payload
  - id: verify-flow
    content: 端到端验证：Seedream 调用链路 → COS 上传 → 图文合并 → SSE 推送 → 前端渲染全流程
    status: completed
    dependencies:
      - fix-seedream-key
      - fix-sse-payload
      - fix-create-vue
      - fix-result-vue
---

## 问题现象

用户运行项目后发现两个问题：

1. **图片出不来**：最终文章中只以 `![配图](url)` 链接形式存在，没有渲染为真实图片
2. **Seedream AI 模型未调用成功**：推测最后由 Picsum 兜底提供

## 根因分析

### 根因 1：Seedream API Key 配置错误（导致问题2）

**文件**：`D:\agent-write-article2\.env:54-56`

```
SEEDREAM_API_KEY=528a9a0d-3896-4b58-ab32-5ada91607621
SEEDREAM_ENDPOINT_ID=528a9a0d-3896-4b58-ab32-5ada91607621
```

两者值相同，都是 **Endpoint ID（推理端点 ID）**，而非 **API Key**。

火山引擎 ARK 的认证体系中：

- **API Key** = 以 `ak-` 开头的密钥字符串（用于 Bearer Token 认证）
- **Endpoint ID** = 推理端点 UUID（用于指定调用哪个模型）

代码 `seedream_service.py:251` 将 `SEEDREAM_API_KEY` 作为 Bearer Token 发送：

```python
headers = {"Authorization": f"Bearer {self.api_key}"}
```

由于传入的是 Endpoint ID 而非真正的 API Key → 认证失败 → 所有模型尝试都返回非 200 → `_real_generate` fallback 到 Picsum URL → 最终使用的是 Picsum 随机图而非 Seedream AI 生成图。

### 根因 2：前端 Create.vue 未在配图完成后更新 content（导致问题1）

完整数据流追踪：

1. 后端 `_generate_images_task()` 完成后，将 `mergedContent`（含 `![配图](cos_url)` Markdown）写入数据库的 `final_output` 和 `content` 字段
2. 前端 SSE 收到 `done` 事件时，`Create.vue:209` 调用 `setCompleted(articleId, finalOutput)`
3. 但 **SSE done 事件不携带 finalOutput 数据**！查看 `sse_manager.send_done()` 只传了 `article_id`
4. 因此前端的 `currentTask.finalOutput` 为空字符串，`currentTask.content` 仍然是配图前的纯文本正文
5. Create.vue 在完成阶段（Step 4）只显示 "文章创作完成" 的 a-result，**没有展示最终内容区域**
6. 用户点击 "查看文章" 跳转到 Result.vue，Result.vue 通过 `getArticle(articleId)` 从数据库获取数据 → 此时应该能看到带图片的内容

**但关键问题是**：如果用户说的 "和正文.md中类似的格式"，指的是 Result.vue 中 `renderMarkdown(final_output)` 将 `![配图](url)` 渲染出来——markdown-it 默认配置**确实能渲染图片为 `<img>` 标签**。所以如果 Result.vue 也显示为纯链接，可能原因有：

- COS 上传也失败了（因为 URL 是 picsum.photos 的外部链接），图片能正常显示
- 更可能是：**用户看到的是 Create.vue 阶段3（配图阶段）的 image-gallery 区域**，那里只显示缩略图列表；而正文预览区域（Stage 2）仍然显示的是配图前的旧 content，没有被更新为 mergedContent

### 总结：两个核心修复点

| 问题 | 根因 | 修复方式 |
| --- | --- | --- |
| Seedream 未调用 | .env 中 SEEDREAM_API_KEY 填成了 Endpoint ID | 需要**用户提供正确的 ak- 开头的 API Key** 并修改 .env |
| 图片以链接形式存在 | 前端未在配图完成后更新正文内容 + 可能缺少最终内容展示 | 修复 SSE done 事件传递 finalOutput + 确保前端正确渲染 |


## Tech Stack

- 后端：Python FastAPI + Pydantic
- 前端：Vue 3 + TypeScript + Pinia + Ant Design Vue + markdown-it
- 图片服务：火山引擎 ARK Seedream / Picsum 兜底
- 对象存储：腾讯云 COS

## Implementation Approach

### 修复策略

**问题 1 修复 — Seedream API Key 校验增强**
由于需要用户提供正确的 API Key（这是用户侧的凭证问题），我们在代码层面做以下增强：

1. `seedream_service.py` 增加 API Key 格式校验：检测到 UUID 格式（非 `ak-` 开头）时，记录明确的 WARNING 日志，提示用户检查配置
2. `.env` 文件中的注释增加更清晰的配置说明
3. 同时确保模型回退逻辑足够健壮

**问题 2 修复 — 前端配图完成后内容更新**
核心问题链路：

- SSE `IMAGE_ALL_COMPLETE` 事件已包含完整的 `results` 数组（含 url、source、status），但前端只用来更新 image gallery 缩略图
- SSE `done` 事件**不携带** finalOutput 内容
- Create.vue 完成阶段（Step 4）没有展示合并后的文章内容

修复方案：

1. **后端**：在 SSE `image_all_complete` 事件或 `done` 事件中附带 `mergedContent`（或至少让前端知道可以去拉取）
2. **前端 Create.vue**：

- 监听 `IMAGE_ALL_COMPLETE` 时，如果事件中有 mergedContent 则更新 store 的 content/finalOutput
- 或者在 Step 4（完成阶段）增加文章内容预览区域，从 store 中读取 finalOutput 或 content
- 确保 `renderMarkdown()` 能正确将 `![配图](cos_url)` 渲染为 `<img>` 标签（当前 markdown-it 配置已支持，但需确认 CSS 样式正确）

3. **前端 Result.vue**：确认 `renderMarkdown` 对图片的渲染正常（已有基础支持，需加 img 样式）

## Architecture Design

```
修复前数据流（断裂）：
后端 mergedContent → 写入DB → SSE done(仅articleId) → 前端 setCompleted(id) → finalOutput为空 → 显示旧content

修复后数据流（完整）：
后端 mergedContent → 写入DB 
  → SSE image_all_complete(含results) 
  → SSE done(携带mergedContent或触发前端拉取) 
  → 前端 updateContent(mergedContent) 
  → renderMarkdown 正确渲染 ![配图](url) 为 <img> 标签
```

## Directory Structure Summary

本实施涉及前后端共约 7 个文件的修改/确认：

```
D:\agent-write-article2\
├── .env                                    # [MODIFY] SEEDREAM_API_KEY 需用户提供正确值 + 增强注释
├── backend/
│   ├── app/config.py                       # [MODIFY] 增加 SEEDREAM_API_KEY 格式校验日志
│   ├── app/image/providers/
│   │   └── seedream_service.py             # [MODIFY] 增加 API Key 格式预警 + 更健壮的错误处理
│   └── app/utils/
│       └── sse_manager.py                  # [MODIFY] done/image_all_complete 事件增加 final_output 字段
├── frontend/src/
│   ├── views/Create.vue                    # [MODIFY] 完成 Step 展示最终内容 + IMAGE_ALL_COMPLETE 更新 content
│   ├── views/Result.vue                    # [MODIFY] 确保 markdown-content 中 img 样式正确
│   └── stores/task.ts                      # [MODIFY] add/updateContent 方法用于接收 mergedContent
```

本次设计主要针对现有页面的功能修复，不需要全新的 UI 设计，而是对 Create.vue 完成阶段和 Result.vue 内容展示区域的渲染优化。

## SubAgent

- **code-explorer**
- Purpose: 深度搜索 sse_manager.py 中 send_done 和 send_image_all_complete 方法的完整实现细节，以及前端 api/index.ts 中 ArticleResponse 类型定义
- Expected outcome: 精确了解 SSE 事件的 data payload 结构，确定在哪里添加 final_output 字段最合适