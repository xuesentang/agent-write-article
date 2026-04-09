/**
 * 任务状态管理 - Pinia Store
 * 管理文章创作的完整流程状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { TaskStatus, OutlineStructure, ImageInfo } from '@/api'

export interface TaskState {
  id: string
  topic: string
  style: string
  extraDescription?: string
  status: TaskStatus
  statusMessage: string
  progress: number

  // 标题阶段
  titles: string[]
  selectedTitle: string
  titleGenerating: boolean

  // 大纲阶段
  outline: OutlineStructure | null
  outlineGenerating: boolean
  outlineContent: string // 流式接收的大纲文本

  // 正文阶段
  content: string
  contentGenerating: boolean
  wordCount: number

  // 配图阶段
  images: ImageInfo[]
  imageGenerating: boolean
  imageProgress: { total: number; completed: number; current: string } | null

  // 最终结果
  articleId: string
  finalOutput: string
}

export const useTaskStore = defineStore('task', () => {
  // 当前任务
  const currentTask = ref<TaskState | null>(null)

  // SSE 连接状态
  const sseConnected = ref(false)
  const sseError = ref<string | null>(null)

  // 当前阶段 (0: 标题, 1: 大纲, 2: 正文, 3: 配图)
  const currentStage = computed(() => {
    if (!currentTask.value) return -1
    const status = currentTask.value.status

    if (status === 'CREATED' || status === 'TITLE_GENERATING') return 0
    if (status === 'TITLE_READY' || status === 'OUTLINE_GENERATING') return 1
    if (status === 'OUTLINE_READY' || status === 'CONTENT_GENERATING') return 2
    if (status === 'IMAGE_GENERATING') return 3
    if (status === 'COMPLETED') return 4
    if (status === 'FAILED') return -1
    return -1
  })

  // 阶段名称
  const stageNames = ['标题生成', '大纲生成', '正文创作', '配图生成', '完成']

  // 创建新任务
  function initTask(id: string, topic: string, style: string, extraDescription?: string) {
    currentTask.value = {
      id,
      topic,
      style,
      extraDescription,
      status: 'CREATED',
      statusMessage: '准备开始',
      progress: 0,
      titles: [],
      selectedTitle: '',
      titleGenerating: false,
      outline: null,
      outlineGenerating: false,
      outlineContent: '',
      content: '',
      contentGenerating: false,
      wordCount: 0,
      images: [],
      imageGenerating: false,
      imageProgress: null,
      articleId: '',
      finalOutput: '',
    }
    sseError.value = null
  }

  // 更新任务状态
  function updateStatus(status: TaskStatus, message: string, progress?: number) {
    if (currentTask.value) {
      currentTask.value.status = status
      currentTask.value.statusMessage = message
      if (progress !== undefined) {
        currentTask.value.progress = progress
      }
    }
  }

  // 设置标题方案
  function setTitles(titles: string[]) {
    if (currentTask.value) {
      currentTask.value.titles = titles
      currentTask.value.titleGenerating = false
    }
  }

  // 添加标题片段 (流式)
  function appendTitleChunk(_chunk: string) {
    // 流式标题生成时，暂时存储到临时变量
    if (currentTask.value) {
      currentTask.value.titleGenerating = true
      // 可以在这里处理流式标题内容
    }
  }

  // 选择标题
  function selectTitle(title: string) {
    if (currentTask.value) {
      currentTask.value.selectedTitle = title
    }
  }

  // 设置大纲
  function setOutline(outline: OutlineStructure) {
    if (currentTask.value) {
      currentTask.value.outline = outline
      currentTask.value.outlineGenerating = false
      currentTask.value.outlineContent = ''
    }
  }

  // 添加大纲片段 (流式)
  function appendOutlineChunk(chunk: string) {
    if (currentTask.value) {
      currentTask.value.outlineGenerating = true
      currentTask.value.outlineContent += chunk
    }
  }

  // 设置正文
  function setContent(content: string, wordCount: number) {
    if (currentTask.value) {
      currentTask.value.content = content
      currentTask.value.wordCount = wordCount
      currentTask.value.contentGenerating = false
    }
  }

  // 添加正文片段 (流式)
  function appendContentChunk(_chunk: string) {
    if (currentTask.value) {
      currentTask.value.contentGenerating = true
    }
  }

  // 设置配图进度
  function setImageProgress(data: { total: number; completed: number; current: string } | null) {
    if (currentTask.value) {
      currentTask.value.imageGenerating = data !== null
      currentTask.value.imageProgress = data
    }
  }

  // 添加单张配图
  function addImage(image: ImageInfo) {
    if (currentTask.value) {
      currentTask.value.images.push(image)
    }
  }

  // 设置所有配图
  function setImages(images: ImageInfo[]) {
    if (currentTask.value) {
      currentTask.value.images = images
      currentTask.value.imageGenerating = false
      currentTask.value.imageProgress = null
    }
  }

  // 设置完成状态
  function setCompleted(articleId: string, finalOutput?: string) {
    if (currentTask.value) {
      currentTask.value.status = 'COMPLETED'
      currentTask.value.statusMessage = '文章生成完成'
      currentTask.value.progress = 100
      currentTask.value.articleId = articleId
      if (finalOutput) {
        currentTask.value.finalOutput = finalOutput
      }
      currentTask.value.contentGenerating = false
      currentTask.value.imageGenerating = false
    }
  }

  // 设置错误
  function setError(message: string) {
    if (currentTask.value) {
      currentTask.value.status = 'FAILED'
      currentTask.value.statusMessage = message
    }
    sseError.value = message
  }

  // 设置 SSE 连接状态
  function setSSEConnected(connected: boolean) {
    sseConnected.value = connected
  }

  // 重置任务
  function resetTask() {
    currentTask.value = null
    sseConnected.value = false
    sseError.value = null
  }

  return {
    currentTask,
    sseConnected,
    sseError,
    currentStage,
    stageNames,

    initTask,
    updateStatus,
    setTitles,
    appendTitleChunk,
    selectTitle,
    setOutline,
    appendOutlineChunk,
    setContent,
    appendContentChunk,
    setImageProgress,
    addImage,
    setImages,
    setCompleted,
    setError,
    setSSEConnected,
    resetTask,
  }
})