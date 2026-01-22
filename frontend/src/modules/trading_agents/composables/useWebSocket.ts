/**
 * WebSocket 连接管理 Composable
 * 实现按需连接、断线重连、心跳检测等功能
 *
 * @see docs/design.md 第827-873行 WebSocket 重连策略
 */
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { TaskEvent, TaskEventHandler } from '../types'

// WebSocket 连接状态
export enum WebSocketStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

// WebSocket 配置
const WS_CONFIG = {
  // 心跳间隔（秒）
  HEARTBEAT_INTERVAL: Number(import.meta.env.VITE_WS_HEARTBEAT_INTERVAL) || 30,
  // 心跳超时（秒）
  HEARTBEAT_TIMEOUT: Number(import.meta.env.VITE_WS_HEARTBEAT_TIMEOUT) || 35,
  // 重连基础延迟（毫秒）
  BASE_RETRY_DELAY: Number(import.meta.env.VITE_WS_BASE_RETRY_DELAY) || 1000,
  // 重连最大延迟（毫秒）
  MAX_RETRY_DELAY: Number(import.meta.env.VITE_WS_MAX_RETRY_DELAY) || 30000,
  // 最大重试次数
  MAX_RETRY_COUNT: Number(import.meta.env.VITE_WS_MAX_RETRY_COUNT) || 10,
  // WebSocket 端点
  WS_ENDPOINT: (taskId: string) => `/api/ws/tasks/${taskId}`,
}

interface WebSocketOptions {
  /**
   * 任务 ID
   */
  taskId: string

  /**
   * 事件处理器
   */
  onEvent?: TaskEventHandler

  /**
   * 连接状态变化回调
   */
  onStatusChange?: (status: WebSocketStatus) => void

  /**
   * 错误回调
   */
  onError?: (error: Error) => void

  /**
   * 是否自动重连（默认 true）
   */
  autoReconnect?: boolean

  /**
   * 心跳间隔（秒），默认 30
   */
  heartbeatInterval?: number

  /**
   * 心跳超时（秒），默认 35
   */
  heartbeatTimeout?: number
}

/**
 * WebSocket 连接管理 Composable
 */
export function useWebSocket(options: WebSocketOptions) {
  const {
    taskId,
    onEvent,
    onStatusChange,
    onError,
    autoReconnect = true,
    heartbeatInterval = WS_CONFIG.HEARTBEAT_INTERVAL,
    heartbeatTimeout = WS_CONFIG.HEARTBEAT_TIMEOUT,
  } = options

  // WebSocket 实例
  let ws: WebSocket | null = null

  // 连接状态
  const status = ref<WebSocketStatus>(WebSocketStatus.DISCONNECTED)

  // 重试计数
  const retryCount = ref(0)

  // 是否手动关闭
  let manuallyClosed = false

  // 定时器
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let heartbeatTimeoutTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 计算属性：是否已连接
  const isConnected = computed(() => status.value === WebSocketStatus.CONNECTED)

  // 计算属性：是否正在连接或重连
  const isConnecting = computed(() =>
    status.value === WebSocketStatus.CONNECTING ||
    status.value === WebSocketStatus.RECONNECTING
  )

  /**
   * 更新连接状态
   */
  function setStatus(newStatus: WebSocketStatus) {
    if (status.value !== newStatus) {
      status.value = newStatus
      onStatusChange?.(newStatus)
    }
  }

  /**
   * 计算重连延迟（指数退避策略）
   */
  function calculateRetryDelay(): number {
    const delay = Math.min(
      WS_CONFIG.BASE_RETRY_DELAY * Math.pow(2, retryCount.value),
      WS_CONFIG.MAX_RETRY_DELAY
    )
    return delay
  }

  /**
   * 发送心跳
   */
  function sendHeartbeat() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'ping' }))
      } catch (error) {
        console.error('[WebSocket] 发送心跳失败:', error)
      }
    }
  }

  /**
   * 启动心跳
   */
  function startHeartbeat() {
    stopHeartbeat()

    heartbeatTimer = setInterval(() => {
      sendHeartbeat()

      // 设置心跳超时检测
      heartbeatTimeoutTimer = setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          console.warn('[WebSocket] 心跳超时，关闭连接')
          ws.close()
        }
      }, heartbeatTimeout * 1000)
    }, heartbeatInterval * 1000)
  }

  /**
   * 停止心跳
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (heartbeatTimeoutTimer) {
      clearTimeout(heartbeatTimeoutTimer)
      heartbeatTimeoutTimer = null
    }
  }

  /**
   * 清除重连定时器
   */
  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  /**
   * 处理 WebSocket 消息
   */
  function handleMessage(event: MessageEvent) {
    try {
      // 重置心跳超时
      if (heartbeatTimeoutTimer) {
        clearTimeout(heartbeatTimeoutTimer)
        heartbeatTimeoutTimer = null
      }

      const data = JSON.parse(event.data)

      // 处理心跳响应
      if (data.type === 'pong') {
        return
      }

      // 处理任务事件
      if (data.event_type && data.task_id) {
        const taskEvent: TaskEvent = {
          event_type: data.event_type,
          task_id: data.task_id,
          timestamp: data.timestamp || Date.now() / 1000,
          data: data.data || {},
        }
        onEvent?.(taskEvent)
      }
    } catch (error) {
      console.error('[WebSocket] 解析消息失败:', error)
    }
  }

  /**
   * 处理 WebSocket 打开
   */
  function handleOpen() {
    console.log('[WebSocket] ✅ 连接已建立')
    retryCount.value = 0
    setStatus(WebSocketStatus.CONNECTED)
    startHeartbeat()
  }

  /**
   * 处理 WebSocket 关闭
   */
  function handleClose(event: CloseEvent) {
    console.log('[WebSocket] 🔌 连接已关闭:', event.code, event.reason)
    stopHeartbeat()

    if (manuallyClosed) {
      setStatus(WebSocketStatus.DISCONNECTED)
      manuallyClosed = false
      return
    }

    // 判断是否需要重连
    // 1001 表示客户端离开页面，不需要重连
    // 1000 表示正常关闭，不需要重连
    if (event.code === 1000 || event.code === 1001) {
      console.log('[WebSocket] ℹ️ 正常关闭，无需重连')
      setStatus(WebSocketStatus.DISCONNECTED)
      return
    }

    // 自动重连
    if (autoReconnect && retryCount.value < WS_CONFIG.MAX_RETRY_COUNT) {
      reconnect()
    } else {
      setStatus(WebSocketStatus.ERROR)
      if (retryCount.value >= WS_CONFIG.MAX_RETRY_COUNT) {
        ElMessage.error('连接失败，请刷新页面重试')
        onError?.(new Error('超过最大重试次数'))
      }
    }
  }

  /**
   * 处理 WebSocket 错误
   */
  function handleError(event: Event) {
    console.error('[WebSocket] 连接错误:', event)
    setStatus(WebSocketStatus.ERROR)
    onError?.(new Error('WebSocket 连接错误'))
  }

  /**
   * 重连
   */
  function reconnect() {
    if (retryCount.value >= WS_CONFIG.MAX_RETRY_COUNT) {
      console.warn('[WebSocket] ⚠️ 已达到最大重试次数，停止重连')
      return
    }

    const delay = calculateRetryDelay()
    retryCount.value++

    console.log(`[WebSocket] 🔄 ${delay / 1000}秒后进行第 ${retryCount.value} 次重连...`)

    setStatus(WebSocketStatus.RECONNECTING)

    reconnectTimer = setTimeout(() => {
      if (!autoReconnect || manuallyClosed) {
        return
      }

      console.log('[WebSocket] 🔄 正在重连...')
      connect()
    }, delay)
  }

  /**
   * 连接 WebSocket
   */
  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 已经连接')
      return
    }

    // 清除现有连接
    if (ws) {
      ws.close()
      ws = null
    }

    // 获取 token
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('[WebSocket] 未找到访问令牌')
      setStatus(WebSocketStatus.ERROR)
      onError?.(new Error('未找到访问令牌'))
      return
    }

    // 构建 WebSocket URL（携带 token 作为查询参数）
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}${WS_CONFIG.WS_ENDPOINT(taskId)}?token=${encodeURIComponent(token)}`

    console.log('[WebSocket] 正在连接:', wsUrl)

    setStatus(WebSocketStatus.CONNECTING)

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = handleOpen
      ws.onmessage = handleMessage
      ws.onclose = handleClose
      ws.onerror = handleError
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error)
      setStatus(WebSocketStatus.ERROR)
      onError?.(error as Error)

      // 尝试重连
      if (autoReconnect) {
        reconnect()
      }
    }
  }

  /**
   * 断开连接
   */
  function disconnect() {
    console.log('[WebSocket] 手动断开连接')
    manuallyClosed = true
    clearReconnectTimer()
    stopHeartbeat()

    if (ws) {
      ws.close(1000, 'User closed')
      ws = null
    }

    setStatus(WebSocketStatus.DISCONNECTED)
  }

  /**
   * 发送消息
   */
  function send(data: Record<string, unknown>) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(data))
        return true
      } catch (error) {
        console.error('[WebSocket] 发送消息失败:', error)
        return false
      }
    }
    console.warn('[WebSocket] 连接未建立，无法发送消息')
    return false
  }

  /**
   * 重置重试计数（外部调用）
   */
  function resetRetryCount() {
    retryCount.value = 0
  }

  // 组件卸载时清理
  onUnmounted(() => {
    disconnect()
  })

  return {
    // 状态
    status,
    isConnected,
    isConnecting,
    retryCount,

    // 方法
    connect,
    disconnect,
    send,
    resetRetryCount,
  }
}

/**
 * 批量 WebSocket 管理器
 * 用于管理多个任务的 WebSocket 连接
 */
export function useBatchWebSocket() {
  const connections = new Map<string, ReturnType<typeof useWebSocket>>()

  /**
   * 获取或创建 WebSocket 连接
   */
  function getOrCreate(options: WebSocketOptions) {
    let connection = connections.get(options.taskId)

    if (!connection) {
      connection = useWebSocket(options)
      connections.set(options.taskId, connection)
    }

    return connection
  }

  /**
   * 移除 WebSocket 连接
   */
  function remove(taskId: string) {
    const connection = connections.get(taskId)
    if (connection) {
      connection.disconnect()
      connections.delete(taskId)
    }
  }

  /**
   * 清空所有连接
   */
  function clear() {
    connections.forEach((connection) => {
      connection.disconnect()
    })
    connections.clear()
  }

  /**
   * 获取活跃连接数
   */
  function getActiveCount(): number {
    let count = 0
    connections.forEach((connection) => {
      if (connection.isConnected.value) {
        count++
      }
    })
    return count
  }

  return {
    getOrCreate,
    remove,
    clear,
    getActiveCount,
  }
}
