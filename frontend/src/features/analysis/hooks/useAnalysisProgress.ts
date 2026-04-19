import { useState, useEffect, useCallback, useRef } from 'react'
import type { AnalysisResult, TaskStatusData, SSEProgressData } from '@/types/analysis.types'
import { getTaskStatus, getTaskResult, connectTaskWebSocket, getStreamTicket } from '@/services/api/analysis'

interface UseAnalysisProgressOptions {
  taskId?: string
  /** 非运行状态时的轮询间隔（毫秒），默认 3000 */
  pollInterval?: number
}

interface UseAnalysisProgressReturn {
  /** 当前进度 0-100 */
  progress: number
  /** 任务状态 */
  status: string
  /** 当前步骤描述 */
  currentStep: string
  /** 步骤详情 */
  stepDetail: string
  /** 分析结果（完成后） */
  result: AnalysisResult | null
  /** 是否还在运行中 */
  isRunning: boolean
  /** 错误信息 */
  error: string | null
  /** WebSocket 是否已连接 */
  isConnected: boolean
  /** 手动刷新状态 */
  refresh: () => Promise<void>
}

export function useAnalysisProgress(options: UseAnalysisProgressOptions): UseAnalysisProgressReturn {
  const { taskId, pollInterval = 3000 } = options

  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<string>('pending')
  const [currentStep, setCurrentStep] = useState('')
  const [stepDetail, setStepDetail] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const fetchingResultRef = useRef(false)
  const isRunningRef = useRef(isRunning)
  const reconnectCountRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    isRunningRef.current = isRunning
  }, [isRunning])

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const closeWebSocket = useCallback(() => {
    clearReconnectTimer()
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
      wsRef.current = null
    }
    setIsConnected(false)
  }, [clearReconnectTimer])

  const fetchStatus = useCallback(async () => {
    if (!taskId) return
    try {
      const res = await getTaskStatus(taskId)
      if (res.success && res.data) {
        applyStatusData(res.data)
      }
    } catch {
      // 轮询时不主动阻断
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  const fetchResult = useCallback(async () => {
    if (!taskId || fetchingResultRef.current) return
    fetchingResultRef.current = true
    try {
      const res = await getTaskResult(taskId)
      if (res.success && res.data) {
        setResult(res.data)
      }
    } catch {
      // ignore
    } finally {
      fetchingResultRef.current = false
    }
  }, [taskId])

  const applyProgressData = useCallback((data: SSEProgressData) => {
    if (data.progress !== undefined) setProgress(data.progress)
    if (data.status) setStatus(data.status)
    if (data.current_step) setCurrentStep(data.current_step)
    if (data.step_detail) setStepDetail(data.step_detail)

    const runningStates = ['pending', 'processing', 'running', 'queued']
    const finishedStates = ['completed', 'failed', 'cancelled']
    const isDone = finishedStates.includes(data.status || '')
    const isRun = runningStates.includes(data.status || '')
    setIsRunning(isRun && !isDone)

    if (isDone) {
      setIsRunning(false)
      if (data.status === 'completed') {
        fetchResult()
      }
      closeWebSocket()
      clearPollTimer()
    }
  }, [clearPollTimer, closeWebSocket, fetchResult])

  const applyStatusData = useCallback((data: TaskStatusData) => {
    setProgress(data.progress ?? 0)
    setStatus(data.status)
    setCurrentStep(data.current_step || '')
    setStepDetail(data.message || '')

    const runningStates = ['pending', 'processing', 'running', 'queued']
    const finishedStates = ['completed', 'failed', 'cancelled']
    const isDone = finishedStates.includes(data.status)
    const isRun = runningStates.includes(data.status)
    setIsRunning(isRun && !isDone)

    if (isDone) {
      setIsRunning(false)
      if (data.status === 'completed') {
        fetchResult()
      }
      closeWebSocket()
      clearPollTimer()
    }
  }, [clearPollTimer, closeWebSocket, fetchResult])

  const connectWebSocket = useCallback(async () => {
    if (!taskId) return

    closeWebSocket()
    setError(null)

    try {
      // 先获取认证 ticket
      let ticket: string | undefined
      try {
        const res = await getStreamTicket(taskId)
        if (res.success && res.data) {
          ticket = res.data.ticket
        }
      } catch {
        // ticket 获取失败仍可尝试无 ticket 连接（开发环境可能允许）
      }

      const ws = connectTaskWebSocket(taskId, ticket)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            event_type: string
            task_id: string
            timestamp: number
            data: Record<string, unknown>
          }

          // 忽略连接建立确认
          if (msg.event_type === 'connection_established') {
            return
          }

          // 处理进度更新事件
          if (msg.event_type === 'progress_update' || msg.event_type === 'PROGRESS_UPDATE') {
            const data = msg.data as SSEProgressData
            applyProgressData(data)
            return
          }

          // 处理任务完成事件
          if (msg.event_type === 'task_completed' || msg.event_type === 'TASK_COMPLETED') {
            const data = msg.data as SSEProgressData
            applyProgressData({
              ...data,
              status: 'completed',
              progress: 100,
            })
            return
          }

          // 处理任务失败事件
          if (msg.event_type === 'task_failed' || msg.event_type === 'TASK_FAILED') {
            const data = msg.data as Record<string, unknown>
            applyProgressData({
              status: 'failed',
              progress: data.progress as number ?? 0,
              message: data.message as string || '任务失败',
            })
            return
          }

          // 处理任务取消事件
          if (msg.event_type === 'task_cancelled' || msg.event_type === 'TASK_CANCELLED') {
            applyProgressData({ status: 'cancelled', progress: 0 })
            return
          }

          // 处理阶段开始/完成事件
          if (msg.event_type === 'phase_started' || msg.event_type === 'PHASE_STARTED') {
            const data = msg.data as Record<string, unknown>
            setCurrentStep(data.message as string || `阶段 ${data.phase} 开始`)
            return
          }

          if (msg.event_type === 'phase_completed' || msg.event_type === 'PHASE_COMPLETED') {
            const data = msg.data as Record<string, unknown>
            setCurrentStep(data.message as string || `阶段 ${data.phase} 完成`)
            if (data.progress !== undefined) {
              setProgress(data.progress as number)
            }
            return
          }

          // 工具调用相关事件（仅更新步骤详情，不修改进度）
          if (msg.event_type === 'tool_called' || msg.event_type === 'TOOL_CALLED') {
            const data = msg.data as Record<string, unknown>
            setStepDetail(`工具调用: ${data.tool_name as string || ''}`)
            return
          }

          if (msg.event_type === 'tool_result' || msg.event_type === 'TOOL_RESULT') {
            const data = msg.data as Record<string, unknown>
            const success = data.success as boolean
            setStepDetail(`工具结果: ${data.tool_name as string || ''} (${success ? '成功' : '失败'})`)
            return
          }

          if (msg.event_type === 'tool_disabled' || msg.event_type === 'TOOL_DISABLED') {
            const data = msg.data as Record<string, unknown>
            setStepDetail(`工具已禁用: ${data.tool_name as string || ''}`)
            return
          }

          // 智能体事件
          if (msg.event_type === 'agent_started' || msg.event_type === 'AGENT_STARTED') {
            const data = msg.data as Record<string, unknown>
            setCurrentStep(`智能体执行: ${data.agent_name as string || data.agent_slug as string || ''}`)
            return
          }

          if (msg.event_type === 'agent_completed' || msg.event_type === 'AGENT_COMPLETED') {
            const data = msg.data as Record<string, unknown>
            if (data.progress !== undefined) {
              setProgress(data.progress as number)
            }
            return
          }
        } catch {
          // ignore parse error
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
      }

      ws.onerror = () => {
        setIsConnected(false)
        setError('WebSocket 连接异常')
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'WebSocket 连接失败'
      setError(errMsg)
    }
  }, [taskId, applyProgressData, closeWebSocket])

  // 建立 WebSocket 连接
  useEffect(() => {
    if (!taskId) {
      closeWebSocket()
      clearPollTimer()
      setProgress(0)
      setStatus('pending')
      setCurrentStep('')
      setStepDetail('')
      setResult(null)
      setIsRunning(false)
      setError(null)
      return
    }

    setError(null)

    // 先拉一次状态
    fetchStatus()

    // 建立 WebSocket（异步获取 ticket 后连接）
    connectWebSocket().catch(() => {
      // 连接失败时由轮询兜底
    })

    // fallback 轮询
    const schedulePoll = () => {
      clearPollTimer()
      pollTimerRef.current = setTimeout(async () => {
        await fetchStatus()
        if (isRunningRef.current) {
          schedulePoll()
        }
      }, pollInterval)
    }
    schedulePoll()

    return () => {
      closeWebSocket()
      clearPollTimer()
    }
  }, [taskId, pollInterval, fetchStatus, applyProgressData, clearPollTimer, closeWebSocket, connectWebSocket])

  const refresh = useCallback(async () => {
    await fetchStatus()
    if (status === 'completed' && !result) {
      await fetchResult()
    }
  }, [fetchStatus, fetchResult, status, result])

  return {
    progress,
    status,
    currentStep,
    stepDetail,
    result,
    isRunning,
    error,
    isConnected,
    refresh,
  }
}
