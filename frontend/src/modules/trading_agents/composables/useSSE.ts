/**
 * SSE (Server-Sent Events) 流式输出 Composable
 * 用于接收第四阶段总结智能体的流式报告输出
 *
 * @see docs/design.md 第1388-1423行 API 路由设计
 */
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

// SSE 连接状态
export enum SSEStatus {
  CONNECTING = 'connecting',
  OPEN = 'open',
  CLOSED = 'closed',
  ERROR = 'error',
}

interface SSEOptions {
  /**
   * 任务 ID
   */
  taskId: string

  /**
   * 接收到消息时的回调
   */
  onMessage?: (chunk: string) => void

  /**
   * 流完成时的回调
   */
  onComplete?: (fullText: string) => void

  /**
   * 错误回调
   */
  onError?: (error: Error) => void

  /**
   * 状态变化回调
   */
  onStatusChange?: (status: SSEStatus) => void
}

/**
 * SSE 流式输出 Composable
 */
export function useSSE(options: SSEOptions) {
  const {
    taskId,
    onMessage,
    onComplete,
    onError,
    onStatusChange,
  } = options

  // EventSource 实例
  let eventSource: EventSource | null = null

  // 连接状态
  const status = ref<SSEStatus>(SSEStatus.CLOSED)

  // 接收到的文本
  const receivedText = ref('')

  // 是否完成
  const isComplete = ref(false)

  // 错误信息
  const error = ref<Error | null>(null)

  // SSE 端点
  const SSE_ENDPOINT = `/api/trading-agents/stream/${taskId}`

  // 计算属性：是否已连接
  const isConnected = computed(() => status.value === SSEStatus.OPEN)

  // 计算属性：是否正在连接
  const isConnecting = computed(() => status.value === SSEStatus.CONNECTING)

  /**
   * 更新连接状态
   */
  function setStatus(newStatus: SSEStatus) {
    if (status.value !== newStatus) {
      status.value = newStatus
      onStatusChange?.(newStatus)
    }
  }

  /**
   * 处理消息接收
   */
  function handleMessage(event: MessageEvent) {
    try {
      const data = event.data

      // 检查是否为完成标记
      if (data === '[DONE]') {
        isComplete.value = true
        setStatus(SSEStatus.CLOSED)
        onComplete?.(receivedText.value)
        ElMessage.success('报告生成完成')
        return
      }

      // 解析 JSON 格式的消息
      const parsed = JSON.parse(data)

      // 处理流式内容
      if (parsed.content) {
        receivedText.value += parsed.content
        onMessage?.(parsed.content)
      }

      // 处理错误
      if (parsed.error) {
        error.value = new Error(parsed.error)
        onError?.(error.value)
      }
    } catch (e) {
      // 如果不是 JSON，直接作为文本处理
      receivedText.value += data
      onMessage?.(data)
    }
  }

  /**
   * 处理连接打开
   */
  function handleOpen() {
    console.log('[SSE] 连接已建立')
    setStatus(SSEStatus.OPEN)
    error.value = null
  }

  /**
   * 处理连接错误
   */
  function handleError(event: Event) {
    console.error('[SSE] 连接错误:', event)
    setStatus(SSEStatus.ERROR)

    const err = new Error('SSE 连接错误')
    error.value = err
    onError?.(err)
    ElMessage.error('连接失败，请重试')
  }

  /**
   * 连接 SSE
   */
  function connect() {
    if (eventSource && eventSource.readyState === EventSource.OPEN) {
      console.log('[SSE] 已经连接')
      return
    }

    // 清除现有连接
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    // 重置状态
    receivedText.value = ''
    isComplete.value = false
    error.value = null

    console.log('[SSE] 正在连接:', SSE_ENDPOINT)

    setStatus(SSEStatus.CONNECTING)

    try {
      eventSource = new EventSource(SSE_ENDPOINT)

      eventSource.onopen = handleOpen
      eventSource.onmessage = handleMessage
      eventSource.onerror = handleError
    } catch (err) {
      console.error('[SSE] 创建连接失败:', err)
      setStatus(SSEStatus.ERROR)
      error.value = err as Error
      onError?.(err as Error)
    }
  }

  /**
   * 断开连接
   */
  function disconnect() {
    console.log('[SSE] 断开连接')

    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    setStatus(SSEStatus.CLOSED)
  }

  /**
   * 重置状态
   */
  function reset() {
    receivedText.value = ''
    isComplete.value = false
    error.value = null
  }

  /**
   * 获取完整文本
   */
  function getFullText(): string {
    return receivedText.value
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
    receivedText,
    isComplete,
    error,

    // 方法
    connect,
    disconnect,
    reset,
    getFullText,
  }
}

/**
 * Markdown 流式渲染 Hook
 * 用于将流式接收的 Markdown 文本渲染为 HTML
 */
export function useMarkdownStream() {
  const renderedHTML = ref('')

  /**
   * 追加文本到渲染缓冲区
   */
  function appendText(text: string) {
    renderedHTML.value += text
  }

  /**
   * 清空渲染缓冲区
   */
  function clear() {
    renderedHTML.value = ''
  }

  /**
   * 将 Markdown 转换为 HTML
   * 注意：这里返回的是原始文本，实际渲染时需要使用 Markdown 库
   * 如 marked.js 或 markdown-it
   */
  function render(markdown: string): string {
    // 简单的 Markdown 转换（生产环境建议使用专门的库）
    return markdown
      // 标题
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      // 粗体
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      // 斜体
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      // 代码块
      .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
      // 行内代码
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      // 链接
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
      // 换行
      .replace(/\n/gim, '<br>')
  }

  return {
    renderedHTML,
    appendText,
    clear,
    render,
  }
}
