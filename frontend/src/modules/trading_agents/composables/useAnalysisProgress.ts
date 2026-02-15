/**
 * 分析进度追踪 Composable
 * 用于追踪和分析股票分析任务的进度
 *
 * @see docs/design.md 第1520-1522行
 */
import { ref, computed, onUnmounted } from 'vue'
import type { TaskEvent, AnalysisTask } from '../types'

// 阶段定义
export const PHASES = [
  { id: 1, name: '信息收集与基础分析', description: '多角度并行分析' },
  { id: 2, name: '多空博弈与投资决策', description: '多空观点交锋与决策' },
  { id: 3, name: '策略风格与风险评估', description: '策略辩论与风险评估' },
  { id: 4, name: '总结智能体', description: '生成最终投资建议' },
] as const

// 智能体名称映射
export const AGENT_NAME_MAPPING: Record<string, string> = {
  // Phase 1
  'financial-news-analyst': '财经新闻分析师',
  'social-media-analyst': '社交媒体分析师',
  'china-market-analyst': '中国市场分析师',
  'market-analyst': '市场技术分析师',
  'market_technical': '市场技术分析师', // 兼容旧 slug
  'fundamentals-analyst': '基本面分析师',
  'short-term-capital-analyst': '短线资金分析师',
  
  // Phase 2
  'bull-researcher': '看涨研究员',
  'bear-researcher': '看跌研究员',
  'research-manager': '投资组合经理',
  'trader': '专业交易员',
  
  // Phase 3
  'aggressive-debator': '激进策略分析师',
  'neutral-debator': '中性策略分析师',
  'conservative-debator': '保守策略分析师',
  'risk-manager': '风险管理委员会主席',
  
  // Phase 4
  'summarizer': '总结智能体',
}

/**
 * 获取智能体显示名称
 */
export function getAgentDisplayName(slug: string, originalName?: string): string {
  // 如果 originalName 是中文，优先使用 originalName
  if (originalName && /[\u4e00-\u9fa5]/.test(originalName)) {
    return originalName
  }
  
  // 否则尝试使用映射
  return AGENT_NAME_MAPPING[slug] || originalName || slug
}

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
  duration?: number
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
  // 恢复智能体状态
  const initialAgents = new Map<string, AgentStatus>()
  if (initialTask?.phase_executions) {
    initialTask.phase_executions.forEach((phase) => {
      // PhaseExecution 包含单个 agent 信息
      if (phase.agent) {
        const agent: any = { slug: phase.agent, name: phase.agent, status: phase.status, started_at: phase.started_at, completed_at: phase.completed_at }
        // 获取显示名称
        const displayName = getAgentDisplayName(agent.slug, agent.name)

        initialAgents.set(agent.slug, {
          slug: agent.slug,
          name: displayName,
          status: agent.status === 'completed' ? 'completed' :
                  agent.status === 'running' ? 'running' :
                  agent.status === 'failed' ? 'failed' : 'pending',
          startTime: agent.started_at ? new Date(agent.started_at).getTime() : null,
          endTime: agent.completed_at ? new Date(agent.completed_at).getTime() : null
        })
      }
    })
  }

  // 恢复工具调用
  const initialToolCalls: ToolCallRecord[] = []
  if (initialTask?.tool_calls) {
    initialTask.tool_calls.forEach((call: any) => {
        initialToolCalls.push({
            toolName: call.tool_name || call.toolName || 'Unknown Tool',
            agentName: call.agent_name || call.agentName || 'Unknown Agent',
            input: typeof call.input === 'string' ? call.input : JSON.stringify(call.input || {}),
            output: call.output ? (typeof call.output === 'string' ? call.output : JSON.stringify(call.output)) : undefined,
            status: call.status === 'success' || call.status === 'completed' ? 'completed' : 
                    call.status === 'failed' ? 'failed' : 'running',
            startTime: call.start_time ? new Date(call.start_time).getTime() : 
                       call.startTime ? new Date(call.startTime).getTime() : 0,
            endTime: call.end_time ? new Date(call.end_time).getTime() :
                     call.endTime ? new Date(call.endTime).getTime() : undefined
        })
    })
  }

  // 进度状态
  const state = ref<ProgressState>({
    currentPhase: initialTask?.current_phase || 1,
    progress: initialTask?.progress || 0,
    agents: initialAgents,
    toolCalls: initialToolCalls,
    reports: new Map(Object.entries(initialTask?.reports || {})),
    startTime: initialTask?.created_at ? new Date(initialTask.created_at).getTime() : Date.now(),
    endTime: initialTask?.completed_at ? new Date(initialTask.completed_at).getTime() : null,
  })

  // 事件历史
  const events = ref<TaskEvent[]>([])

  // 当前智能体
  const currentAgent = ref<string | null>(initialTask?.current_agent || null)

  // 当前时间（用于计时）
  const now = ref(Date.now())
  let timer: number | null = null

  // 启动计时器
  if (typeof window !== 'undefined') {
    timer = window.setInterval(() => {
      now.value = Date.now()
    }, 1000)
  }

  // 组件卸载时清除计时器
  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })

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

  // 计算属性：已完成的智能体
  const completedAgents = computed(() => {
    const completed: AgentStatus[] = []
    state.value.agents.forEach((agent: any) => {
      if (agent.status === 'completed') {
        completed.push(agent)
      }
    })
    return completed
  })

  // 计算属性：所有智能体（按完成时间倒序）
  const allAgents = computed(() => {
    const all: AgentStatus[] = []
    state.value.agents.forEach((agent: any) => {
      all.push(agent)
    })
    // 按完成时间倒序排列（已完成的在前）
    return all.sort((a, b) => {
      if (a.status === 'completed' && b.status !== 'completed') return -1
      if (a.status !== 'completed' && b.status === 'completed') return 1
      return (b.endTime || 0) - (a.endTime || 0)
    })
  })

  // 计算属性：已生成的报告
  const generatedReports = computed(() => {
    const reports: { agent: string; name: string; report: string }[] = []
    state.value.reports.forEach((report, slug) => {
      // 过滤掉 final_report，因为它单独展示
      if (slug === 'final_report') return

      const agentInfo = state.value.agents.get(slug)
      // 优先使用 agentInfo 中的名字，如果没有则尝试从映射表中获取
      const displayName = getAgentDisplayName(slug, agentInfo?.name)
      
      reports.push({ 
        agent: slug, 
        name: displayName,
        report 
      })
    })
    return reports
  })

  // 计算属性：最近工具调用
  const recentToolCalls = computed(() => {
    return state.value.toolCalls.slice(-10).reverse()
  })

  // 计算属性：任务耗时（秒）
  const elapsedSeconds = computed(() => {
    const end = state.value.endTime || now.value
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
      case 'agent_failed':
        handleAgentFailed(event)
        break
      case 'tool_called':
        handleToolCall(event)
        break
      case 'tool_call':
        // 兼容旧版本事件名
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
      case 'progress_update':
        handleProgressUpdate(event)
        break
      case 'phase_agents':
        handlePhaseAgents(event)
        break
      case 'connection_established':
        // WebSocket 连接建立确认，无需处理
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

    // 获取显示名称（处理后端可能传回英文名的情况）
    const displayName = getAgentDisplayName(agent_slug as string, agent_name as string)

    // 如果智能体已存在（可能由 phase_agents 添加），则更新状态
    const existing = state.value.agents.get(agent_slug as string)
    if (existing) {
      existing.status = 'running'
      existing.name = displayName // 更新名称
      existing.startTime = event.timestamp * 1000
      return
    }

    const agent: AgentStatus = {
      slug: agent_slug as string,
      name: displayName,
      status: 'running',
      startTime: event.timestamp * 1000,
      endTime: null,
    }

    state.value.agents.set(agent_slug as string, agent)
  }

  /**
   * 处理智能体完成
   * 进度：优先使用后端下发的 progress；否则按「已完成数/总智能体数」估算，总数不写死。
   */
  function handleAgentCompleted(event: TaskEvent) {
    const { agent_slug, report, content, progress: backendProgress, total_agents } = event.data
    const agent = state.value.agents.get(agent_slug as string)

    if (agent) {
      agent.status = 'completed'
      agent.endTime = event.timestamp * 1000
      // 某些事件可能在 completed 事件中携带报告
      const reportContent = (content || report) as string
      if (reportContent) {
        agent.report = reportContent
        state.value.reports.set(agent_slug as string, reportContent)
      }
    }

    // 进度：优先使用后端下发的数字类型 progress
    if (typeof backendProgress === 'number') {
      state.value.progress = Math.min(Math.max(backendProgress, 0), 100)
      return
    }
    // 否则按「已完成智能体数 / 总智能体数」估算（总数不写死，与后端口径一致）
    const total = typeof total_agents === 'number' && total_agents > 0
      ? total_agents
      : state.value.agents.size
    if (total > 0) {
      const completed = Array.from(state.value.agents.values()).filter(
        (a) => a.status === 'completed'
      ).length
      state.value.progress = Math.min(Math.round((completed / total) * 100), 100)
    }
  }

  /**
   * 处理工具调用
   * 兼容后端 tool_input/input、agent_name/agent_slug
   */
  function handleToolCall(event: TaskEvent) {
    const d = event.data as Record<string, unknown>
    const tool_name = (d.tool_name ?? '') as string
    const agent_name = (d.agent_name ?? d.agent_slug ?? '') as string
    const inputVal = d.input ?? d.tool_input ?? ''

    const toolCall: ToolCallRecord = {
      toolName: tool_name,
      agentName: agent_name,
      input: typeof inputVal === 'string' ? inputVal : JSON.stringify(inputVal),
      status: 'running',
      startTime: event.timestamp * 1000,
    }

    state.value.toolCalls.push(toolCall)
  }

  /**
   * 处理工具结果
   * 兼容后端 output 为 string 或 object
   */
  function handleToolResult(event: TaskEvent) {
    const d = event.data as Record<string, unknown>
    const tool_name = (d.tool_name ?? '') as string
    const output = d.output
    const success = (d.success ?? false) as boolean

    const toolCall = state.value.toolCalls.find(
      (tc) => tc.toolName === tool_name && tc.status === 'running'
    )

    if (toolCall) {
      toolCall.status = success ? 'completed' : 'failed'
      toolCall.output = output !== undefined && output !== null
        ? (typeof output === 'string' ? output : JSON.stringify(output))
        : ''
      toolCall.endTime = event.timestamp * 1000
    }
  }

  /**
   * 处理报告生成
   */
  function handleReportGenerated(event: TaskEvent) {
    const { agent_slug, report, content } = event.data
    // 后端发送的是 content 字段，但也兼容 report 字段
    const reportContent = (content || report) as string
    if (reportContent) {
      state.value.reports.set(agent_slug as string, reportContent)
    }
  }

  /**
   * 处理任务完成
   */
  function handleTaskCompleted(event: TaskEvent) {
    state.value.progress = 100
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  /**
   * 处理任务失败
   */
  function handleTaskFailed(event: TaskEvent) {
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  /**
   * 处理任务取消
   */
  function handleTaskCancelled(event: TaskEvent) {
    state.value.endTime = event.timestamp * 1000
    currentAgent.value = null
    if (timer) {
      clearInterval(timer)
      timer = null
    }

    // 标记所有运行中的智能体为失败
    state.value.agents.forEach((agent: any) => {
      if (agent.status === 'running') {
        agent.status = 'failed'
        agent.endTime = event.timestamp * 1000
      }
    })
  }

  /**
   * 处理智能体失败
   */
  function handleAgentFailed(event: TaskEvent) {
    const { agent_slug } = event.data
    const agent = state.value.agents.get(agent_slug as string)

    if (agent) {
      agent.status = 'failed'
      agent.endTime = event.timestamp * 1000
    }

    // 如果当前智能体失败，清除当前智能体
    if (currentAgent.value === agent_slug) {
      currentAgent.value = null
    }
  }

  /**
   * 处理进度更新
   */
  function handleProgressUpdate(event: TaskEvent) {
    const { progress, phase } = event.data
    if (typeof progress === 'number') {
      state.value.progress = Math.min(Math.max(progress, 0), 100)
    }
    if (typeof phase === 'number') {
      state.value.currentPhase = phase
    }
  }

  /**
   * 处理阶段智能体列表
   */
  function handlePhaseAgents(event: TaskEvent) {
    const { agents, phase } = event.data
    console.log('[AnalysisProgress] Received phase agents:', agents, 'Phase:', phase)
    if (Array.isArray(agents)) {
      // 更新当前阶段的智能体列表
      agents.forEach((agent: any) => {
        const { slug, name } = agent
        
        // 获取显示名称
        const displayName = getAgentDisplayName(slug, name)
        
        if (!state.value.agents.has(slug)) {
          state.value.agents.set(slug, {
            slug: slug || 'unknown',
            name: displayName,
            status: 'pending',
            startTime: null,
            endTime: null,
          })
        } else {
           // 如果已存在，更新名称（可能从配置加载时名字是旧的）
           const existing = state.value.agents.get(slug)
           if (existing) {
             existing.name = displayName
           }
        }
      })
    }
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
    now.value = Date.now()
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
    completedAgents,
    allAgents,
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
