/**
 * 事件总线
 * 用于跨组件通信
 */
type EventCallback<T = unknown> = (data: T) => void

class EventBus {
  private events: Map<string, Set<EventCallback<unknown>>>

  constructor() {
    this.events = new Map()
  }

  on<T = unknown>(event: string, callback: EventCallback<T>): () => void {
    if (!this.events.has(event)) {
      this.events.set(event, new Set())
    }
    this.events.get(event)!.add(callback as EventCallback<unknown>)

    // 返回取消订阅函数
    return () => {
      this.off(event, callback)
    }
  }

  off<T = unknown>(event: string, callback: EventCallback<T>): void {
    const callbacks = this.events.get(event)
    if (callbacks) {
      callbacks.delete(callback as EventCallback<unknown>)
      if (callbacks.size === 0) {
        this.events.delete(event)
      }
    }
  }

  emit<T = unknown>(event: string, data?: T): void {
    const callbacks = this.events.get(event)
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in event handler for "${event}":`, error)
        }
      })
    }
  }

  once<T = unknown>(event: string, callback: EventCallback<T>): void {
    const wrappedCallback: EventCallback<unknown> = (data) => {
      callback(data as T)
      this.off(event, wrappedCallback)
    }
    this.on(event, wrappedCallback as EventCallback<T>)
  }

  clear(): void {
    this.events.clear()
  }
}

// 全局事件总线实例
export const eventBus = new EventBus()

// ==================== 定义常用事件 ====================

export const Events = {
  // 用户相关
  USER_LOGIN: 'user:login',
  USER_LOGOUT: 'user:logout',
  USER_UPDATED: 'user:updated',

  // 配置相关
  PREFERENCES_UPDATED: 'preferences:updated',
}

export default eventBus
