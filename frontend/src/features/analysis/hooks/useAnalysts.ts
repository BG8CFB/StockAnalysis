import { useState, useEffect, useCallback } from 'react'
import type { AgentConfig } from '@/services/api/agents'
import { getFullAgentConfig } from '@/services/api/agent-configs'

interface UseAnalystsReturn {
  analysts: AgentConfig[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export function useAnalysts(): UseAnalystsReturn {
  const [analysts, setAnalysts] = useState<AgentConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const config = await getFullAgentConfig(true)
      // 从所有阶段收集 enabled 的智能体
      const allAgents: AgentConfig[] = [
        ...(config.phase1?.agents ?? []),
        ...(config.phase2?.agents ?? []),
        ...(config.phase3?.agents ?? []),
        ...(config.phase4?.agents ?? []),
      ]
      setAnalysts(allAgents.filter(a => a.enabled))
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
