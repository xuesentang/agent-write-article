/**
 * 任务状态管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export type TaskStatus =
  | 'CREATED'
  | 'TITLE_GENERATING'
  | 'TITLE_READY'
  | 'OUTLINE_GENERATING'
  | 'OUTLINE_READY'
  | 'CONTENT_GENERATING'
  | 'IMAGE_GENERATING'
  | 'COMPLETED'
  | 'FAILED'

export interface TaskState {
  id: string
  topic: string
  style: string
  status: TaskStatus
  statusMessage: string
  titles: string[]
  selectedTitle: string
  outline: any
  content: string
  images: any[]
  progress: number
}

export const useTaskStore = defineStore('task', () => {
  const currentTask = ref<TaskState | null>(null)
  const partialContent = ref('')

  // 创建新任务
  function createTask(topic: string, style: string) {
    currentTask.value = {
      id: '',
      topic,
      style,
      status: 'CREATED',
      statusMessage: '准备开始',
      titles: [],
      selectedTitle: '',
      outline: null,
      content: '',
      images: [],
      progress: 0,
    }
  }

  // 更新任务状态
  function updateStatus(status: TaskStatus, message: string) {
    if (currentTask.value) {
      currentTask.value.status = status
      currentTask.value.statusMessage = message
    }
  }

  // 设置标题方案
  function setTitles(titles: string[]) {
    if (currentTask.value) {
      currentTask.value.titles = titles
    }
  }

  // 选择标题
  function selectTitle(title: string) {
    if (currentTask.value) {
      currentTask.value.selectedTitle = title
    }
  }

  // 设置大纲
  function setOutline(outline: any) {
    if (currentTask.value) {
      currentTask.value.outline = outline
    }
  }

  // 添加正文片段（流式）
  function appendContent(chunk: string) {
    if (currentTask.value) {
      currentTask.value.content += chunk
      partialContent.value += chunk
    }
  }

  // 清空缓存内容
  function clearPartialContent() {
    partialContent.value = ''
  }

  // 重置任务
  function resetTask() {
    currentTask.value = null
    partialContent.value = ''
  }

  return {
    currentTask,
    partialContent,
    createTask,
    updateStatus,
    setTitles,
    selectTitle,
    setOutline,
    appendContent,
    clearPartialContent,
    resetTask,
  }
})