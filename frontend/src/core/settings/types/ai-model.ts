/**
 * AI 模型相关类型定义
 */

export enum ModelProviderEnum {
  ZHIPU = 'zhipu',
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  DEEPSEEK = 'deepseek',
  QWEN = 'qwen',
  MOONSHOT = 'moonshot',
  CUSTOM = 'custom',
}

export enum PlatformTypeEnum {
  PRESET = 'preset',
  CUSTOM = 'custom',
}

export enum PresetPlatformEnum {
  ZHIPU = 'zhipu',
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  DEEPSEEK = 'deepseek',
  QWEN = 'qwen',
  MOONSHOT = 'moonshot',
}

// 思考模式已简化：只使用 thinking_enabled 布尔值
// 保留枚举用于向后兼容
export enum ThinkingModeEnum {
  PRESERVED = 'preserved',
  CLEAR_ON_NEW = 'clear_on_new',
  AUTO = 'auto',
}

export interface AIModelConfig {
  id: string
  name: string
  platform_type: PlatformTypeEnum
  platform_name?: string
  provider?: ModelProviderEnum
  api_base_url: string
  api_key: string
  model_id: string
  custom_headers?: Record<string, string>
  max_concurrency: number
  task_concurrency: number
  batch_concurrency: number
  timeout_seconds: number
  temperature: number
  enabled: boolean
  thinking_enabled?: boolean
  // 保留向后兼容
  thinking_mode?: ThinkingModeEnum | null
  custom_input_price?: number | null
  custom_output_price?: number | null
  custom_thinking_price?: number | null
  is_system: boolean
  owner_id?: string
  created_at: string
  updated_at: string
}

export interface AIModelConfigCreate {
  name: string
  platform_type: PlatformTypeEnum
  platform_name?: string
  provider?: ModelProviderEnum
  api_base_url: string
  api_key: string
  model_id: string
  custom_headers?: Record<string, string>
  max_concurrency: number
  task_concurrency: number
  batch_concurrency: number
  timeout_seconds: number
  temperature: number
  enabled: boolean
  thinking_enabled?: boolean
  // 保留向后兼容
  thinking_mode?: ThinkingModeEnum | null
  custom_input_price?: number | null
  custom_output_price?: number | null
  custom_thinking_price?: number | null
  is_system: boolean
}

export interface AIModelConfigUpdate {
  name?: string
  platform_type?: PlatformTypeEnum
  platform_name?: string
  provider?: ModelProviderEnum
  api_base_url?: string
  api_key?: string
  model_id?: string
  custom_headers?: Record<string, string>
  max_concurrency?: number
  task_concurrency?: number
  batch_concurrency?: number
  timeout_seconds?: number
  temperature?: number
  enabled?: boolean
  thinking_enabled?: boolean
  // 保留向后兼容
  thinking_mode?: ThinkingModeEnum | null
  custom_input_price?: number | null
  custom_output_price?: number | null
  custom_thinking_price?: number | null
}

export interface AIModelTestRequest {
  platform_type: PlatformTypeEnum
  platform_name?: string
  api_base_url: string
  api_key: string
  model_id?: string
  custom_headers?: Record<string, string>
}

export interface ConnectionTestResponse {
  success: boolean
  message: string
  latency_ms?: number
  details?: Record<string, unknown>
}

export interface ListModelsRequest {
  platform_type: PlatformTypeEnum
  platform_name?: string
  api_base_url: string
  api_key: string
  custom_headers?: Record<string, string>
}

export interface ListModelsResponse {
  success: boolean
  message: string
  models: Array<{ id: string; name?: string }>
}

// 提供商预设配置
export const PROVIDER_PRESETS: Record<ModelProviderEnum, { name: string; icon?: string }> = {
  [ModelProviderEnum.ZHIPU]: { name: '智谱 AI' },
  [ModelProviderEnum.OPENAI]: { name: 'OpenAI' },
  [ModelProviderEnum.ANTHROPIC]: { name: 'Anthropic' },
  [ModelProviderEnum.DEEPSEEK]: { name: 'DeepSeek' },
  [ModelProviderEnum.QWEN]: { name: '通义千问' },
  [ModelProviderEnum.MOONSHOT]: { name: 'Moonshot AI' },
  [ModelProviderEnum.CUSTOM]: { name: '自定义' },
}
