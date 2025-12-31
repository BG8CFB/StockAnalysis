/**
 * 分析进度追踪 Composable
 * 用于追踪和分析股票分析任务的进度
 *
 * @see docs/design.md 第1520-1522行
 */
import { ref, computed } from 'vue'
import type { TaskEvent, AnalysisTask } from '../types'

// 阶段定义
export const PHASES = [
  { id: 1, name: '分析师团队', description: '多角度并行分析' },
  { id: 2, name: '研究员辩论', description: '多空观点交锋' },
  { id: 3, name: '风险评估', description: '风险分析讨论' },
  { id: 4, name: '总结输出', description: '生成投资建议' },
] as const

// 智能体状态
export interface AgentStatus {
  slug: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  startTime: number | null
  endTime: number | null
  report?: string
}

// 工具调用记录
export interface ToolCallRecord {
  toolName: string
  agentName: string
  input: string
  output?: string
  status: 'running' | 'completed' | 'failed'
  startTime: number
  endTime?: number
}

// 分析进度状态
interface ProgressState {
  currentPhase: number
  progress: number
  agents: Map<string, AgentStatus>
  toolCalls: ToolCallRecord[]
  reports: Map<string, string>
  startTime: number
  endTime: number | null
}

/**
 * 分析进度追踪 Composable
 */
export function useAnalysisProgress(initialTask?: AnalysisTask) {
  // 进度状态
  const state = ref<ProgressState>({
    currentPhase: initialTask?.current_phase || 1,
    progress: initialTask?.progress || 0,
    agents: new Map(),
    toolCalls: [],
    reports: new Map(Object.entries(initialTask?.reports || {})),
    startTime: initialTask?.created_at ? new Date(initialTask.created_at).getTime() : Date.now(),
    endTime: initialTask?.completed_at ? new Date(initialTask.completed_at).getTime() : null,
  })

  // 事件历史
  const events = ref<TaskEvent[]>([])

  // 当前智能体
  const currentAgent = ref<string | null>(initialTask?.current_agent || null)

  // 计算属性：当前阶段信息
  const currentPhaseInfo = computed(() =>
    PHASES.find((p) => p.id === state.value.currentPhase)
  )

  // 计算属性：任务状态
  const taskStatus = computed(() => {
    if (state.value.progress === 100) return 'completed'
    if (state.value.progress > 0) return 'running'
    return 'pending'
  })

  // 计算属性：已完成的智能体数量
  const completedAgentsCount = computed(() => {
    let count = 0
    state.value.agents.forEach((agent) => {
      if (agent.status === 'completed') count++
    })
    return count
  })

  // 计算属性：总智能体数量
  const totalAgentsCount = computed(() => state.value.agents.size)

  // 计算属性：运行中的智能体
  const runningAgents = computed(() => {
    const running: AgentStatus[] = []
    state.value.agents.forEach((agent) => {
      if (agent.status === 'running') {
        running.push(agent)
      }
    })
    return running
  })

  // 计算属性：已生成的报告
  const generatedReports = computed(() => {
    const reports: { agent: string; report: string }[] = []
    state.value.reports.forEach((report, slug) => {
      reports.push({ agent: slug, report })
    })
    return reports
  })

  // 计算属性：最近工具调用
  const recentToolCalls = computed(() => {
    return state.value.toolCalls.slice(-10).reverse()
  })

  // 计算属性：任务耗时（秒）
  const elapsedSeconds = computed(() => {
    const end = state.value.endTime || Date.now()
    return Math.floor((end - state.value.startTime) / 1000)
  })

  /**
   * 处理 WebSocket 事件
   */
  function handleEvent(event: TaskEvent) {
    events.value.push(event)

    switch (event.event_type) {
      case 'task_started':
        handleTaskStarted(event)
        break
      case 'phase_started':
        handlePhaseStarted(event)
        break
      case 'phase_completed':
        handlePhaseCompleted(event)
        break
      case 'agent_started':
        handleAgentStarted(event)
        break
      case 'agent_completed':
        handleAgentCompleted(event)
        break
      case 'tool_call':
        handleToolCall(event)
        break
      case 'tool_result':
        handleToolResult(event)
        break
      case 'report_generated':
        handleReportGenerated(event)
        break
      case 'task_completed':
        handleTaskCompleted(event)
        break
      case 'task_failed':
        handleTaskFailed(event)
        break
      case 'task_cancelled':
        handleTaskCancelled(event)
        break
      default:
        console.log('[AnalysisProgress] 未知事件类型:', event.event_type)
    }
  }

  /**
   * 处理任务开始
   */
  function handleTaskStarted(event: TaskEvent) {
    state.value.startTime = event.timestamp * 1000
    state.value.progress = 0
  }

  /**
   * 处理阶段开始
   */
  function handlePhaseStarted(event: TaskEvent) {
    state.value.currentPhase = event.data.phase as number || state.value.currentPhase
  }

  /**
   * 处理阶段完成
   */
  function handlePhaseCompleted(event: TaskEvent) {
    const phase = event.data.phase as number
    if (phase && phase >= state.value.currentPhase) {
      state.value.currentPhase = phase + 1
    }
  }

  /**
   * 处理智能体开始
   */
  function handleAgentStarted(event: TaskEvent) {
    const { agent_slug, agent_name } = event.data
    currentAgent.value = agent_slug as string

    const agent: AgentStatus = {
      slug: agent_slug as string,
      name: agent_name as string,
      status: 'running',
      startTime: event.timestamp * 1000,
      endTime: null,
    }

    state.value.agents.set(agent_slug as string, agent)
  }

  /**
   * 处理智能体完成
   */
  function handleAgentCompleted(event: TaskEvent) {
    const { agent_slug, report } = event.data
    const agent = state.value.agents.get(agent_slug as string)

    if (agent) {
      agent.status = 'completed'
      agent.endTime = event.timestamp * 1000
      agent.report = report as string
    }

    // 更新进度（假设每个智能体占总进度的 10%）
    const progressPerAgent = 100 / 10 // 假设总共10个智能体
    state.value.progress = Math.min(
      state.value.progress + progressPerAgent,
      100
    )
  }

  /**
   * 处理工具调用
   */
  function handleToolCall(event: TaskEvent) {
    const { tool_name, agent_name, input } = event.data

    const toolCall: ToolCallRecord = {
      toolName: tool_name as string,
      agentName: agent_name as string,
      input: JSON.stringify(input),
      status: 'running',
      startTime: event.timestamp * 1000,
    }

    state.value.toolCalls.push(toolCall)
  }

  /**
   * 处理工具结果
   */
  function handleToolResult(event: TaskEvent) {
    const { tool_name, output, success } = event.data

    // 找到对应的工具调用记录并更新
    const toolCall = state.value.toolCalls.find(
      (tc) => tc.toolName === tool_name && tc.status === 'running'
    )

    if (toolCall) {
      toolCall.status = success ? 'completed' : 'failed'
      toolCall.output = JSON.stringify(output)
      toolCall.endTime = event.timestamp * 1000
    }
  }

  /**
   * 处理报告生成
   */
  function handleReportGenerated(event: TaskEvent) {
    const { agent_slug, report } = event.data
    state.value.reports.set(agent_slug as string, report as string)
  }

  /**
   * 处理任务完成
   */
  function handleTaskCompleted(event: TaskEvent) {
    state.value.progress = 100
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null
  }

  /**
   * 处理任务失败
   */
  function handleTaskFailed(event: TaskEvent) {
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null
  }

  /**
   * 处理任务取消
   */
  function handleTaskCancelled(event: TaskEvent) {
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null

    // 标记所有运行中的智能体为失败
    state.value.agents.forEach((agent) => {
      if (agent.status === 'running') {
        agent.status = 'failed'
        agent.endTime = event.timestamp * 1000
      }
    })
  }

  /**
   * 重置进度
   */
  function reset() {
    state.value = {
      currentPhase: 1,
      progress: 0,
      agents: new Map(),
      toolCalls: [],
      reports: new Map(),
      startTime: Date.now(),
      endTime: null,
    }
    events.value = []
    currentAgent.value = null
  }

  /**
   * 获取智能体状态
   */
  function getAgentStatus(slug: string): AgentStatus | undefined {
    return state.value.agents.get(slug)
  }

  /**
   * 获取报告
   */
  function getReport(slug: string): string | undefined {
    return state.value.reports.get(slug)
  }

  return {
    // 状态
    state,
    events,
    currentAgent,
    currentPhaseInfo,
    taskStatus,
    completedAgentsCount,
    totalAgentsCount,
    runningAgents,
    generatedReports,
    recentToolCalls,
    elapsedSeconds,

    // 方法
    handleEvent,
    reset,
    getAgentStatus,
    getReport,
  }
}
