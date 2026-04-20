# Seedream 配图服务无法调用问题分析与修复计划

## 问题概述

**现象**：用户测试运行几次配图功能时，发现 Seedream 模型都没有成功调用，都是使用了 Picsum 策略进行兜底，导致图片质量很低。

**调查日期**：2026-04-15

---

## 一、问题根源分析

### 1.1 主要问题：后端配置缺失和错误

经过代码审查，发现以下配置问题：

#### 问题 1：后端 `.env` 文件中缺少 `SEEDREAM_ENDPOINT_ID` 配置

**文件位置**：`backend/.env`

**当前配置**：
```env
SEEDREAM_API_KEY=528a9a0d-3896-4b58-ab32-5ada91607621
SEEDREAM_BASE_URL=https://api.seedream.ai/v1
```

**缺失配置**：
- `SEEDREAM_ENDPOINT_ID=ep-20260410201140-sfnn9` （此配置存在于根目录 `.env` 中）

**影响**：
- 代码在 `seedream_service.py` 第 277-278 行会检查是否有 `endpoint_id`：
  ```python
  if self.endpoint_id:
      model_names_to_try.append(self.endpoint_id)
  ```
- 缺少此配置会导致无法使用推理端点 ID 进行调用，只能尝试通用模型名称

#### 问题 2：`SEEDREAM_BASE_URL` 配置可能不正确

**当前后端配置**：
```
SEEDREAM_BASE_URL=https://api.seedream.ai/v1
```

**根目录正确配置**：
```
SEEDREAM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

**代码注释说明**（`seedream_service.py` 第 228-242 行）：
```python
"""
火山引擎 ARK API 图像生成格式（类似 OpenAI）：
POST /images/generations
{
    "model": "Doubao-Seedream-5.0-lite",
    "prompt": "描述",
    "size": "1024x1024"
}

或者使用推理端点：
POST /images/generations
{
    "model": "endpoint-id",  # 用户配置的 API Key 可能是端点 ID
    "prompt": "描述",
    "size": "1024x1024"
}
"""
```

**分析**：
- 根据代码注释，Seedream 服务实际调用的是火山引擎 ARK API
- 正确的 BASE_URL 应该是 `https://ark.cn-beijing.volces.com/api/v3`
- 当前的 `https://api.seedream.ai/v1` 可能是错误的端点地址

### 1.2 次要问题：代码降级逻辑设计

**文件位置**：`backend/app/image/providers/seedream_service.py` 第 352-365 行

**当前代码**：
```python
# 所有尝试都失败，返回 Mock URL 作为备用
# 这样可以确保流程不中断
mock_url = f"https://picsum.photos/seed/{hash(prompt) % 10000}/{width}/{height}"
logger.error(...)
return mock_url
```

**问题分析**：
- 当 Seedream API 调用全部失败时，代码返回的是 Picsum 的 URL
- 这个 URL 会被 `fetch_image` 方法返回，但标记为失败（`success=False`）
- `ImageGeneratorAgent` 检测到失败后会继续尝试其他服务，最终使用 Picsum 兜底
- 这种设计确保了流程不中断，但也掩盖了实际的 API 调用失败问题

### 1.3 调用流程分析

**完整调用链**：
```
1. 前端调用 POST /api/tasks/{task_id}/start-image-analysis
   ↓
2. 后端 task.py 的 _generate_images_task 函数
   ↓
3. 创建 ImageAnalyzerAgent 解析占位符
   ↓
4. 创建 ImageGeneratorAgent (use_mock=false，因为前端没传参数)
   ↓
5. ImageGeneratorAgent 调用 Seedream 服务的 fetch_image 方法
   ↓
6. SeedreamService._real_generate 尝试 API 调用
   ↓
7. API 调用失败（配置错误）
   ↓
8. 返回 Picsum URL
   ↓
9. ImageGeneratorAgent 检测到 success=False，尝试其他服务
   ↓
10. 最终使用 Picsum 兜底
```

---

## 二、修复计划

### 2.1 优先级 1：修复后端 `.env` 配置

**修改文件**：`backend/.env`

**需要修改的配置**：

```env
# 修改前
SEEDREAM_API_KEY=528a9a0d-3896-4b58-ab32-5ada91607621
SEEDREAM_BASE_URL=https://api.seedream.ai/v1

# 修改后
SEEDREAM_API_KEY=528a9a0d-3896-4b58-ab32-5ada91607621
SEEDREAM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDREAM_ENDPOINT_ID=ep-20260410201140-sfnn9
```

**修改说明**：
1. 添加缺失的 `SEEDREAM_ENDPOINT_ID` 配置
2. 修正 `SEEDREAM_BASE_URL` 为正确的火山引擎 ARK API 地址

### 2.2 优先级 2：增强错误日志输出

**修改文件**：`backend/app/image/providers/seedream_service.py`

**修改位置**：第 352-365 行

**修改目的**：更清晰地记录失败原因，便于调试

**建议修改**：
```python
# 所有尝试都失败，返回 Picsum URL 作为备用
mock_url = f"https://picsum.photos/seed/{hash(prompt) % 10000}/{width}/{height}"
logger.error(
    f"[SeedreamService] ===== 所有模型尝试均失败，使用 Picsum 备用 URL =====\n"
    f"  尝试的模型数: {len(model_names_to_try)}\n"
    f"  API 地址: {generate_url}\n"
    f"  请检查:\n"
    f"    1. API Key 是否正确（当前 key 前位: {self.api_key[:8] if len(self.api_key) > 8 else self.api_key}...）\n"
    f"    2. 推理端点 {self.endpoint_id} 是否已部署并处于运行状态\n"
    f"    3. 端点绑定的模型 ID 是否在尝试列表中\n"
    f"    4. BASE_URL 是否正确（当前: {self.base_url}）\n"
    f"  备用 URL: {mock_url}"
)
return mock_url
```

### 2.3 优先级 3：添加配置验证和健康检查（可选优化）

**目的**：在服务启动时验证 Seedream 配置的有效性

**建议添加**：
```python
# 在 SeedreamService.__init__ 中添加
if self.endpoint_id:
    logger.info(f"[SeedreamService] 检测到推理端点 ID: {self.endpoint_id}")
else:
    logger.warning(
        f"[SeedreamService] 未配置推理端点 ID (SEEDREAM_ENDPOINT_ID)，"
        f"将尝试使用通用模型名称"
    )

# 验证 BASE_URL 格式
if not self.base_url.endswith('/api/v3'):
    logger.warning(
        f"[SeedreamService] BASE_URL 格式可能不正确: {self.base_url}，"
        f"火山引擎 ARK API 通常以 /api/v3 结尾"
    )
```

---

## 三、验证计划

### 3.1 配置修复后的验证步骤

1. **修改 `backend/.env` 文件**
   - 更新 `SEEDREAM_BASE_URL`
   - 添加 `SEEDREAM_ENDPOINT_ID`

2. **重启后端服务**
   ```bash
   cd backend
   # 停止当前服务
   # 重新启动
   uvicorn app.main:app --reload --port 8000
   ```

3. **检查启动日志**
   - 确认 Seedream 服务初始化成功
   - 确认配置被正确读取

4. **进行配图测试**
   - 创建新任务并生成配图
   - 观察 SSE 推送的图片来源
   - 检查是否使用了 Seedream 而非 Picsum

### 3.2 预期结果

**成功标志**：
- 日志中出现 `[SeedreamService] 生成成功: model=xxx, url=xxx`
- SSE 事件中 `source` 字段显示为 `seedream`
- 生成的图片与正文内容语义相关（而非随机图片）

**失败标志**：
- 日志中出现 `[SeedreamService] 所有模型尝试均失败`
- 最终使用的图片来源是 `picsum`

### 3.3 如果配置修复后仍然失败

可能的原因：
1. **API Key 无效或已过期**
2. **推理端点未部署或已停止**
3. **网络连接问题（防火墙/代理）**
4. **火山引擎 ARK API 接口变更**

进一步排查：
1. 使用 curl 或 Postman 直接测试 API
2. 检查火山引擎控制台的端点状态
3. 查看完整的错误响应内容

---

## 四、代码修改清单

| 文件路径 | 修改类型 | 修改内容 |
|---------|---------|---------|
| `backend/.env` | 修改配置 | 修改 SEEDREAM_BASE_URL，添加 SEEDREAM_ENDPOINT_ID |
| `backend/app/image/providers/seedream_service.py` | 增强日志 | 在失败日志中添加 BASE_URL 信息 |

---

## 五、风险提示

1. **配置修改需重启服务**：修改 `.env` 文件后必须重启后端服务才能生效
2. **API Key 安全**：确保 `.env` 文件不被提交到版本控制系统
3. **火山引擎费用**：Seedream 是付费服务，确保账户有足够余额
4. **网络环境**：如果服务器在中国大陆，访问火山引擎 API 通常没有问题，但需检查防火墙设置

---

## 六、总结

**核心问题**：后端 `backend/.env` 文件中 Seedream 配置不完整且错误
- 缺少 `SEEDREAM_ENDPOINT_ID` 配置
- `SEEDREAM_BASE_URL` 配置为错误的地址

**解决方案**：修改 `backend/.env` 文件，添加正确的配置

**优先级**：高（配置修复是解决问题的唯一途径，代码层面的改动是辅助调试）

**预计工作量**：5 分钟（修改配置 + 重启服务）
