/**
 * API 模块 - 所有后端 API 接口定义
 */

import { request } from './http'

// ============ 类型定义 ============

export interface ApiResponse<T = any> {
  code: string
  message: string
  data: T
  success: boolean
}

export interface PagedResponse<T = any> {
  code: string
  message: string
  data: {
    items: T[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
  success: boolean
}

// 任务状态枚举
export type TaskStatus =
  | 'CREATED'
  | 'TITLE_GENERATING'
  | 'TITLE_READY'
  | 'OUTLINE_GENERATING'
  | 'OUTLINE_READY'
  | 'CONTENT_GENERATING'
  | 'CONTENT_READY'
  | 'IMAGE_GENERATING'
  | 'COMPLETED'
  | 'FAILED'

// 任务相关类型
export interface TaskCreateRequest {
  topic: string
  style: string
  extra_description?: string
}

export interface TaskResponse {
  id: string
  topic: string
  style: string
  extra_description?: string
  status: TaskStatus
  status_message?: string
  progress: string
  error_message?: string
  created_at: string
  updated_at: string
}

export interface SelectTitleRequest {
  selected_title: string
}

export interface GenerateOutlineRequest {
  target_length?: number
}

export interface OptimizeOutlineRequest {
  user_modifications: string
}

export interface SaveOutlineRequest {
  outline: OutlineStructure
}

export interface ConfirmOutlineRequest {
  outline?: OutlineStructure
}

// 大纲结构
export interface OutlineSection {
  id: string
  title: string
  level: number
  key_points?: string[]
  estimated_length?: number
  subsections?: OutlineSection[]
}

export interface OutlineStructure {
  sections: OutlineSection[]
}

// 文章相关类型
export interface TitleOption {
  title: string
  index: number
}

export interface ImageInfo {
  position: string
  url: string
  source: string
  keywords?: string[]
  width?: number
  height?: number
}

export interface ArticleResponse {
  id: string
  task_id: string
  selected_title?: string
  title_options?: TitleOption[]
  outline?: OutlineStructure
  content?: string
  images?: ImageInfo[]
  final_output?: string
  final_html?: string
  word_count?: string
  created_at: string
  updated_at: string
}

export interface ArticleExportResponse {
  title: string
  content: string
  word_count: number
  images: ImageInfo[]
  format: string
}

// ============ Task API ============

/** 创建任务 */
export function createTask(data: TaskCreateRequest): Promise<ApiResponse<TaskResponse>> {
  return request.post('/tasks', data)
}

/** 获取任务详情 */
export function getTask(taskId: string): Promise<ApiResponse<TaskResponse>> {
  return request.get(`/tasks/${taskId}`)
}

/** 获取任务列表 */
export function getTasks(params?: {
  page?: number
  page_size?: number
  status?: TaskStatus
}): Promise<PagedResponse<TaskResponse>> {
  return request.get('/tasks', { params })
}

/** 删除任务 */
export function deleteTask(taskId: string): Promise<ApiResponse<null>> {
  return request.delete(`/tasks/${taskId}`)
}

/** 获取进行中的任务 */
export function getInProgressTasks(): Promise<ApiResponse<TaskResponse[]>> {
  return request.get('/tasks/in-progress')
}

/** 触发标题生成 */
export function generateTitles(taskId: string, useMock = false): Promise<ApiResponse<{ task_id: string; status: string; message: string }>> {
  return request.post(`/tasks/${taskId}/generate-titles`, null, { params: { use_mock: useMock } })
}

/** 选择标题 */
export function selectTitle(taskId: string, data: SelectTitleRequest): Promise<ApiResponse<{ task_id: string; selected_title: string }>> {
  return request.post(`/tasks/${taskId}/select-title`, data)
}

/** 触发大纲生成 */
export function generateOutline(taskId: string, data?: GenerateOutlineRequest, useMock = false): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return request.post(`/tasks/${taskId}/generate-outline`, data, { params: { use_mock: useMock } })
}

/** 优化大纲 */
export function optimizeOutline(taskId: string, data: OptimizeOutlineRequest, useMock = false): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return request.post(`/tasks/${taskId}/optimize-outline`, data, { params: { use_mock: useMock } })
}

/** 保存大纲 */
export function saveOutline(taskId: string, data: SaveOutlineRequest): Promise<ApiResponse<{ task_id: string; outline: OutlineStructure }>> {
  return request.put(`/tasks/${taskId}/outline`, data)
}

/** 确认大纲，触发正文生成 */
export function confirmOutline(taskId: string, data?: ConfirmOutlineRequest, useMock = false): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return request.post(`/tasks/${taskId}/confirm-outline`, data, { params: { use_mock: useMock } })
}

/** 触发配图分析和生成 */
export function startImageAnalysis(taskId: string, useMock = false): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return request.post(`/tasks/${taskId}/start-image-analysis`, null, { params: { use_mock: useMock } })
}

// ============ Article API ============

/** 获取文章详情 */
export function getArticle(articleId: string): Promise<ApiResponse<ArticleResponse>> {
  return request.get(`/articles/${articleId}`)
}

/** 根据任务 ID 获取文章 */
export function getArticleByTaskId(taskId: string): Promise<ApiResponse<ArticleResponse>> {
  return request.get(`/articles/by-task/${taskId}`)
}

/** 获取文章列表 */
export function getArticles(params?: {
  page?: number
  page_size?: number
}): Promise<PagedResponse<ArticleResponse>> {
  return request.get('/articles', { params })
}

/** 导出文章 */
export function exportArticle(articleId: string): Promise<ApiResponse<ArticleExportResponse>> {
  return request.get(`/articles/${articleId}/export`)
}

/** 删除文章 */
export function deleteArticle(articleId: string): Promise<ApiResponse<null>> {
  return request.delete(`/articles/${articleId}`)
}

// ============ Health API ============

/** 健康检查 */
export function healthCheck(): Promise<ApiResponse<{ status: string; version: string; debug: boolean }>> {
  return request.get('/health')
}

/** 完整健康检查 */
export function fullHealthCheck(): Promise<ApiResponse<{ overall: boolean; components: any; version: string }>> {
  return request.get('/health/full')
}

// ============ SSE API ============

/** 获取 SSE 连接 URL */
export function getSSEUrl(taskId: string): string {
  return `/api/sse/connect/${taskId}`
}

/** 获取 SSE 测试 URL */
export function getSSETestUrl(taskId: string): string {
  return `/api/sse/test/${taskId}`
}

// ============ SSE 事件类型 ============

export enum SSEEventType {
  STATUS = 'status',
  TITLE_CHUNK = 'title_chunk',
  TITLE_COMPLETE = 'title_complete',
  OUTLINE_CHUNK = 'outline_chunk',
  OUTLINE_COMPLETE = 'outline_complete',
  CONTENT_CHUNK = 'content_chunk',
  CONTENT_COMPLETE = 'content_complete',
  IMAGE_TASK_START = 'image_task_start',
  IMAGE_PROGRESS = 'image_progress',
  IMAGE_COMPLETE = 'image_complete',
  IMAGE_ALL_COMPLETE = 'image_all_complete',
  PROGRESS = 'progress',
  ERROR = 'error',
  DONE = 'done',
  HEARTBEAT = 'heartbeat',
}

export enum SSEStage {
  TITLE = 'title',
  OUTLINE = 'outline',
  CONTENT = 'content',
  IMAGE = 'image',
}

export interface SSEEventData {
  event: SSEEventType
  stage?: SSEStage
  data: any
  progress: number
  message?: string
  timestamp?: string
  sequence?: number
  total?: number
}