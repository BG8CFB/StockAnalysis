/**
 * 智能体配置查询 API
 *
 * 后端只有 GET /api/trading-agents/agent-config 获取全部配置。
 * 本模块提供完整配置查询的便捷函数。
 */

import { getAgentConfig } from './agents'
import type { AgentConfigResponse, Phase1Config, Phase2Config, Phase3Config, Phase4Config } from './agents'

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
