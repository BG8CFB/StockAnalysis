<template>
  <div class="batch-analysis-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon class="header-icon" :size="28">
          <DataLine />
        </el-icon>
        <div>
          <h2>批量分析</h2>
          <p class="description">
            输入多只股票代码，批量进行深度分析
          </p>
        </div>
      </div>
    </div>

    <!-- 主内容区：左右两栏布局 -->
    <div class="main-content-grid">
      <!-- 左侧列：主要内容 -->
      <div class="left-column">
        <!-- 股票输入卡片 -->
        <el-card class="section-card stock-input-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><Tickets /></el-icon>
                股票信息
              </span>
              <el-tag type="danger" size="small">必填</el-tag>
            </div>
          </template>
          <el-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            label-position="top"
          >
            <!-- 股票代码：单独占一行 -->
            <el-form-item label="股票代码" prop="stock_codes">
              <el-input
                v-model="codesText"
                type="textarea"
                :rows="5"
                placeholder="每行一个股票代码，例如：&#10;000001&#10;600000&#10;300001"
                clearable
              />
              <div class="form-tip">
                已输入 {{ codesList.length }} 个股票代码（最多 50 个）
              </div>
            </el-form-item>

            <!-- 市场类型 + 交易日期：同一行 -->
            <div class="stock-form-row">
              <el-form-item label="股票市场" prop="market" class="form-item-flex">
                <el-select
                  v-model="formData.market"
                  placeholder="选择市场"
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="item in marketOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="交易日期" prop="trade_date" class="form-item-flex">
                <el-date-picker
                  v-model="formData.trade_date"
                  type="date"
                  placeholder="选择日期"
                  :disabled-date="disabledDate"
                  value-format="YYYY-MM-DD"
                  size="large"
                  style="width: 100%"
                />
              </el-form-item>
            </div>
          </el-form>
        </el-card>

        <!-- 分析师团队卡片 -->
        <el-card class="section-card analyst-card">
      <template #header>
        <div class="card-header">
          <span class="header-title">
            <el-icon><User /></el-icon>
            分析师团队
            <span class="subtitle">选择第一阶段参与的分析师（至少1个）</span>
          </span>
          <el-tag type="info" size="plain">
            已选 {{ stagesConfig.stage1.selected_agents.length }}/{{ activeAnalysts.length }}
          </el-tag>
        </div>
      </template>

      <div
        v-loading="loadingConfig"
        class="agents-grid"
      >
        <div
          v-for="agent in activeAnalysts"
          :key="agent.slug"
          class="agent-card"
          :class="{ 'agent-selected': stagesConfig.stage1.selected_agents.includes(agent.slug) }"
          @click="toggleAgent(agent.slug)"
        >
          <div class="agent-icon-wrapper">
            <el-icon :size="20">
              <component :is="getAgentIcon(agent.slug)" />
            </el-icon>
          </div>
          <div class="agent-info">
            <div class="agent-name">
              {{ agent.name }}
            </div>
            <div class="agent-when" :title="agent.when_to_use || ''">
              {{ agent.when_to_use || '适用场景：—' }}
            </div>
          </div>
          <div class="agent-status">
            <el-icon v-if="stagesConfig.stage1.selected_agents.includes(agent.slug)" color="#409eff">
              <CircleCheckFilled />
            </el-icon>
            <el-icon v-else color="#dcdfe6">
              <CircleCheck />
            </el-icon>
          </div>
        </div>
      </div>

      <div v-if="!loadingConfig && activeAnalysts.length === 0" class="validation-hint">
        <el-icon color="#f56c6c"><WarningFilled /></el-icon>
        <span>未获取到第一阶段智能体，请到「智能体管理」启用</span>
      </div>
      <div v-if="stagesConfig.stage1.selected_agents.length === 0" class="validation-hint">
        <el-icon color="#f56c6c"><WarningFilled /></el-icon>
        <span>请至少选择一个智能体</span>
      </div>
    </el-card>

        <!-- 深度分析阶段卡片 -->
        <el-card class="section-card stages-card">
      <template #header>
        <div class="card-header">
          <span class="header-title">
            <el-icon><DataAnalysis /></el-icon>
            深度分析阶段
            <span class="subtitle">配置后续分析流程（第四阶段为必需）</span>
          </span>
          <el-tag type="success" size="plain">
            <el-icon><Timer /></el-icon> 预计 {{ estimateTime }} 分钟
          </el-tag>
        </div>
      </template>

      <div class="stages-grid">
        <!-- 第二阶段 -->
        <div class="stage-item" :class="{ 'stage-enabled': stagesConfig.stage2.enabled }">
          <div class="stage-header">
            <div class="stage-info">
              <span class="stage-number">02</span>
              <div>
                <h4 class="stage-title">双向辩论</h4>
                <p class="stage-desc">看涨/看跌分析师对抗辩论</p>
              </div>
            </div>
            <el-switch v-model="stagesConfig.stage2.enabled" @change="onStage2Change" />
          </div>
          <div v-if="stagesConfig.stage2.enabled" class="stage-detail">
            <div class="stage-tags">
              <el-tag v-for="role in ['看涨分析师', '看跌分析师', '研究部主管']" :key="role" size="small">
                {{ role }}
              </el-tag>
            </div>
            <div class="stage-config">
              <span class="label">辩论轮次:</span>
              <el-input-number v-model="stagesConfig.stage2.debate.rounds" :min="1" :max="5" size="small" controls-position="right" />
            </div>
          </div>
        </div>

        <!-- 第三阶段 -->
        <div class="stage-item" :class="{ 'stage-enabled': stagesConfig.stage3.enabled }">
          <div class="stage-header">
            <div class="stage-info">
              <span class="stage-number">03</span>
              <div>
                <h4 class="stage-title">风险管理</h4>
                <p class="stage-desc">三方风险评估与风控方案</p>
              </div>
            </div>
            <el-switch v-model="stagesConfig.stage3.enabled" @change="onStage3Change" />
          </div>
          <div v-if="stagesConfig.stage3.enabled" class="stage-detail">
            <div class="stage-tags">
              <el-tag v-for="role in ['激进派', '保守派', '中性派']" :key="role" size="small">
                {{ role }}
              </el-tag>
            </div>
            <div class="stage-config">
              <span class="label">辩论轮次:</span>
              <el-input-number v-model="stagesConfig.stage3.debate.rounds" :min="1" :max="5" size="small" controls-position="right" />
            </div>
          </div>
        </div>

        <!-- 第四阶段（必需） -->
        <div class="stage-item stage-enabled stage-required">
          <div class="stage-header">
            <div class="stage-info">
              <span class="stage-number">04</span>
              <div>
                <h4 class="stage-title">最终总结</h4>
                <p class="stage-desc">综合所有分析结果生成报告</p>
              </div>
            </div>
            <el-switch :model-value="true" disabled />
          </div>
          <div class="stage-detail">
            <div class="stage-tags">
              <el-tag size="small">总结智能体</el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-card>

        <!-- 分析预览 -->
        <el-card class="section-card preview-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><DataLine /></el-icon>
                分析预览
              </span>
            </div>
          </template>
          <div class="preview-content">
            <div class="preview-item">
              <span class="preview-label">股票数量</span>
              <el-tag type="primary" size="small">{{ codesList.length }} 只</el-tag>
            </div>
            <div class="preview-item">
              <span class="preview-label">已选分析师</span>
              <el-tag type="success" size="small">
                {{ stagesConfig.stage1.selected_agents.length }} 个
              </el-tag>
            </div>
            <div class="preview-item">
              <span class="preview-label">深度分析</span>
              <div class="preview-stages">
                <el-tag v-if="stagesConfig.stage2.enabled" type="success" size="small">
                  多维度分析
                </el-tag>
                <el-tag v-if="stagesConfig.stage3.enabled" type="warning" size="small">
                  风险管理
                </el-tag>
                <el-tag type="info" size="small">
                  最终总结
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧列：AI模型配置 + 操作按钮 -->
      <div class="right-column">
        <div class="right-sticky-wrapper">
          <!-- AI 模型配置卡片 -->
          <el-card class="config-card model-card">
            <template #header>
              <div class="card-header">
                <span class="header-title">
                  <el-icon><Cpu /></el-icon>
                  AI 模型配置
                </span>
                <el-tag type="info" size="small">可选</el-tag>
              </div>
            </template>
            <div class="model-config-grid">
              <div class="model-item">
                <label class="model-label">数据收集模型</label>
                <el-select
                  v-model="formData.data_collection_model"
                  placeholder="使用默认模型"
                  clearable
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  >
                    <span>{{ model.name }}</span>
                    <el-tag
                      size="small"
                      style="margin-left: 8px"
                      :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                    >
                      {{ getProviderLabel(model.provider) }}
                    </el-tag>
                  </el-option>
                </el-select>
                <span class="model-tip">用于数据收集、基本面分析等阶段</span>
              </div>
              <div class="model-item">
                <label class="model-label">辩论阶段模型</label>
                <el-select
                  v-model="formData.debate_model"
                  placeholder="使用默认模型"
                  clearable
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  >
                    <span>{{ model.name }}</span>
                    <el-tag
                      size="small"
                      style="margin-left: 8px"
                      :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                    >
                      {{ getProviderLabel(model.provider) }}
                    </el-tag>
                  </el-option>
                </el-select>
                <span class="model-tip">用于看涨/看跌辩论、最终总结阶段</span>
              </div>
            </div>
          </el-card>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button size="large" @click="handleReset" style="width: 100%">
              重置
            </el-button>
            <el-button
              type="primary"
              size="large"
              class="action-btn"
              :loading="submitting"
              :disabled="!canSubmit"
              @click="handleSubmit"
              style="width: 100%"
            >
              <el-icon><MagicStick /></el-icon>
              开始批量分析 ({{ codesList.length }} 只股票)
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量任务进度 -->
    <el-card
      v-if="batchTasks.length > 0 || currentBatchId"
      shadow="never"
      class="progress-card"
    >
      <template #header>
        <div class="progress-header">
          <span>批量任务进度</span>
          <el-button
            v-if="hasRunningTasks"
            type="danger"
            text
            @click="handleCancelAll"
          >
            取消全部
          </el-button>
        </div>
      </template>

      <div class="batch-progress">
        <el-progress
          :percentage="batchProgress"
          :status="batchStatus"
        >
          <span>{{ completedCount }}/{{ totalCount }}</span>
        </el-progress>
      </div>

      <div class="task-list">
        <div
          v-for="task in batchTasks"
          :key="task.id"
          class="task-item"
        >
          <div class="task-info">
            <span class="task-code">{{ task.stock_code }}</span>
            <el-tag
              :type="getStatusType(task.status)"
              size="small"
            >
              {{ getStatusLabel(task.status) }}
            </el-tag>
          </div>
          <div
            v-if="task.status === TaskStatusEnum.PENDING && taskQueuePositions[task.id]"
            class="queue-info"
          >
            <el-icon><Clock /></el-icon>
            <span>排队中，前面还有 {{ taskQueuePositions[task.id].position }} 个任务</span>
          </div>
          <div class="task-actions">
            <el-button
              v-if="task.status === TaskStatusEnum.FAILED"
              type="warning"
              text
              size="small"
              @click.stop="handleRetryTask(task.id)"
            >
              重试
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  MagicStick,
  Collection,
  Cpu,
  WarningFilled,
  CircleCheckFilled,
  CircleCheck,
  TrendCharts,
  Monitor,
  DataLine,
  Money,
  ChatLineSquare,
  DataAnalysis,
  Wallet,
  Document,
  Clock,
  User,
  Tickets,
  Timer,
} from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../../store'
import { useUserStore } from '@core/auth/store'
import { agentConfigApi, batchApi } from '../../api'
import { PROVIDER_PRESETS } from '../../types'
import {
  TaskStatusEnum,
  StockMarketEnum,
  type AnalysisTask,
  type AnalysisStagesConfig,
  type UserAgentConfig,
  type AgentConfig,
  type AIModelConfig,
} from '../../types'

const router = useRouter()
const store = useTradingAgentsStore()
const userStore = useUserStore()

// 表单引用
const formRef = ref<FormInstance>()

// 提交状态
const submitting = ref(false)

const loadingConfig = ref(false)
const agentConfig = ref<UserAgentConfig | null>(null)

const activeAnalysts = computed(() => {
  if (!agentConfig.value?.phase1?.agents) return []
  return agentConfig.value.phase1.agents.filter(a => a.enabled)
})

// 可用的 AI 模型列表
const availableModels = computed(() => {
  return store.enabledModels
})

// 计算预计耗时
const estimateTime = computed(() => {
  let time = 3 // 基础时间
  if (stagesConfig.stage2.enabled) time += 2
  if (stagesConfig.stage3.enabled) time += 2
  time += 1
  return time
})

// 获取提供商标签
function getProviderLabel(provider: string): string {
  return PROVIDER_PRESETS[provider as keyof typeof PROVIDER_PRESETS]?.name || provider
}

const phase2Agents = computed<AgentConfig[]>(() => {
  const agents = agentConfig.value?.phase2?.agents
  return Array.isArray(agents) ? agents.filter(a => a.enabled) : []
})

const phase3Agents = computed<AgentConfig[]>(() => {
  const agents = agentConfig.value?.phase3?.agents
  return Array.isArray(agents) ? agents.filter(a => a.enabled) : []
})

const phase4Agents = computed<AgentConfig[]>(() => {
  const agents = agentConfig.value?.phase4?.agents
  return Array.isArray(agents) ? agents.filter(a => a.enabled) : []
})

function getAgentIcon(slug: string) {
  const s = slug.toLowerCase()
  if (s.includes('news')) return Document
  if (s.includes('financial')) return Money
  if (s.includes('market')) return TrendCharts
  if (s.includes('fundamental')) return DataAnalysis
  if (s.includes('social') || s.includes('sentiment')) return ChatLineSquare
  if (s.includes('capital') || s.includes('fund') || s.includes('short')) return Wallet
  return Monitor
}

async function loadAgentConfig() {
  loadingConfig.value = true
  try {
    agentConfig.value = await agentConfigApi.getAgentConfig()
    if (stagesConfig.stage1.selected_agents.length === 0 && activeAnalysts.value.length > 0) {
      stagesConfig.stage1.selected_agents = activeAnalysts.value.map(a => a.slug)
    }

    // 从用户偏好设置中加载默认辩论轮次
    const prefs = userStore.userPreferences
    const tradingAgentsSettings = (prefs as any)?.trading_agents || {}
    const defaultDebateRounds = tradingAgentsSettings.default_debate_rounds ?? 3

    // 设置默认辩论轮次
    stagesConfig.stage2.debate.rounds = defaultDebateRounds
    stagesConfig.stage3.debate.rounds = defaultDebateRounds

    // 从智能体配置中获取模型 ID 并设置到 formData
    if (agentConfig.value?.phase1?.model_id) {
      formData.data_collection_model = agentConfig.value.phase1.model_id
    }
    // 第二/三/四阶段共用一个深度决策模型，优先使用 phase2 的配置
    if (agentConfig.value?.phase2?.model_id) {
      formData.debate_model = agentConfig.value.phase2.model_id
    } else if (agentConfig.value?.phase3?.model_id) {
      formData.debate_model = agentConfig.value.phase3.model_id
    } else if (agentConfig.value?.phase4?.model_id) {
      formData.debate_model = agentConfig.value.phase4.model_id
    }
  } catch (error) {
    console.error('Failed to load agent config:', error)
    ElMessage.error('无法加载智能体配置，请刷新重试')
  } finally {
    loadingConfig.value = false
  }
}

// 当前批量任务 ID
const currentBatchId = ref<string | null>(null)

// 批量任务列表
const batchTasks = ref<AnalysisTask[]>([])

// 任务队列位置信息
const taskQueuePositions = ref<Record<string, { position: number; waiting_count: number }>>({})

// 定时器
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 切换智能体选中状态
function toggleAgent(agentId: string) {
  const index = stagesConfig.stage1.selected_agents.indexOf(agentId)
  if (index > -1) {
    if (stagesConfig.stage1.selected_agents.length > 1) {
      stagesConfig.stage1.selected_agents.splice(index, 1)
    } else {
      ElMessage.warning('至少选择一个智能体')
    }
  } else {
    stagesConfig.stage1.selected_agents.push(agentId)
  }
}

// 表单数据
const formData = reactive({
  market: StockMarketEnum.A_SHARE,
  stock_codes: [] as string[],
  trade_date: new Date().toISOString().split('T')[0],
  data_collection_model: '', // 数据收集阶段模型
  debate_model: '', // 辩论阶段模型
})

// 市场选项
const marketOptions = [
  { label: 'A股', value: StockMarketEnum.A_SHARE },
  { label: '港股', value: StockMarketEnum.HONG_KONG },
  { label: '美股', value: StockMarketEnum.US },
]

// 输入的文本
const codesText = ref('')

// 获取 TradingAgents 设置（从 localStorage 或 userStore 读取）
const getTradingAgentsSettings = () => {
  // 优先从 localStorage 读取（因为后端 UserPreferences 不支持 trading_agents）
  const localSettingsStr = localStorage.getItem('trading_agents_settings')
  if (localSettingsStr) {
    try {
      return JSON.parse(localSettingsStr)
    } catch (error) {
      console.error('Failed to parse trading_agents_settings from localStorage:', error)
    }
  }

  // 降级从 userStore 读取
  const prefs = userStore.preferences || userStore.userPreferences
  return (prefs as any)?.trading_agents || {}
}

// 获取默认辩论轮次
const getDefaultDebateRounds = () => {
  const settings = getTradingAgentsSettings()
  return settings.default_debate_rounds ?? 3
}

// 阶段配置（默认状态）
const stagesConfig = reactive<AnalysisStagesConfig>({
  stage1: {
    enabled: true,
    selected_agents: [],
  },
  stage2: {
    enabled: true, // 默认启用
    debate: {
      enabled: true,
      rounds: getDefaultDebateRounds(), // 从用户设置读取默认辩论轮次
    },
  },
  stage3: {
    enabled: false, // 默认不启用
    debate: {
      enabled: false,
      rounds: getDefaultDebateRounds(), // 从用户设置读取默认辩论轮次
    },
  },
  stage4: {
    enabled: true, // 强制启用
  },
})

// 股票代码列表
const codesList = computed(() => {
  const lines = codesText.value
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && /^\d{6}$/.test(line))

  // 去重
  return Array.from(new Set(lines))
})

// 监听代码列表变化
watch(codesList, (newList) => {
  formData.stock_codes = newList
})

// 是否可以提交
const canSubmit = computed(() => {
  return (
    formData.market &&
    codesList.value.length > 0 &&
    codesList.value.length <= 50 &&
    stagesConfig.stage1.selected_agents.length > 0
  )
})

// 总任务数
const totalCount = computed(() => batchTasks.value.length)

// 完成数
const completedCount = computed(() => {
  return batchTasks.value.filter(
    task => task.status === TaskStatusEnum.COMPLETED
  ).length
})

// 批量进度
const batchProgress = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((completedCount.value / totalCount.value) * 100)
})

// 批量状态
const batchStatus = computed(() => {
  if (hasRunningTasks.value) return undefined
  if (completedCount.value === totalCount.value) return 'success'
  return 'exception'
})

// 是否有运行中的任务
const hasRunningTasks = computed(() => {
  return batchTasks.value.some(
    task => task.status === TaskStatusEnum.RUNNING ||
           task.status === TaskStatusEnum.PENDING
  )
})

// 表单验证规则
const formRules: FormRules = {
  market: [
    { required: true, message: '请选择股票市场', trigger: 'change' },
  ],
  stock_codes: [
    {
      validator: (_rule, _value, callback) => {
        if (codesList.value.length === 0) {
          callback(new Error('请至少输入一个股票代码'))
        } else if (codesList.value.length > 50) {
          callback(new Error('最多支持 50 个股票代码'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
  trade_date: [
    { required: true, message: '请选择交易日期', trigger: 'change' },
  ],
}

/**
 * 禁用未来日期
 */
function disabledDate(time: Date) {
  return time.getTime() > Date.now()
}

/**
 * 第二阶段变化处理
 */
function onStage2Change(enabled: boolean | string | number) {
  const isEnabled = enabled === true
  if (!isEnabled) {
    stagesConfig.stage2.debate.enabled = false
  }
}

/**
 * 第三阶段变化处理
 */
function onStage3Change(enabled: boolean | string | number) {
  const isEnabled = enabled === true
  if (!isEnabled) {
    stagesConfig.stage3.debate.enabled = false
  }
}

/**
 * 获取状态标签类型
 */
type ElTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

function getStatusType(status: TaskStatusEnum): ElTagType {
  const typeMap: Record<TaskStatusEnum, ElTagType> = {
    [TaskStatusEnum.PENDING]: 'info',
    [TaskStatusEnum.RUNNING]: 'warning',
    [TaskStatusEnum.COMPLETED]: 'success',
    [TaskStatusEnum.FAILED]: 'danger',
    [TaskStatusEnum.CANCELLED]: 'info',
    [TaskStatusEnum.STOPPED]: 'info',
    [TaskStatusEnum.EXPIRED]: 'danger',
  }
  return typeMap[status] ?? 'info'
}

/**
 * 获取状态标签文本
 */
function getStatusLabel(status: TaskStatusEnum): string {
  const labelMap: Record<string, string> = {
    [TaskStatusEnum.PENDING]: '待执行',
    [TaskStatusEnum.RUNNING]: '分析中',
    [TaskStatusEnum.COMPLETED]: '已完成',
    [TaskStatusEnum.FAILED]: '失败',
    [TaskStatusEnum.CANCELLED]: '已取消',
    [TaskStatusEnum.STOPPED]: '已停止',
    [TaskStatusEnum.EXPIRED]: '已过期',
  }
  return labelMap[status] || '未知'
}

/**
 * 提交批量分析
 */
async function handleSubmit() {
  await formRef.value?.validate()

  if (stagesConfig.stage1.selected_agents.length === 0) {
    ElMessage.warning('请至少选择一个第一阶段智能体')
    return
  }

  submitting.value = true

  try {
    const result = await store.createBatchTask({
      stock_codes: formData.stock_codes,
      market: formData.market,
      trade_date: formData.trade_date,
      data_collection_model: formData.data_collection_model || undefined,
      debate_model: formData.debate_model || undefined,
      stages: {
        stage1: {
          enabled: true,
          selected_agents: stagesConfig.stage1.selected_agents,
        },
        stage2: {
          enabled: stagesConfig.stage2.enabled,
          debate: stagesConfig.stage2.debate,
        },
        stage3: {
          enabled: stagesConfig.stage3.enabled,
          debate: stagesConfig.stage3.debate,
        },
        stage4: {
          enabled: true,
        },
      },
    })

    currentBatchId.value = result.id  // 从 BatchTaskResponse 提取 id
    ElMessage.success(`批量分析任务已创建，共 ${formData.stock_codes.length} 只股票`)

    // 开始刷新任务状态
    startRefreshing()

    // 清空表单
    codesText.value = ''
  } catch (error) {
    console.error('创建批量任务失败:', error)
  } finally {
    submitting.value = false
  }
}

/**
 * 重置表单
 */
function handleReset() {
  formRef.value?.resetFields()
  codesText.value = ''
  stagesConfig.stage1.selected_agents = activeAnalysts.value.map(a => a.slug)
  stagesConfig.stage2.enabled = true
  stagesConfig.stage2.debate.enabled = true
  // 使用用户设置的默认辩论轮次
  const prefs = userStore.userPreferences
  const tradingAgentsSettings = (prefs as any)?.trading_agents || {}
  const defaultDebateRounds = tradingAgentsSettings.default_debate_rounds ?? 3
  stagesConfig.stage2.debate.rounds = defaultDebateRounds
  stagesConfig.stage3.enabled = false
  stagesConfig.stage3.debate.enabled = false
  stagesConfig.stage3.debate.rounds = defaultDebateRounds
  formData.trade_date = new Date().toISOString().split('T')[0]
}

/**
 * 刷新任务状态
 */
async function refreshTasks() {
  if (!currentBatchId.value) return

  try {
    await store.fetchTasks({
      limit: 50,
      offset: 0,
    })

    // 过滤出属于当前批量任务的任务
    batchTasks.value = store.tasks.filter(
      task => task.batch_id === currentBatchId.value
    )

    // 获取等待中的任务的队列位置
    const waitingTasks = batchTasks.value.filter(
      task => task.status === TaskStatusEnum.PENDING
    )

    for (const task of waitingTasks) {
      try {
        const queueInfo = await taskApi.getQueuePosition(task.id)
        taskQueuePositions.value[task.id] = queueInfo
      } catch (error) {
        console.error(`获取任务队列位置失败: task_id=${task.id}`, error)
      }
    }

    // 如果所有任务都完成，停止刷新
    if (!hasRunningTasks.value) {
      stopRefreshing()
    }
  } catch (error) {
    console.error('刷新任务状态失败:', error)
  }
}

/**
 * 开始定时刷新
 */
function startRefreshing() {
  refreshTasks()
  refreshTimer = setInterval(refreshTasks, 3000)
}

/**
 * 停止定时刷新
 */
function stopRefreshing() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

/**
 * 取消所有任务
 */
async function handleCancelAll() {
  try {
    await ElMessageBox.confirm(
      '确定要取消所有进行中的任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    for (const task of batchTasks.value) {
      if (task.status === TaskStatusEnum.RUNNING || task.status === TaskStatusEnum.PENDING) {
        await store.cancelTask(task.id)
      }
    }

    ElMessage.success('已取消所有任务')
    stopRefreshing()
  } catch {
    // 用户取消
  }
}

/**
 * 取消单个任务
 */
async function handleCancelTask(taskId: string) {
  try {
    await store.cancelTask(taskId)
    ElMessage.success('任务已取消')
  } catch (error) {
    console.error('取消任务失败:', error)
  }
}

/**
 * 重试任务
 */
async function handleRetryTask(taskId: string) {
  try {
    await store.retryTask(taskId)
    ElMessage.success('任务已重新提交')
    startRefreshing()
  } catch (error) {
    console.error('重试任务失败:', error)
  }
}

/**
 * 跳转到详情页面
 */
function goToDetail(taskId: string) {
  router.push({
    name: 'AnalysisDetail',
    params: { taskId },
  })
}

// 组件卸载时清理
// 监听 localStorage 的 trading_agents_settings 变化
const storageEventHandler = (event: StorageEvent) => {
  if (event.key === 'trading_agents_settings' && event.newValue) {
    try {
      const newSettings = JSON.parse(event.newValue)
      if (newSettings.default_debate_rounds !== undefined) {
        stagesConfig.stage2.debate.rounds = newSettings.default_debate_rounds
        stagesConfig.stage3.debate.rounds = newSettings.default_debate_rounds
      }
    } catch (error) {
      console.error('Failed to parse trading_agents_settings from storage event:', error)
    }
  }
}

onMounted(async () => {
  // 注册 storage 事件监听
  window.addEventListener('storage', storageEventHandler)

  await loadAgentConfig()
  // 加载模型列表
  await store.fetchModels()
})

onUnmounted(() => {
  stopRefreshing()
  // 移除 storage 事件监听
  window.removeEventListener('storage', storageEventHandler)
})
</script>

<style scoped>
/* ==================== 基础布局 ==================== */
.batch-analysis-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* 页面标题 */
.page-header {
  margin-bottom: 20px;
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f0f9ff;
  color: #409eff;
}

.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.description {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

/* ==================== 顶部配置行 ==================== */
.main-content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  align-items: start;
}

/* 左侧列：主要内容 */
.left-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 右侧列：AI模型配置 + 按钮 */
.right-column {
  display: flex;
  flex-direction: column;
}

.right-sticky-wrapper {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.config-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.config-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.header-title .subtitle {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
  margin-left: 8px;
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

/* 股票表单行 */
.stock-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-item-flex {
  margin-bottom: 0;
}

/* 模型配置网格 */
.model-config-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.model-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.model-tip {
  font-size: 12px;
  color: #909399;
}

/* ==================== 分析师团队卡片 ==================== */
.analyst-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.analyst-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.agent-card {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
}

.agent-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}

.agent-card.agent-selected {
  background: #ecf5ff;
  border-color: #409eff;
}

.agent-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #606266;
  flex-shrink: 0;
  transition: all 0.25s;
}

.agent-selected .agent-icon-wrapper {
  background: #409eff;
  color: #fff;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.agent-when {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-status {
  flex-shrink: 0;
}

.validation-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #f56c6c;
  margin-top: 10px;
}

/* ==================== 深度分析阶段卡片 ==================== */
.stages-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.stages-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.stages-card :deep(.el-card__body) {
  padding: 16px;
}

.stages-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stage-item {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 16px;
  background: #fafbfc;
  transition: all 0.25s;
}

.stage-item:hover {
  border-color: #c0c4cc;
}

.stage-item.stage-enabled {
  background: #fff;
  border-color: #67c23a;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.1);
}

.stage-item.stage-required {
  border-color: #409eff;
  background: #ecf5ff;
}

.stage-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.stage-info {
  display: flex;
  gap: 12px;
  flex: 1;
}

.stage-number {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #909399;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.stage-item.stage-enabled .stage-number {
  background: #67c23a;
}

.stage-item.stage-required .stage-number {
  background: #409eff;
}

.stage-title {
  margin: 0 0 4px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.stage-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.stage-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.stage-config {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stage-config .label {
  font-size: 13px;
  color: #606266;
}

/* ==================== 底部操作区 ==================== */
.preview-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.preview-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.preview-content {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-label {
  font-size: 13px;
  color: #909399;
}

.preview-stages {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
}

/* ==================== 批量任务进度 ==================== */
.progress-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.progress-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.batch-progress {
  margin-bottom: 16px;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  transition: all 0.2s;
}

.task-item:hover {
  background: #ebeef5;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-code {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.queue-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
}

/* ==================== 响应式调整 ==================== */
@media (max-width: 1024px) {
  .main-content-grid {
    grid-template-columns: 1fr;
  }

  .right-sticky-wrapper {
    position: static;
  }

  .stock-form-row {
    grid-template-columns: 1fr;
  }

  .stages-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .agents-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-content {
    grid-template-columns: 1fr;
  }
}
</style>
