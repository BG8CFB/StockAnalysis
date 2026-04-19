/**
 * 智能体配置查询 API（按阶段）
 *
 * 后端只有 GET /api/trading-agents/agent-config 获取全部配置。
 * 本模块提供按阶段过滤的便捷函数，内部调用 agents.ts 的 getAgentConfig。
 */

import { getAgentConfig } from './agents'
import type { AgentConfigResponse, Phase1Config, Phase2Config, Phase3Config, Phase4Config } from './agents'

/** 阶段编号到阶段键名的映射 */
const PHASE_KEYS = {
  1: 'phase1',
  2: 'phase2',
  3: 'phase3',
  4: 'phase4',
} as const

/** 阶段配置联合类型 */
export type PhaseConfig = Phase1Config | Phase2Config | Phase3Config | Phase4Config

/**
 * 获取指定阶段的智能体配置
 *
 * 调用后端 GET /api/trading-agents/agent-config 获取全部配置，
 * 然后客户端按 phase 过滤返回对应阶段数据。
 *
 * @param phase 阶段编号 (1-4)
 * @param includePrompts 是否包含提示词（仅管理员生效）
 * @returns 该阶段的配置数据，如果不存在返回 null
 */
export async function getPhaseConfig(
  phase: 1 | 2 | 3 | 4,
  includePrompts = false,
): Promise<PhaseConfig | null> {
  const config = await getAgentConfig(includePrompts)
  const key = PHASE_KEYS[phase]
  return (config as unknown as Record<string, unknown>)[key] as PhaseConfig | null
}

/**
 * 获取完整智能体配置（所有阶段）
 *
 * @param includePrompts 是否包含提示词（仅管理员生效）
 * @returns 完整的用户智能体配置
 */
export async function getFullAgentConfig(includePrompts = false): Promise<AgentConfigResponse> {
  return getAgentConfig(includePrompts)
}

// 重导出类型供外部使用
export type { AgentConfigResponse, Phase1Config, Phase2Config, Phase3Config, Phase4Config }
