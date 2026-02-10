/**
 * Token 消耗追踪 Composable
 * 用于追踪和分析 LLM Token 消耗情况
 *
 * @see docs/design.md 第1522行
 * @see docs/tasks.md 第449-453行 Token 追踪功能
 */
import { ref, computed } from 'vue'
import type { AnalysisTask, TokenUsage } from '../types'

// Token 使用统计（内部使用 camelCase）
export interface TokenUsageStats {
  promptTokens: number
  completionTokens: number
  totalTokens: number
}

// 智能体级别的 Token 使用
export interface AgentTokenUsage {
  agentSlug: string
  agentName: string
  phase: number
  tokenUsage: TokenUsageStats
}

// Token 使用详情
export interface TokenUsageDetail {
  taskId: string
  totalUsage: TokenUsageStats
  agentBreakdown: AgentTokenUsage[]
  estimatedCost: number
  currency: string
}

/**
 * Token 追踪 Composable
 */
export function useTokenUsage(initialTask?: AnalysisTask) {
  // Token 使用统计
  const promptTokens = ref<number>(initialTask?.token_usage?.prompt_tokens || 0)
  const completionTokens = ref<number>(initialTask?.token_usage?.completion_tokens || 0)
  const totalTokens = ref<number>(initialTask?.token_usage?.total_tokens || 0)

  // 智能体级别的 Token 使用
  const agentBreakdown = ref<AgentTokenUsage[]>([])

  // 是否启用成本估算
  const enableCostEstimation = ref(true)

  // 货币单位
  const currency = ref('CNY')

  // 当前使用的模型 ID（用于计算成本）
  const currentModelId = ref<string | null>(null)

  // Token 价格配置（每 1K tokens 的价格）
  // 格式：{ 模型ID: { input: 输入单价, output: 输出单价, currency: 货币单位 } }
  const modelPricing = ref<Record<string, { input: number; output: number; currency: string }>>({
    // 智谱 AI (glm-4 系列)
    'glm-4.6': { input: 0.01, output: 0.01, currency: 'CNY' },
    'glm-4-plus': { input: 0.05, output: 0.05, currency: 'CNY' },
    'glm-4': { input: 0.01, output: 0.01, currency: 'CNY' },
    'glm-3-turbo': { input: 0.005, output: 0.005, currency: 'CNY' },

    // OpenAI
    'gpt-4o': { input: 0.0025, output: 0.01, currency: 'USD' },
    'gpt-4o-mini': { input: 0.00015, output: 0.0006, currency: 'USD' },
    'gpt-4-turbo': { input: 0.01, output: 0.03, currency: 'USD' },
    'gpt-4': { input: 0.03, output: 0.06, currency: 'USD' },
    'gpt-3.5-turbo': { input: 0.0005, output: 0.0015, currency: 'USD' },

    // Anthropic Claude
    'claude-sonnet-4': { input: 0.003, output: 0.015, currency: 'USD' },
    'claude-haiku-4': { input: 0.00025, output: 0.00125, currency: 'USD' },
    'claude-opus-3': { input: 0.015, output: 0.075, currency: 'USD' },
    'claude-sonnet-3': { input: 0.003, output: 0.015, currency: 'USD' },
    'claude-haiku-3': { input: 0.00025, output: 0.00125, currency: 'USD' },

    // DeepSeek
    'deepseek-chat': { input: 0.00014, output: 0.00028, currency: 'USD' },
    'deepseek-reasoner': { input: 0.00055, output: 0.0011, currency: 'USD' },

    // 阿里通义千问
    'qwen-turbo': { input: 0.0003, output: 0.0006, currency: 'USD' },
    'qwen-plus': { input: 0.0008, output: 0.002, currency: 'USD' },
    'qwen-max': { input: 0.002, output: 0.008, currency: 'USD' },

    // 本地模型（免费）
    'ollama': { input: 0, output: 0, currency: 'USD' },
    'local': { input: 0, output: 0, currency: 'USD' },

    // 默认配置（兜底）
    'default': { input: 0.001, output: 0.002, currency: 'CNY' },
  })

  // 计算属性：总 Token 数
  const totalUsage = computed<TokenUsageStats>(() => ({
    promptTokens: promptTokens.value,
    completionTokens: completionTokens.value,
    totalTokens: totalTokens.value,
  }))

  // 计算属性：Token 比例
  const tokenRatio = computed(() => {
    if (totalTokens.value === 0) return { prompt: 0, completion: 0 }
    return {
      prompt: Math.round((promptTokens.value / totalTokens.value) * 100),
      completion: Math.round((completionTokens.value / totalTokens.value) * 100),
    }
  })

  // 计算属性：估算成本
  // 根据当前使用的模型计算成本，支持多模型混合使用
  const estimatedCost = computed(() => {
    if (!enableCostEstimation.value) return 0

    // 获取当前模型的定价，如果没有则使用默认
    const modelId = currentModelId.value || 'default'
    const pricing = modelPricing.value[modelId] || modelPricing.value.default

    // 如果有智能体级别的 Token 使用明细，按各模型分别计算后相加
    if (agentBreakdown.value.length > 0) {
      // 按模型分组计算成本
      const modelCosts: Record<string, number> = {}

      agentBreakdown.value.forEach((agent) => {
        // 尝试从 agent slug 中提取模型标识
        const modelKey = extractModelKey(agent.agentSlug)
        const agentPricing = modelPricing.value[modelKey] || modelPricing.value.default

        const cost = (agent.tokenUsage.promptTokens / 1000) * agentPricing.input +
                     (agent.tokenUsage.completionTokens / 1000) * agentPricing.output

        modelCosts[modelKey] = (modelCosts[modelKey] || 0) + cost
      })

      // 计算总成本
      const totalCost = Object.values(modelCosts).reduce((sum, cost) => sum + cost, 0)
      return parseFloat(totalCost.toFixed(4))
    }

    // 没有明细时，使用当前模型的定价
    const cost = (promptTokens.value / 1000) * pricing.input +
                 (completionTokens.value / 1000) * pricing.output

    return parseFloat(cost.toFixed(4))
  })

  // 计算属性：格式化的成本字符串（根据货币单位格式化）
  const formattedCost = computed(() => {
    const modelId = currentModelId.value || 'default'
    const pricing = modelPricing.value[modelId] || modelPricing.value.default

    if (pricing.currency === 'USD') {
      return `$${estimatedCost.value.toFixed(4)}`
    }
    return `¥${estimatedCost.value.toFixed(4)}`
  })

  // 计算属性：当前使用的货币单位
  const currentCurrency = computed(() => {
    const modelId = currentModelId.value || 'default'
    return modelPricing.value[modelId]?.currency || 'CNY'
  })

  // 计算属性：是否超过警告阈值（100K tokens）
  const isOverThreshold = computed(() => {
    return totalTokens.value > 100000
  })

  // 计算属性：阈值进度
  const thresholdProgress = computed(() => {
    return Math.min((totalTokens.value / 100000) * 100, 100)
  })

  // 计算属性：智能体 Token 排行
  const agentRanking = computed(() => {
    return [...agentBreakdown.value].sort((a, b) =>
      b.tokenUsage.totalTokens - a.tokenUsage.totalTokens
    )
  })

  // 计算属性：按阶段分组的 Token 使用
  const usageByPhase = computed(() => {
    const phaseMap = new Map<number, TokenUsageStats>()

    agentBreakdown.value.forEach((agent) => {
      const existing = phaseMap.get(agent.phase) || {
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
      }

      existing.promptTokens += agent.tokenUsage.promptTokens
      existing.completionTokens += agent.tokenUsage.completionTokens
      existing.totalTokens += agent.tokenUsage.totalTokens

      phaseMap.set(agent.phase, existing)
    })

    return phaseMap
  })

  /**
   * 更新 Token 使用量（从后端 TokenUsage 格式）
   */
  function updateTokenUsage(usage: TokenUsage) {
    promptTokens.value = usage.prompt_tokens
    completionTokens.value = usage.completion_tokens
    totalTokens.value = usage.total_tokens
  }

  /**
   * 更新 Token 使用量（从内部 TokenUsageStats 格式）
   */
  function updateTokenUsageStats(usage: TokenUsageStats) {
    promptTokens.value = usage.promptTokens
    completionTokens.value = usage.completionTokens
    totalTokens.value = usage.totalTokens
  }

  /**
   * 增加 Token 使用量
   */
  function addTokenUsage(prompt: number, completion: number) {
    promptTokens.value += prompt
    completionTokens.value += completion
    totalTokens.value = prompt + completion
  }

  /**
   * 添加智能体级别的 Token 使用
   */
  function addAgentTokenUsage(agent: AgentTokenUsage) {
    agentBreakdown.value.push(agent)

    // 同时更新总量
    addTokenUsage(
      agent.tokenUsage.promptTokens,
      agent.tokenUsage.completionTokens
    )
  }

  /**
   * 从智能体 slug 中提取模型标识
   * 例如: "technical-analyst-glm-4.6" -> "glm-4.6"
   */
  function extractModelKey(agentSlug: string): string {
    // 常见模型标识模式
    const modelPatterns = [
      /-(glm-\d[\w-]*)/,  // glm-4.6, glm-4-plus
      /-(gpt-4[\w-]*)/,   // gpt-4o, gpt-4-turbo
      /-(claude-[\w-]+)/,  // claude-sonnet-4, claude-haiku-3
      /-(deepseek-[\w-]+)/, // deepseek-chat
      /-(qwen-[\w-]+)/,   // qwen-turbo, qwen-plus
    ]

    for (const pattern of modelPatterns) {
      const match = agentSlug.match(pattern)
      if (match) {
        return match[1]
      }
    }

    // 兜底：返回原始 slug 的最后一部分作为标识
    const parts = agentSlug.split('-')
    return parts[parts.length - 1] || 'default'
  }

  /**
   * 设置当前使用的模型（用于成本计算）
   * @param modelId 模型 ID，如 'glm-4.6'、'gpt-4o' 等
   */
  function setCurrentModel(modelId: string | null) {
    currentModelId.value = modelId
  }

  /**
   * 根据模型提供商估算成本
   * @deprecated 请使用 setCurrentModel + estimatedCost
   */
  function estimateCostForModel(provider: string): number {
    const prices = modelPricing.value[provider] || modelPricing.value.default
    const cost = (promptTokens.value / 1000) * prices.input +
                 (completionTokens.value / 1000) * prices.output
    return parseFloat(cost.toFixed(4))
  }

  /**
   * 重置统计数据
   */
  function reset() {
    promptTokens.value = 0
    completionTokens.value = 0
    totalTokens.value = 0
    agentBreakdown.value = []
  }

  /**
   * 格式化 Token 数量
   */
  function formatTokenCount(count: number): string {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`
    }
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`
    }
    return count.toString()
  }

  /**
   * 获取使用详情
   */
  function getDetail(taskId: string): TokenUsageDetail {
    return {
      taskId,
      totalUsage: totalUsage.value,
      agentBreakdown: agentBreakdown.value,
      estimatedCost: estimatedCost.value,
      currency: currency.value,
    }
  }

  /**
   * 导出为 CSV
   */
  function exportToCSV(): string {
    const headers = ['Agent', 'Phase', 'Prompt Tokens', 'Completion Tokens', 'Total Tokens']
    const rows = agentBreakdown.value.map((agent) => [
      agent.agentName,
      `Phase ${agent.phase}`,
      agent.tokenUsage.promptTokens.toString(),
      agent.tokenUsage.completionTokens.toString(),
      agent.tokenUsage.totalTokens.toString(),
    ])

    const csv = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
      '',
      'Total',
      '',
      promptTokens.value.toString(),
      completionTokens.value.toString(),
      totalTokens.value.toString(),
    ].join('\n')

    return csv
  }

  return {
    // 状态
    promptTokens,
    completionTokens,
    totalTokens,
    agentBreakdown,
    enableCostEstimation,
    currency,
    currentModelId,
    modelPricing,

    // 计算属性
    totalUsage,
    tokenRatio,
    estimatedCost,
    formattedCost,
    currentCurrency,
    isOverThreshold,
    thresholdProgress,
    agentRanking,
    usageByPhase,

    // 方法
    updateTokenUsage,
    updateTokenUsageStats,
    addTokenUsage,
    addAgentTokenUsage,
    setCurrentModel,
    extractModelKey,
    estimateCostForModel,
    reset,
    formatTokenCount,
    getDetail,
    exportToCSV,
  }
}

/**
 * Token 使用历史管理
 */
export function useTokenHistory() {
  // 存储历史记录
  const history = ref<Map<string, TokenUsageDetail>>(new Map())

  /**
   * 添加历史记录
   */
  function addHistory(taskId: string, detail: TokenUsageDetail) {
    history.value.set(taskId, detail)
  }

  /**
   * 获取历史记录
   */
  function getHistory(taskId: string): TokenUsageDetail | undefined {
    return history.value.get(taskId)
  }

  /**
   * 获取所有历史记录
   */
  function getAllHistory(): TokenUsageDetail[] {
    return Array.from(history.value.values())
  }

  /**
   * 计算总 Token 使用
   */
  function getTotalUsage(): TokenUsageStats {
    let promptTokens = 0
    let completionTokens = 0
    let totalTokens = 0

    history.value.forEach((detail) => {
      promptTokens += detail.totalUsage.promptTokens
      completionTokens += detail.totalUsage.completionTokens
      totalTokens += detail.totalUsage.totalTokens
    })

    return { promptTokens, completionTokens, totalTokens }
  }

  /**
   * 计算总成本
   */
  function getTotalCost(): number {
    let cost = 0
    history.value.forEach((detail) => {
      cost += detail.estimatedCost
    })
    return parseFloat(cost.toFixed(2))
  }

  /**
   * 清除历史记录
   */
  function clearHistory() {
    history.value.clear()
  }

  /**
   * 删除单条记录
   */
  function removeHistory(taskId: string) {
    history.value.delete(taskId)
  }

  return {
    history,
    addHistory,
    getHistory,
    getAllHistory,
    getTotalUsage,
    getTotalCost,
    clearHistory,
    removeHistory,
  }
}
