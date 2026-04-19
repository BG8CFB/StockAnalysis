import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
  event_type: string
  task_id: string
  timestamp: number
  data: Record<string, unknown>
}

interface UseWebSocketOptions {
  url: string
  onMessage?: (msg: WebSocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: string) => void
  autoReconnect?: boolean
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  error: string | null
  send: (data: unknown) => void
  close: () => void
  reconnect: () => void
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect = true,
    maxReconnectAttempts = 3,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connectRef = useRef<(() => void) | null>(null)
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const close = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
      pingTimerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const startPing = useCallback(() => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
    }
    pingTimerRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
  }, [])

  const connect = useCallback(() => {
    close()
    setError(null)

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
        onOpen?.()
        startPing()
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WebSocketMessage
          // 自动处理 pong 响应
          if (msg.event_type === 'connection_established') {
            return
          }
          onMessage?.(msg)
        } catch {
          // ignore parse error
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (pingTimerRef.current) {
          clearInterval(pingTimerRef.current)
          pingTimerRef.current = null
        }
        onClose?.()

        if (autoReconnect && reconnectCountRef.current < maxReconnectAttempts) {
          reconnectCountRef.current += 1
          const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 10000)
          reconnectTimerRef.current = setTimeout(() => {
            connectRef.current?.()
          }, delay)
        } else if (reconnectCountRef.current >= maxReconnectAttempts) {
          const errMsg = 'WebSocket 重连次数已达上限'
          setError(errMsg)
          onError?.(errMsg)
        }
      }

      ws.onerror = () => {
        setIsConnected(false)
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'WebSocket 连接失败'
      setError(errMsg)
      onError?.(errMsg)
    }
  }, [url, autoReconnect, maxReconnectAttempts, onMessage, onOpen, onClose, onError, close, startPing])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    connectRef.current = connect
  })

  useEffect(() => {
    // 使用 setTimeout 避免在 effect 同步体中调用 setState（触发级联渲染警告）
    const timer = setTimeout(() => {
      connectRef.current?.()
    }, 0)
    return () => {
      clearTimeout(timer)
      close()
    }
  }, [connect, close])

  return {
    isConnected,
    error,
    send,
    close,
    reconnect: connect,
  }
}
