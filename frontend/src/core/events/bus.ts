import { ref, reactive } from 'vue'

export interface Event {
  type: string
  data: any
  timestamp: Date
  source: string
}

export interface EventHandler {
  (event: Event): void | Promise<void>
}

class EventBus {
  private handlers: Map<string, Set<EventHandler>> = new Map()
  private eventHistory: Event[] = []
  private maxHistorySize = 1000

  // 订阅事件
  on(eventType: string, handler: EventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set())
    }

    const handlers = this.handlers.get(eventType)!
    handlers.add(handler)

    // 返回取消订阅函数
    return () => {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.handlers.delete(eventType)
      }
    }
  }

  // 订阅事件（只触发一次）
  once(eventType: string, handler: EventHandler): () => void {
    const onceHandler: EventHandler = (event) => {
      handler(event)
      this.off(eventType, onceHandler)
    }

    return this.on(eventType, onceHandler)
  }

  // 取消订阅事件
  off(eventType: string, handler: EventHandler): void {
    const handlers = this.handlers.get(eventType)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.handlers.delete(eventType)
      }
    }
  }

  // 发布事件
  async emit(eventType: string, data: any, source = 'unknown'): Promise<void> {
    const event: Event = {
      type: eventType,
      data,
      timestamp: new Date(),
      source
    }

    // 记录事件历史
    this.eventHistory.push(event)
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory.shift()
    }

    // 异步调用所有处理器
    const handlers = this.handlers.get(eventType)
    if (handlers) {
      const promises = Array.from(handlers).map(handler => {
        try {
          return Promise.resolve(handler(event))
        } catch (error) {
          console.error(`Error in event handler for ${eventType}:`, error)
          return Promise.resolve()
        }
      })

      await Promise.all(promises)
    }
  }

  // 获取事件历史
  getEventHistory(eventType?: string): Event[] {
    if (eventType) {
      return this.eventHistory.filter(event => event.type === eventType)
    }
    return [...this.eventHistory]
  }

  // 获取已订阅的事件类型
  getSubscribedEvents(): string[] {
    return Array.from(this.handlers.keys())
  }

  // 清除所有订阅
  clear(): void {
    this.handlers.clear()
    this.eventHistory.length = 0
  }

  // 获取某个事件类型的订阅者数量
  getHandlerCount(eventType: string): number {
    return this.handlers.get(eventType)?.size || 0
  }
}

// 创建全局事件总线实例
export const eventBus = new EventBus()

// 事件类型常量
export const EventTypes = {
  // 用户事件
  USER_LOGIN: 'user.login',
  USER_LOGOUT: 'user.logout',
  USER_REGISTER: 'user.register',
  USER_UPDATED: 'user.updated',

  // 模块事件
  MODULE_LOADED: 'module.loaded',
  MODULE_ERROR: 'module.error',
  MODULE_UNLOADED: 'module.unloaded',

  // 系统事件
  SYSTEM_STARTUP: 'system.startup',
  SYSTEM_ERROR: 'system.error',

  // 路由事件
  ROUTE_CHANGED: 'route.changed',

  // API事件
  API_REQUEST: 'api.request',
  API_RESPONSE: 'api.response',
  API_ERROR: 'api.error',

  // UI事件
  LOADING_START: 'ui.loading.start',
  LOADING_END: 'ui.loading.end',
  NOTIFICATION_SHOW: 'ui.notification.show',
  NOTIFICATION_HIDE: 'ui.notification.hide'
} as const

// 创建响应式状态
export const eventState = reactive({
  lastEvent: null as Event | null,
  loadingCount: 0,
  notifications: [] as Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message?: string
    duration?: number
  }>
})

// 自动处理loading状态
eventBus.on(EventTypes.LOADING_START, () => {
  eventState.loadingCount++
})

eventBus.on(EventTypes.LOADING_END, () => {
  if (eventState.loadingCount > 0) {
    eventState.loadingCount--
  }
})

// 自动记录最后一个事件
eventBus.on('*', (event: Event) => {
  eventState.lastEvent = event
})