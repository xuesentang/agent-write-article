/**
 * SSE (Server-Sent Events) 客户端封装
 * 提供可复用的 SSE 连接管理功能
 */

import { ref, onUnmounted, watch } from 'vue'

// SSE 事件类型枚举（与后端保持一致）
export enum SSEEventType {
  STATUS = 'status',
  TITLE_CHUNK = 'title_chunk',
  TITLE_COMPLETE = 'title_complete',
  OUTLINE_CHUNK = 'outline_chunk',
  OUTLINE_COMPLETE = 'outline_complete',
  CONTENT_CHUNK = 'content_chunk',
  CONTENT_COMPLETE = 'content_complete',
  IMAGE_PROGRESS = 'image_progress',
  IMAGE_COMPLETE = 'image_complete',
  PROGRESS = 'progress',
  ERROR = 'error',
  DONE = 'done',
  HEARTBEAT = 'heartbeat',
}

// SSE 阶段枚举
export enum SSEStage {
  TITLE = 'title',
  OUTLINE = 'outline',
  CONTENT = 'content',
  IMAGE = 'image',
}

// 统一事件数据格式
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

// 连接状态
export enum ConnectionState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
}

// SSE 客户端配置
export interface SSEClientOptions {
  // 最大重连次数
  maxReconnectAttempts?: number
  // 重连延迟（毫秒）
  reconnectDelay?: number
  // 是否自动重连
  autoReconnect?: boolean
  // 心跳超时（毫秒）
  heartbeatTimeout?: number
}

// 事件回调类型
export type EventCallback = (data: SSEEventData) => void

/**
 * SSE 客户端类
 */
export class SSEClient {
  private eventSource: EventSource | null = null
  private url: string
  private options: Required<SSEClientOptions>
  private reconnectAttempts = 0
  private eventCallbacks: Map<SSEEventType, EventCallback[]> = new Map()
  private anyCallback: EventCallback | null = null
  private heartbeatTimer: number | null = null
  private lastEventTime: number = 0

  // 响应式状态
  public connectionState = ref<ConnectionState>(ConnectionState.DISCONNECTED)
  public lastError = ref<string | null>(null)
  public eventCount = ref(0)

  constructor(url: string, options: SSEClientOptions = {}) {
    this.url = url
    this.options = {
      maxReconnectAttempts: options.maxReconnectAttempts ?? 3,
      reconnectDelay: options.reconnectDelay ?? 1000,
      autoReconnect: options.autoReconnect ?? true,
      heartbeatTimeout: options.heartbeatTimeout ?? 60000, // 60 秒
    }
  }

  /**
   * 建立 SSE 连接
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.eventSource) {
        this.disconnect()
      }

      this.connectionState.value = ConnectionState.CONNECTING
      console.log(`[SSE] 正在连接: ${this.url}`)

      this.eventSource = new EventSource(this.url)

      // 连接成功
      this.eventSource.onopen = () => {
        console.log('[SSE] 连接成功')
        this.connectionState.value = ConnectionState.CONNECTED
        this.reconnectAttempts = 0
        this.lastError.value = null
        this.startHeartbeatCheck()
        resolve()
      }

      // 连接错误
      this.eventSource.onerror = (error) => {
        console.error('[SSE] 连接错误:', error)
        this.connectionState.value = ConnectionState.ERROR

        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.handleReconnect()
        }

        reject(new Error('SSE 连接失败'))
      }

      // 默认消息处理
      this.eventSource.onmessage = (event) => {
        this.handleEvent('message', event)
      }

      // 注册所有事件类型监听
      Object.values(SSEEventType).forEach((eventType) => {
        this.eventSource?.addEventListener(eventType, (event: MessageEvent) => {
          this.handleEvent(eventType, event)
        })
      })
    })
  }

  /**
   * 断开 SSE 连接
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
      console.log('[SSE] 连接已断开')
    }

    this.connectionState.value = ConnectionState.DISCONNECTED
    this.stopHeartbeatCheck()
  }

  /**
   * 注册事件回调
   * @param eventType 事件类型
   * @param callback 回调函数
   */
  on(eventType: SSEEventType, callback: EventCallback): void {
    if (!this.eventCallbacks.has(eventType)) {
      this.eventCallbacks.set(eventType, [])
    }
    this.eventCallbacks.get(eventType)?.push(callback)
  }

  /**
   * 移除事件回调
   * @param eventType 事件类型
   * @param callback 回调函数（可选，不传则移除该类型的所有回调）
   */
  off(eventType: SSEEventType, callback?: EventCallback): void {
    if (callback) {
      const callbacks = this.eventCallbacks.get(eventType)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
      }
    } else {
      this.eventCallbacks.delete(eventType)
    }
  }

  /**
   * 注册任意事件回调
   * @param callback 回调函数
   */
  onAny(callback: EventCallback): void {
    this.anyCallback = callback
  }

  /**
   * 处理接收到的 SSE 事件
   */
  private handleEvent(eventType: string, event: MessageEvent): void {
    this.lastEventTime = Date.now()
    this.eventCount.value++

    let data: SSEEventData
    try {
      data = JSON.parse(event.data) as SSEEventData
    } catch {
      console.warn('[SSE] 无法解析事件数据:', event.data)
      return
    }

    console.log(`[SSE] 收到事件: ${eventType}`, data)

    // 触发特定事件回调
    const callbacks = this.eventCallbacks.get(eventType as SSEEventType) || []
    callbacks.forEach((cb) => cb(data))

    // 触发通用回调
    if (this.anyCallback) {
      this.anyCallback(data)
    }

    // 处理特殊事件
    if (eventType === SSEEventType.DONE || eventType === SSEEventType.ERROR) {
      // 任务完成或出错时断开连接
      if (eventType === SSEEventType.DONE) {
        console.log('[SSE] 任务完成，断开连接')
        this.disconnect()
      }
    }
  }

  /**
   * 处理重连逻辑
   */
  private handleReconnect(): void {
    if (!this.options.autoReconnect) {
      console.log('[SSE] 自动重连已禁用')
      return
    }

    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('[SSE] 已达到最大重连次数')
      this.lastError.value = '已达到最大重连次数'
      this.connectionState.value = ConnectionState.ERROR
      return
    }

    this.reconnectAttempts++
    const delay = this.options.reconnectDelay * this.reconnectAttempts

    console.log(
      `[SSE] 准备重连... 第 ${this.reconnectAttempts}/${this.options.maxReconnectAttempts} 次，延迟 ${delay}ms`
    )

    setTimeout(() => {
      this.connect().catch((err) => {
        console.error('[SSE] 重连失败:', err)
      })
    }, delay)
  }

  /**
   * 启动心跳检查
   */
  private startHeartbeatCheck(): void {
    this.stopHeartbeatCheck()
    this.lastEventTime = Date.now()

    this.heartbeatTimer = window.setInterval(() => {
      const elapsed = Date.now() - this.lastEventTime
      if (elapsed > this.options.heartbeatTimeout) {
        console.warn('[SSE] 心跳超时，断开连接')
        this.disconnect()
        this.handleReconnect()
      }
    }, 10000) // 每 10 秒检查一次
  }

  /**
   * 停止心跳检查
   */
  private stopHeartbeatCheck(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

/**
 * 创建 SSE 客户端 composable
 * @param url SSE 连接 URL
 * @param options 配置选项
 */
export function useSSE(url: string | (() => string), options: SSEClientOptions = {}) {
  let client: SSEClient | null = null

  // 响应式状态
  const connectionState = ref<ConnectionState>(ConnectionState.DISCONNECTED)
  const lastError = ref<string | null>(null)
  const eventCount = ref(0)
  const lastEventData = ref<SSEEventData | null>(null)

  // 创建客户端
  const createClient = () => {
    const actualUrl = typeof url === 'function' ? url() : url
    client = new SSEClient(actualUrl, options)

    // 同步状态
    watch(
      () => client?.connectionState.value,
      (newState) => {
        if (newState) connectionState.value = newState
      }
    )
    watch(
      () => client?.lastError.value,
      (newError) => {
        lastError.value = newError ?? null
      }
    )
    watch(
      () => client?.eventCount.value,
      (newCount) => {
        eventCount.value = newCount
      }
    )

    return client
  }

  // 连接
  const connect = async () => {
    if (!client) {
      createClient()
    }
    await client?.connect()
  }

  // 断开
  const disconnect = () => {
    client?.disconnect()
  }

  // 注册事件回调
  const on = (eventType: SSEEventType, callback: EventCallback) => {
    client?.on(eventType, callback)
  }

  // 移除事件回调
  const off = (eventType: SSEEventType, callback?: EventCallback) => {
    client?.off(eventType, callback)
  }

  // 注册任意事件回调
  const onAny = (callback: EventCallback) => {
    client?.onAny(callback)
  }

  // 组件卸载时自动断开
  onUnmounted(() => {
    client?.disconnect()
  })

  return {
    // 状态
    connectionState,
    lastError,
    eventCount,
    lastEventData,
    // 方法
    connect,
    disconnect,
    on,
    off,
    onAny,
    // 枚举
    ConnectionState,
    SSEEventType,
    SSEStage,
  }
}