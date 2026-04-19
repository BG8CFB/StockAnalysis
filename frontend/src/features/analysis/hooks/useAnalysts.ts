import { useState, useEffect, useCallback } from 'react'
import type { AgentConfig } from '@/services/api/agents'
import { getFullAgentConfig } from '@/services/api/agent-configs'

interface UseAnalystsReturn {
  analysts: AgentConfig[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * 获取第一阶段的分析师列表
 * 仅返回 Phase 1（信息收集与基础分析）的智能体，不含其他阶段
 */
export function useAnalysts(): UseAnalystsReturn {
  const [analysts, setAnalysts] = useState<AgentConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const config = await getFullAgentConfig(true)
      // 仅获取第一阶段的分析师
      const phase1Agents = (config.phase1?.agents ?? []).filter((a) => a.enabled)
      setAnalysts(phase1Agents)
    } catch (err) {
      setAnalysts([])
      const msg = err instanceof Error ? err.message : '获取分析师列表失败'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    analysts,
    loading,
    error,
    refresh,
  }
}
