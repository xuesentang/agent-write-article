<script setup lang="ts">
/**
 * 文章创作页面 - 核心工作流
 * 四阶段流程: 标题生成 → 大纲生成 → 正文创作 → 配图生成
 * 使用 SSE 实现实时流式输出
 */
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  BulbOutlined,
  EditOutlined,
  FileTextOutlined,
  PictureOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ReloadOutlined,
  SendOutlined,
} from '@ant-design/icons-vue'
import MarkdownIt from 'markdown-it'

import { useTaskStore } from '@/stores/task'
import { useSSE, SSEEventType, ConnectionState } from '@/composables/useSSE'
import {
  createTask,
  generateTitles,
  selectTitle as apiSelectTitle,
  generateOutline,
  confirmOutline,
  type OutlineSection,
} from '@/api'

// ============ 初始化 ============

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

// Markdown 渲染器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
})

// ============ 状态 ============

// 获取 URL 参数
const topicFromQuery = ref((route.query.topic as string) || '')
const styleFromQuery = ref((route.query.style as string) || '专业')

// 目标字数
const targetLength = ref(2000)

// 当前阶段 (0-3)
const currentStep = computed(() => taskStore.currentStage)

// 阶段配置 - 使用渲染函数
const steps = [
  { title: '标题生成', renderIcon: () => h(BulbOutlined), description: 'AI 生成多个爆款标题方案' },
  { title: '大纲生成', renderIcon: () => h(EditOutlined), description: '根据标题生成结构化大纲' },
  { title: '正文创作', renderIcon: () => h(FileTextOutlined), description: '流式输出文章正文' },
  { title: '配图生成', renderIcon: () => h(PictureOutlined), description: '并行生成文章配图' },
]

// SSE 客户端
const sseUrl = computed(() => taskStore.currentTask ? `/api/sse/connect/${taskStore.currentTask.id}` : '')
const {
  connectionState,
  connect: connectSSE,
  disconnect: disconnectSSE,
  on: onSSEEvent,
} = useSSE(() => sseUrl.value, {
  maxReconnectAttempts: 3,
  reconnectDelay: 1000,
})

// 各阶段的交互状态
const titleSelection = ref<number | null>(null) // 选中的标题索引
const userModification = ref('') // 用户的大纲修改建议
const isOptimizing = ref(false) // 是否正在优化大纲

// ============ SSE 事件处理 ============

function setupSSEHandlers() {
  // 状态变更
  onSSEEvent(SSEEventType.STATUS, (data) => {
    taskStore.updateStatus(data.data.status, data.data.message, data.progress)
  })

  // 标题生成
  onSSEEvent(SSEEventType.TITLE_CHUNK, (_data) => {
    // 可以在这里处理流式标题片段
  })

  onSSEEvent(SSEEventType.TITLE_COMPLETE, (data) => {
    taskStore.setTitles(data.data.titles)
    message.success('标题生成完成，请选择一个标题')
  })

  // 大纲生成
  onSSEEvent(SSEEventType.OUTLINE_CHUNK, (data) => {
    taskStore.appendOutlineChunk(data.data.content || '')
  })

  onSSEEvent(SSEEventType.OUTLINE_COMPLETE, (data) => {
    taskStore.setOutline(data.data.outline)
    message.success('大纲生成完成')
  })

  // 正文生成
  onSSEEvent(SSEEventType.CONTENT_CHUNK, (data) => {
    taskStore.appendContentChunk(data.data.content || '')
  })

  onSSEEvent(SSEEventType.CONTENT_COMPLETE, (data) => {
    taskStore.setContent(taskStore.currentTask?.content || '', data.data.word_count)
    message.success('正文创作完成')
  })

  // 配图生成
  onSSEEvent(SSEEventType.IMAGE_TASK_START, (data) => {
    taskStore.setImageProgress({
      total: data.data.total_image_tasks,
      completed: 0,
      current: '',
    })
  })

  onSSEEvent(SSEEventType.IMAGE_PROGRESS, (data) => {
    const progress = taskStore.currentTask?.imageProgress
    if (progress) {
      taskStore.setImageProgress({
        ...progress,
        current: data.data.position,
      })
    }
  })

  onSSEEvent(SSEEventType.IMAGE_COMPLETE, (data) => {
    taskStore.addImage(data.data)
    const progress = taskStore.currentTask?.imageProgress
    if (progress) {
      taskStore.setImageProgress({
        ...progress,
        completed: progress.completed + 1,
        current: data.data.position,
      })
    }
  })

  onSSEEvent(SSEEventType.IMAGE_ALL_COMPLETE, () => {
    taskStore.setImageProgress(null)
    message.success('配图生成完成')
  })

  // 进度更新
  onSSEEvent(SSEEventType.PROGRESS, (data) => {
    if (taskStore.currentTask) {
      taskStore.currentTask.progress = data.progress
    }
  })

  // 错误
  onSSEEvent(SSEEventType.ERROR, (data) => {
    taskStore.setError(data.data.message || '生成过程中发生错误')
    message.error(data.data.message || '生成失败')
  })

  // 完成
  onSSEEvent(SSEEventType.DONE, (data) => {
    taskStore.setCompleted(data.data.article_id)
    message.success('文章生成完成！')
  })
}

// ============ 工作流操作 ============

// 开始创作
async function startCreation() {
  if (!topicFromQuery.value.trim()) {
    message.warning('请输入选题描述')
    return
  }

  try {
    // 创建任务
    const res = await createTask({
      topic: topicFromQuery.value,
      style: styleFromQuery.value,
      extra_description: '',
    })

    taskStore.initTask(
      res.data.id,
      res.data.topic,
      res.data.style,
      res.data.extra_description
    )

    // 建立 SSE 连接
    await connectSSE()
    taskStore.setSSEConnected(true)

    // 触发标题生成
    await generateTitles(res.data.id)

    message.success('任务创建成功，正在生成标题...')
  } catch (error: any) {
    message.error(error.message || '创建任务失败')
    console.error('创建任务失败:', error)
  }
}

// 选择标题
async function handleSelectTitle() {
  if (titleSelection.value === null || !taskStore.currentTask) {
    message.warning('请选择一个标题')
    return
  }

  const selectedTitle = taskStore.currentTask.titles[titleSelection.value]

  try {
    await apiSelectTitle(taskStore.currentTask.id, { selected_title: selectedTitle })
    taskStore.selectTitle(selectedTitle)
    message.success('标题选择成功，正在生成大纲...')

    // 触发大纲生成
    await generateOutline(taskStore.currentTask.id, { target_length: targetLength.value })
  } catch (error: any) {
    message.error(error.message || '选择标题失败')
  }
}

// 优化大纲
async function handleOptimizeOutline() {
  if (!userModification.value.trim() || !taskStore.currentTask) {
    message.warning('请输入修改建议')
    return
  }

  isOptimizing.value = true
  try {
    // 这里需要调用优化大纲的 API
    // await optimizeOutline(taskStore.currentTask.id, { user_modifications: userModification.value })
    message.success('大纲优化中...')
  } catch (error: any) {
    message.error(error.message || '优化大纲失败')
  } finally {
    isOptimizing.value = false
  }
}

// 确认大纲，开始正文生成
async function handleConfirmOutline() {
  if (!taskStore.currentTask) return

  try {
    await confirmOutline(taskStore.currentTask.id)
    message.success('大纲确认成功，正在创作正文...')
  } catch (error: any) {
    message.error(error.message || '确认大纲失败')
  }
}

// 查看结果
function viewResult() {
  if (taskStore.currentTask?.articleId) {
    router.push({ name: 'result', params: { id: taskStore.currentTask.articleId } })
  }
}

// 重新开始
function restart() {
  disconnectSSE()
  taskStore.resetTask()
  router.push({ name: 'home' })
}

// ============ 辅助方法 ============

// 渲染 Markdown
function renderMarkdown(content: string): string {
  return md.render(content)
}

// 获取阶段状态
function getStepStatus(stepIndex: number): 'wait' | 'process' | 'finish' | 'error' {
  if (!taskStore.currentTask) return 'wait'
  if (taskStore.currentTask.status === 'FAILED') return 'error'

  if (stepIndex < currentStep.value) return 'finish'
  if (stepIndex === currentStep.value) return 'process'
  return 'wait'
}

// 获取连接状态颜色
function getConnectionColor(): string {
  switch (connectionState.value) {
    case ConnectionState.CONNECTED: return 'green'
    case ConnectionState.CONNECTING: return 'blue'
    case ConnectionState.ERROR: return 'red'
    default: return 'default'
  }
}

// 大纲渲染
function renderOutlineSections(sections: OutlineSection[], level = 1): string {
  let html = ''
  for (const section of sections) {
    const margin = (level - 1) * 20
    html += `<div class="outline-item level-${level}" style="margin-left: ${margin}px">
      <span class="outline-title">${section.title}</span>
      ${section.key_points?.length ? `<ul class="outline-points">${section.key_points.map(p => `<li>${p}</li>`).join('')}</ul>` : ''}
    </div>`
    if (section.subsections?.length) {
      html += renderOutlineSections(section.subsections, level + 1)
    }
  }
  return html
}

// ============ 生命周期 ============

onMounted(() => {
  setupSSEHandlers()
})

onUnmounted(() => {
  disconnectSSE()
})
</script>

<template>
  <div class="create-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <EditOutlined class="title-icon" />
        创作文章
      </h1>
      <p class="page-subtitle">AI 多智能体协作，四步完成爆款文章创作</p>
    </div>

    <!-- 未开始状态：显示选题输入 -->
    <div v-if="!taskStore.currentTask" class="start-section fade-in">
      <a-card class="start-card glass-card">
        <a-form layout="vertical" class="start-form">
          <a-form-item label="选题描述" required>
            <a-textarea
              v-model:value="topicFromQuery"
              placeholder="请输入您的选题想法，例如：如何在30天内打造爆款自媒体账号"
              :rows="4"
              :maxlength="500"
              show-count
            />
          </a-form-item>

          <a-form-item label="文章风格">
            <a-select v-model:value="styleFromQuery" style="width: 200px">
              <a-select-option value="专业">专业</a-select-option>
              <a-select-option value="轻松">轻松</a-select-option>
              <a-select-option value="幽默">幽默</a-select-option>
              <a-select-option value="深度">深度</a-select-option>
              <a-select-option value="热点">热点</a-select-option>
              <a-select-option value="教程">教程</a-select-option>
            </a-select>
          </a-form-item>

          <a-form-item label="目标字数">
            <a-input-number v-model:value="targetLength" :min="500" :max="10000" :step="500" style="width: 200px" />
            <span class="input-hint">建议 2000-5000 字</span>
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              size="large"
              block
              @click="startCreation"
              :disabled="!topicFromQuery.trim()"
            >
              <template #icon><BulbOutlined /></template>
              开始创作
            </a-button>
          </a-form-item>
        </a-form>
      </a-card>
    </div>

    <!-- 已开始状态：显示工作流 -->
    <div v-else class="workflow-section">
      <!-- 进度指示器 -->
      <div class="steps-container glass-card">
        <a-steps :current="currentStep" status="process">
          <a-step
            v-for="(step, index) in steps"
            :key="index"
            :title="step.title"
            :description="step.description"
            :status="getStepStatus(index)"
          >
            <template #icon>
              <component :is="step.renderIcon" />
            </template>
          </a-step>
        </a-steps>

        <!-- 状态信息 -->
        <div class="status-bar">
          <div class="status-left">
            <a-tag :color="getConnectionColor()">
              {{ connectionState === ConnectionState.CONNECTED ? '已连接' : connectionState }}
            </a-tag>
            <span class="status-message">{{ taskStore.currentTask.statusMessage }}</span>
          </div>
          <div class="status-right">
            <a-progress
              :percent="taskStore.currentTask.progress"
              :status="taskStore.currentTask.status === 'FAILED' ? 'exception' : undefined"
              style="width: 200px"
            />
          </div>
        </div>
      </div>

      <!-- 阶段 0: 标题生成 -->
      <div v-if="currentStep === 0" class="stage-section fade-in">
        <a-card title="标题方案" class="stage-card">
          <template #extra>
            <a-tag v-if="taskStore.currentTask.titleGenerating" color="processing">
              <LoadingOutlined /> 生成中...
            </a-tag>
          </template>

          <div v-if="taskStore.currentTask.titleGenerating && !taskStore.currentTask.titles.length" class="loading-state">
            <a-spin size="large" />
            <p>AI 正在为您生成爆款标题方案...</p>
          </div>

          <div v-else-if="taskStore.currentTask.titles.length" class="titles-list">
            <div class="select-hint">请选择一个最满意的标题：</div>
            <div
              v-for="(title, index) in taskStore.currentTask.titles"
              :key="index"
              class="title-item cursor-pointer"
              :class="{ selected: titleSelection === index }"
              @click="titleSelection = index"
            >
              <div class="title-index">{{ index + 1 }}</div>
              <div class="title-content">{{ title }}</div>
              <CheckCircleOutlined v-if="titleSelection === index" class="check-icon" />
            </div>

            <div class="action-bar">
              <a-button type="primary" size="large" @click="handleSelectTitle" :disabled="titleSelection === null">
                <template #icon><SendOutlined /></template>
                选择此标题，继续下一步
              </a-button>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>等待标题生成...</p>
          </div>
        </a-card>
      </div>

      <!-- 阶段 1: 大纲生成 -->
      <div v-else-if="currentStep === 1" class="stage-section fade-in">
        <a-card title="文章大纲" class="stage-card">
          <template #extra>
            <a-space>
              <a-tag v-if="taskStore.currentTask.outlineGenerating" color="processing">
                <LoadingOutlined /> 生成中...
              </a-tag>
            </a-space>
          </template>

          <div v-if="taskStore.currentTask.outlineGenerating && !taskStore.currentTask.outline" class="loading-state">
            <a-spin size="large" />
            <p>AI 正在构建文章结构大纲...</p>
            <div v-if="taskStore.currentTask.outlineContent" class="stream-preview">
              <pre>{{ taskStore.currentTask.outlineContent }}</pre>
            </div>
          </div>

          <div v-else-if="taskStore.currentTask.outline" class="outline-section">
            <div class="outline-header">
              <h3 class="outline-title-main">{{ taskStore.currentTask.selectedTitle }}</h3>
            </div>

            <div class="outline-tree">
              <div
                v-html="renderOutlineSections(taskStore.currentTask.outline.sections)"
                class="outline-content"
              />
            </div>

            <!-- 修改建议 -->
            <div class="modification-section">
              <a-divider>修改建议</a-divider>
              <a-textarea
                v-model:value="userModification"
                placeholder="如需调整大纲，请输入您的修改建议（可选）"
                :rows="3"
                :maxlength="500"
              />
              <div class="mod-actions">
                <a-button @click="handleOptimizeOutline" :loading="isOptimizing" :disabled="!userModification.trim()">
                  <template #icon><ReloadOutlined /></template>
                  AI 优化大纲
                </a-button>
              </div>
            </div>

            <div class="action-bar">
              <a-button type="primary" size="large" @click="handleConfirmOutline">
                <template #icon><SendOutlined /></template>
                确认大纲，开始创作正文
              </a-button>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>等待大纲生成...</p>
          </div>
        </a-card>
      </div>

      <!-- 阶段 2: 正文创作 -->
      <div v-else-if="currentStep === 2" class="stage-section fade-in">
        <a-card title="正文内容" class="stage-card">
          <template #extra>
            <a-space>
              <a-tag v-if="taskStore.currentTask.contentGenerating" color="processing">
                <LoadingOutlined /> 写作中...
              </a-tag>
              <a-tag v-else color="success">
                <CheckCircleOutlined /> 完成
              </a-tag>
              <span v-if="taskStore.currentTask.wordCount" class="word-count">
                {{ taskStore.currentTask.wordCount }} 字
              </span>
            </a-space>
          </template>

          <div class="content-preview">
            <div
              class="stream-output"
              :class="{ generating: taskStore.currentTask.contentGenerating }"
            >
              <div
                v-if="taskStore.currentTask.content"
                v-html="renderMarkdown(taskStore.currentTask.content)"
                class="markdown-content"
              />
              <span v-if="taskStore.currentTask.contentGenerating" class="cursor-blink" />
            </div>
          </div>
        </a-card>
      </div>

      <!-- 阶段 3: 配图生成 -->
      <div v-else-if="currentStep === 3" class="stage-section fade-in">
        <a-card title="配图生成" class="stage-card">
          <template #extra>
            <a-tag v-if="taskStore.currentTask.imageGenerating" color="processing">
              <LoadingOutlined /> 生成中...
            </a-tag>
          </template>

          <div v-if="taskStore.currentTask.imageProgress" class="image-progress">
            <a-progress
              :percent="Math.round((taskStore.currentTask.imageProgress.completed / taskStore.currentTask.imageProgress.total) * 100)"
              :format="() => `${taskStore.currentTask?.imageProgress?.completed || 0} / ${taskStore.currentTask?.imageProgress?.total || 0}`"
            />
            <p class="progress-text">正在处理: {{ taskStore.currentTask.imageProgress.current }}</p>
          </div>

          <div v-if="taskStore.currentTask.images.length" class="image-gallery">
            <div
              v-for="(img, index) in taskStore.currentTask.images"
              :key="index"
              class="image-item"
            >
              <img :src="img.url" :alt="img.position" />
              <div class="image-info">
                <span class="position">{{ img.position }}</span>
                <span class="source">{{ img.source }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="!taskStore.currentTask.imageGenerating" class="empty-state">
            <p>等待配图生成...</p>
          </div>
        </a-card>
      </div>

      <!-- 阶段 4: 完成 -->
      <div v-else-if="currentStep === 4" class="stage-section fade-in">
        <a-result
          status="success"
          title="文章创作完成！"
          sub-title="AI 已完成所有创作流程，您可以查看完整文章或重新开始"
        >
          <template #extra>
            <a-space>
              <a-button type="primary" size="large" @click="viewResult">
                <template #icon><FileTextOutlined /></template>
                查看文章
              </a-button>
              <a-button size="large" @click="restart">
                <template #icon><ReloadOutlined /></template>
                重新开始
              </a-button>
            </a-space>
          </template>
        </a-result>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="taskStore.currentTask.status === 'FAILED'" class="stage-section fade-in">
        <a-result
          status="error"
          title="生成失败"
          :sub-title="taskStore.currentTask.statusMessage"
        >
          <template #extra>
            <a-space>
              <a-button type="primary" @click="restart">重新开始</a-button>
            </a-space>
          </template>
        </a-result>
      </div>

      <!-- 操作栏 -->
      <div v-if="taskStore.currentTask && currentStep >= 0 && currentStep < 4" class="action-footer">
        <a-button @click="restart">取消并返回</a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-page {
  padding: 0;
}

/* 页面标题 */
.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.title-icon {
  margin-right: 12px;
  color: var(--primary-color);
}

.page-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
}

/* 开始区域 */
.start-section {
  max-width: 700px;
  margin: 0 auto;
}

.start-card {
  padding: 24px;
}

.start-form {
  max-width: 500px;
  margin: 0 auto;
}

.input-hint {
  margin-left: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

/* 工作流区域 */
.workflow-section {
  max-width: 900px;
  margin: 0 auto;
}

/* 步骤容器 */
.steps-container {
  padding: 24px;
  margin-bottom: 24px;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}

.status-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-message {
  color: var(--text-secondary);
}

/* 阶段卡片 */
.stage-section {
  margin-bottom: 24px;
}

.stage-card {
  min-height: 300px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--text-secondary);
}

.loading-state p {
  margin-top: 16px;
  font-size: 15px;
}

.stream-preview {
  margin-top: 24px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  width: 100%;
  max-height: 200px;
  overflow: auto;
}

.stream-preview pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  color: var(--text-secondary);
}

/* 空状态 */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--text-muted);
}

/* 标题列表 */
.titles-list {
  padding: 16px 0;
}

.select-hint {
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.title-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  margin-bottom: 12px;
  background: var(--bg-color);
  border: 2px solid transparent;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.title-item:hover {
  background: #F0F9FF;
  border-color: var(--primary-light);
}

.title-item.selected {
  background: rgba(8, 145, 178, 0.05);
  border-color: var(--primary-color);
}

.title-index {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  font-weight: 600;
  font-size: 14px;
}

.title-content {
  flex: 1;
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-primary);
}

.check-icon {
  flex-shrink: 0;
  font-size: 20px;
  color: var(--cta-color);
}

/* 操作栏 */
.action-bar {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
  text-align: center;
}

/* 大纲区域 */
.outline-section {
  padding: 16px 0;
}

.outline-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--primary-light);
}

.outline-title-main {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.outline-tree {
  padding: 20px;
  background: #F8FAFC;
  border-radius: 12px;
  margin-bottom: 24px;
}

.outline-content :deep(.outline-item) {
  padding: 12px 16px;
  margin: 8px 0;
  background: white;
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.outline-content :deep(.outline-item.level-1) {
  font-weight: 600;
  font-size: 15px;
}

.outline-content :deep(.outline-item.level-2) {
  font-weight: 500;
  font-size: 14px;
}

.outline-content :deep(.outline-item.level-3) {
  font-size: 14px;
}

.outline-content :deep(.outline-points) {
  margin: 8px 0 0 16px;
  padding: 0;
  list-style: disc;
}

.outline-content :deep(.outline-points li) {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 4px 0;
}

/* 修改建议区域 */
.modification-section {
  margin: 24px 0;
}

.mod-actions {
  margin-top: 12px;
  text-align: right;
}

/* 内容预览 */
.content-preview {
  padding: 16px 0;
}

.stream-output {
  min-height: 300px;
  max-height: 600px;
  overflow-y: auto;
}

/* 配图进度 */
.image-progress {
  padding: 24px;
  text-align: center;
  background: #F8FAFC;
  border-radius: 12px;
  margin-bottom: 24px;
}

.progress-text {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* 图片画廊 */
.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.image-item {
  border-radius: 12px;
  overflow: hidden;
  background: white;
  border: 1px solid var(--border-light);
  transition: all 0.2s ease;
}

.image-item:hover {
  box-shadow: var(--shadow-md);
}

.image-item img {
  width: 100%;
  aspect-ratio: 16/10;
  object-fit: cover;
}

.image-info {
  padding: 12px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}

/* 字数统计 */
.word-count {
  font-size: 14px;
  color: var(--text-secondary);
  margin-left: 8px;
}

/* 操作栏 */
.action-footer {
  text-align: center;
  padding: 24px;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }

  .steps-container {
    padding: 16px;
  }

  .status-bar {
    flex-direction: column;
    gap: 12px;
  }

  .title-item {
    padding: 12px;
  }

  .title-content {
    font-size: 14px;
  }

  .image-gallery {
    grid-template-columns: 1fr;
  }
}
</style>