/**
 * SSE (Server-Sent Events) 连接管理
 * 用于实时接收后端推送的生成进度
 */

export interface SSEEvent {
  event: string
  data: any
  id?: string
}

export type SSEEventHandler = (event: SSEEvent) => void

export class SSEClient {
  private eventSource: EventSource | null = null
  private handlers: Map<string, SSEEventHandler[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  /**
   * 连接到 SSE 服务
   */
  connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.eventSource) {
        this.disconnect()
      }

      this.eventSource = new EventSource(url)

      this.eventSource.onopen = () => {
        console.log('SSE connection opened')
        this.reconnectAttempts = 0
        resolve()
      }

      this.eventSource.onerror = (error) => {
        console.error('SSE connection error:', error)

        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.handleReconnect(url)
        } else {
          reject(new Error('SSE connection failed'))
        }
      }

      // 监听所有消息
      this.eventSource.onmessage = (event) => {
        this.handleEvent({
          event: 'message',
          data: this.parseData(event.data),
          id: event.lastEventId,
        })
      }

      // 监听自定义事件类型
      const eventTypes = [
        'status',
        'title_chunk',
        'title_complete',
        'outline_chunk',
        'outline_complete',
        'content_chunk',
        'image_progress',
        'image_complete',
        'error',
        'done',
      ]

      eventTypes.forEach((type) => {
        this.eventSource?.addEventListener(type, (event: MessageEvent) => {
          this.handleEvent({
            event: type,
            data: this.parseData(event.data),
            id: event.lastEventId,
          })
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
      console.log('SSE connection closed')
    }
    this.handlers.clear()
  }

  /**
   * 注册事件处理器
   */
  on(eventType: string, handler: SSEEventHandler): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, [])
    }
    this.handlers.get(eventType)?.push(handler)
  }

  /**
   * 移除事件处理器
   */
  off(eventType: string, handler?: SSEEventHandler): void {
    if (handler) {
      const handlers = this.handlers.get(eventType)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    } else {
      this.handlers.delete(eventType)
    }
  }

  /**
   * 处理接收到的 SSE 事件
   */
  private handleEvent(event: SSEEvent): void {
    const handlers = this.handlers.get(event.event) || []
    handlers.forEach((handler) => handler(event))

    // 同时触发通用的 'any' 处理器
    const anyHandlers = this.handlers.get('*') || []
    anyHandlers.forEach((handler) => handler(event))
  }

  /**
   * 解析 SSE 数据
   */
  private parseData(data: string): any {
    try {
      return JSON.parse(data)
    } catch {
      return data
    }
  }

  /**
   * 处理重连逻辑
   */
  private handleReconnect(url: string): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`SSE reconnecting... attempt ${this.reconnectAttempts}`)

      setTimeout(() => {
        this.connect(url).catch(console.error)
      }, this.reconnectDelay * this.reconnectAttempts)
    } else {
      console.error('SSE max reconnect attempts reached')
      this.handleEvent({
        event: 'error',
        data: { message: '连接失败，请刷新页面重试' },
      })
    }
  }
}

// 创建全局 SSE 客户端实例
export const sseClient = new SSEClient()