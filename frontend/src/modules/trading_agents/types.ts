/**
 * TradingAgents 模块类型定义
 */

// =============================================================================
// 枚举类型
// =============================================================================

export enum RecommendationEnum {
  BUY = '买入',
  SELL = '卖出',
  HOLD = '持有',
}

export enum RiskLevelEnum {
  HIGH = '高',
  MEDIUM = '中',
  LOW = '低',
}

export enum TaskStatusEnum {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  STOPPED = 'stopped',
  EXPIRED = 'expired',
}

export enum MCPServerStatusEnum {
  AVAILABLE = 'available',
  UNAVAILABLE = 'unavailable',
  UNKNOWN = 'unknown',
}

export enum TransportModeEnum {
  STDIO = 'stdio',
  SSE = 'sse',
  HTTP = 'http',
}

export enum AuthTypeEnum {
  NONE = 'none',
  BEARER = 'bearer',
  BASIC = 'basic',
}

export enum ModelProviderEnum {
  ZHIPU = 'zhipu',
  DEEPSEEK = 'deepseek',
  QWEN = 'qwen',
  OPENAI = 'openai',
  OLLAMA = 'ollama',
  CUSTOM = 'custom',
}

export enum PlatformTypeEnum {
  PRESET = 'preset',   // 预设平台
  CUSTOM = 'custom',   // 自定义平台
}

export enum PresetPlatformEnum {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  AZURE_OPENAI = 'azure_openai',
  BAIDU = 'baidu',
  ALIBABA = 'alibaba',
  TENCENT = 'tencent',
  DEEPSEEK = 'deepseek',
  MOONSHOT = 'moonshot',
  ZHIPU = 'zhipu',
  ZHIPU_CODING = 'zhipu_coding',  // 智谱AI编程套餐
}

export enum StockMarketEnum {
  A_SHARE = 'a_share',      // A股
  HONG_KONG = 'hong_kong',  // 港股
  US = 'us',                // 美股
}

// =============================================================================
// AI 模型配置
// =============================================================================

export interface AIModelConfig {
  id: string
  name: string
  platform_type: PlatformTypeEnum
  platform_name?: PresetPlatformEnum
  provider?: ModelProviderEnum  // 保留兼容性
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
  is_system: boolean
  owner_id: string | null
  masked_api_key: string
  created_at: string
  updated_at: string
}

export interface AIModelConfigCreate {
  name: string
  platform_type: PlatformTypeEnum
  platform_name?: PresetPlatformEnum
  provider?: ModelProviderEnum  // 保留兼容性
  api_base_url: string
  api_key: string
  model_id: string
  custom_headers?: Record<string, string>
  max_concurrency?: number
  task_concurrency?: number
  batch_concurrency?: number
  timeout_seconds?: number
  temperature?: number
  enabled?: boolean
  is_system?: boolean
}

export interface AIModelConfigUpdate {
  name?: string
  platform_type?: PlatformTypeEnum
  platform_name?: PresetPlatformEnum
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
}

export interface AIModelTestRequest {
  api_base_url: string
  api_key: string
  model_id: string
  timeout_seconds?: number
}

export interface ConnectionTestResponse {
  success: boolean
  message: string
  latency_ms?: number
  details?: Record<string, unknown>
}

export interface ListModelsRequest {
  platform_type: PlatformTypeEnum
  platform_name?: PresetPlatformEnum
  api_base_url: string
  api_key: string
  custom_headers?: Record<string, string>
  timeout_seconds?: number
}

export interface ModelInfo {
  id: string
  name?: string
  created_at?: number
  owned_by?: string
}

export interface ListModelsResponse {
  success: boolean
  message: string
  models: ModelInfo[]
  is_from_api: boolean
  fallback_used: boolean
}

// =============================================================================
// MCP 服务器配置
// =============================================================================

export interface MCPServerConfig {
  id: string
  name: string
  transport: TransportModeEnum
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>  // HTTP 请求头（用于认证等）
  auth_type: AuthTypeEnum
  auth_token?: string
  auto_approve: string[]
  enabled: boolean
  is_system: boolean
  owner_id: string | null
  status: MCPServerStatusEnum
  last_check_at: string | null
  created_at: string
  updated_at: string
}

export interface MCPServerConfigCreate {
  name: string
  transport: TransportModeEnum
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>  // HTTP 请求头（用于认证等）
  auth_type?: AuthTypeEnum
  auth_token?: string
  auto_approve?: string[]
  enabled?: boolean
  is_system?: boolean
}

export interface MCPServerConfigUpdate {
  name?: string
  transport?: TransportModeEnum
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>  // HTTP 请求头（用于认证等）
  auth_type?: AuthTypeEnum
  auth_token?: string
  auto_approve?: string[]
  enabled?: boolean
}

export interface MCPTool {
  name: string
  description?: string
  input_schema?: Record<string, unknown>
}

// =============================================================================
// 智能体配置
// =============================================================================

/**
 * 单个智能体配置
 * role_definition 可选，以支持精简模式（不暴露提示词给普通用户）
 */
export interface AgentConfig {
  slug: string
  name: string
  role_definition?: string  // 可选：非管理员用户获取的配置不含此字段
  when_to_use: string
  enabled_mcp_servers: string[]
  enabled_local_tools: string[]
  enabled: boolean
}

/**
 * 阶段配置基础模型（不含 model_id，模型选择与智能体配置分离）
 */
export interface Phase1Config {
  enabled: boolean
  max_rounds: number
  max_concurrency: number
  agents: AgentConfig[]
}

export interface Phase2Config {
  enabled: boolean
  max_rounds: number
  agents: AgentConfig[]
}

export interface Phase3Config {
  enabled: boolean
  max_rounds: number
  agents: AgentConfig[]
}

export interface Phase4Config {
  enabled: boolean
  max_rounds: number
  agents: AgentConfig[]
}

export interface UserAgentConfig {
  id: string
  user_id: string
  is_public: boolean
  is_customized: boolean
  phase1: Phase1Config
  phase2?: Phase2Config | null
  phase3?: Phase3Config | null
  phase4?: Phase4Config | null
  created_at: string
  updated_at: string
}

export interface UserAgentConfigUpdate {
  phase1?: Phase1Config
  phase2?: Phase2Config | null
  phase3?: Phase3Config | null
  phase4?: Phase4Config | null
}

// =============================================================================
// 分析任务 - 新的阶段配置
// =============================================================================

// 第一阶段智能体定义
export interface Stage1Agent {
  id: string
  name: string
}

// 第一阶段配置（用户选择具体智能体）
export interface Stage1Config {
  enabled: boolean
  selected_agents: string[]  // 选中的智能体ID列表
}

// 第二/三阶段辩论配置
export interface DebateConfig {
  enabled: boolean
  rounds: number  // 辩论轮数 1-10
}

// 第二阶段配置
export interface Stage2Config {
  enabled: boolean
  debate: DebateConfig
}

// 第三阶段配置
export interface Stage3Config {
  enabled: boolean
  debate: DebateConfig
}

// 第四阶段配置（强制启用）
export interface Stage4Config {
  enabled: true  // 固定为 true
}

// 创建分析任务的阶段配置
export interface AnalysisStagesConfig {
  stage1: Stage1Config
  stage2: Stage2Config
  stage3: Stage3Config
  stage4: Stage4Config
}

export interface AnalysisTask {
  id: string
  user_id: string
  stock_code: string
  market: StockMarketEnum
  trade_date: string
  status: TaskStatusEnum
  current_phase: number
  current_agent: string | null
  progress: number
  reports: Record<string, string>
  final_report?: string
  final_recommendation: RecommendationEnum | null
  buy_price: number | null
  sell_price: number | null
  token_usage?: TokenUsage
  risk_level?: string
  error_message: string | null
  error_details: Record<string, unknown> | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  expired_at: string | null
  batch_id: string | null
}

export interface BatchTask {
  id: string
  user_id: string
  stock_codes: string[]
  market: StockMarketEnum
  total_count: number
  completed_count: number
  failed_count: number
  status: TaskStatusEnum
  created_at: string
  completed_at: string | null
}

// =============================================================================
// 统一任务创建类型
// =============================================================================

export interface UnifiedTaskCreate {
  stock_codes: string[]  // 1-50个股票代码
  market: StockMarketEnum
  trade_date: string
  data_collection_model?: string  // 数据收集阶段模型ID（第一阶段）
  debate_model?: string  // 辩论和总结阶段模型ID（第二三四阶段）
  stages: AnalysisStagesConfig
}

export interface UnifiedTaskResponse {
  task_id: string | null  // 单股分析时返回
  batch_id: string | null  // 批量分析时返回
  stock_codes: string[]
  total_count: number
  message: string
}

// =============================================================================
// Token 使用统计
// =============================================================================

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

// =============================================================================
// WebSocket 事件
// =============================================================================

export interface TaskEvent {
  event_type: string
  task_id: string
  timestamp: number
  data: Record<string, unknown>
}

// =============================================================================
// 分析报告
// =============================================================================

export interface AnalysisReport {
  id: string
  task_id: string
  user_id: string
  stock_code: string
  trade_date: string
  final_report: string
  recommendation: RecommendationEnum | null
  buy_price: number | null
  sell_price: number | null
  risk_level: RiskLevelEnum | null
  token_usage?: TokenUsage
  created_at: string
}

export interface ReportSummary {
  total_reports: number
  buy_count: number
  sell_count: number
  hold_count: number
  avg_buy_price: number | null
  avg_sell_price: number | null
  total_token_usage: number
  recommendation_distribution: {
    buy: number
    sell: number
    hold: number
  }
}

// =============================================================================
// WebSocket 事件
// =============================================================================

export interface TaskEvent {
  event_type: string
  task_id: string
  timestamp: number
  data: Record<string, unknown>
}

export type TaskEventHandler = (event: TaskEvent) => void

// =============================================================================
// 提供商预设配置
// =============================================================================

export interface ProviderPreset {
  name: string
  value: ModelProviderEnum
  defaultBaseUrl: string
  exampleModelId: string
}

export const PROVIDER_PRESETS: Record<ModelProviderEnum, ProviderPreset> = {
  [ModelProviderEnum.ZHIPU]: {
    name: '智谱AI',
    value: ModelProviderEnum.ZHIPU,
    defaultBaseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    exampleModelId: 'glm-4',
  },
  [ModelProviderEnum.DEEPSEEK]: {
    name: 'DeepSeek',
    value: ModelProviderEnum.DEEPSEEK,
    defaultBaseUrl: 'https://api.deepseek.com/v1',
    exampleModelId: 'deepseek-chat',
  },
  [ModelProviderEnum.QWEN]: {
    name: '通义千问',
    value: ModelProviderEnum.QWEN,
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    exampleModelId: 'qwen-turbo',
  },
  [ModelProviderEnum.OPENAI]: {
    name: 'OpenAI',
    value: ModelProviderEnum.OPENAI,
    defaultBaseUrl: 'https://api.openai.com/v1',
    exampleModelId: 'gpt-4',
  },
  [ModelProviderEnum.OLLAMA]: {
    name: 'Ollama',
    value: ModelProviderEnum.OLLAMA,
    defaultBaseUrl: 'http://localhost:11434/v1',
    exampleModelId: 'llama2',
  },
  [ModelProviderEnum.CUSTOM]: {
    name: '自定义',
    value: ModelProviderEnum.CUSTOM,
    defaultBaseUrl: '',
    exampleModelId: '',
  },
}

// =============================================================================
// TradingAgents 设置类型
// =============================================================================

export interface TradingAgentsSettings {
  // AI 模型配置
  data_collection_model_id: string
  debate_model_id: string

  // 辩论配置
  default_debate_rounds: number
  max_debate_rounds: number

  // 超时配置
  phase_timeout_minutes: number
  agent_timeout_minutes: number
  tool_timeout_seconds: number

  // 其他配置
  task_expiry_hours: number
  archive_days: number
  enable_loop_detection: boolean
  enable_progress_events: boolean
}

export interface TradingAgentsSettingsResponse {
  id: string
  user_id: string
  settings: TradingAgentsSettings
  created_at: string
  updated_at: string
}
