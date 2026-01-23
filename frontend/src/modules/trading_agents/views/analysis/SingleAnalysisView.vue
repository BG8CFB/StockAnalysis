<template>
  <div class="single-analysis-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon
          class="header-icon"
          :size="28"
        >
          <TrendCharts />
        </el-icon>
        <div>
          <h2>单股分析</h2>
          <p class="description">
            AI驱动的智能股票分析，多维度评估投资价值与风险
          </p>
        </div>
      </div>
    </div>

    <!-- 主内容区：左右两栏布局 -->
    <div class="main-content-grid">
      <!-- 左侧列：主要内容 -->
      <div class="left-column">
        <!-- 股票信息卡片 -->
        <el-card class="section-card stock-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><Tickets /></el-icon>
                股票信息
              </span>
              <el-tag
                type="danger"
                size="small"
              >
                必填
              </el-tag>
            </div>
          </template>
          <el-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            label-position="top"
            class="stock-form"
          >
            <div class="stock-form-row">
              <el-form-item
                label="股票代码"
                prop="stock_code"
                required
                class="form-item-flex"
              >
                <el-input
                  v-model="formData.stock_code"
                  placeholder="如: 000001, AAPL, 700"
                  clearable
                  size="large"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item
                label="市场类型"
                prop="market"
                class="form-item-flex"
              >
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
              <el-form-item
                label="分析日期"
                prop="trade_date"
                class="form-item-flex"
              >
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

        <!-- 分析师团队 -->
        <el-card class="section-card agents-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><User /></el-icon>
                分析师团队
                <span class="subtitle">选择第一阶段参与的分析师（至少1个）</span>
              </span>
              <el-tag
                type="info"
                effect="plain"
                size="small"
              >
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
                <div
                  class="agent-when"
                  :title="agent.when_to_use || ''"
                >
                  {{ agent.when_to_use || '适用场景：—' }}
                </div>
              </div>
              <div class="agent-status">
                <el-icon
                  v-if="stagesConfig.stage1.selected_agents.includes(agent.slug)"
                  color="#409eff"
                >
                  <CircleCheckFilled />
                </el-icon>
                <el-icon
                  v-else
                  color="#dcdfe6"
                >
                  <CircleCheck />
                </el-icon>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 深度分析阶段 -->
        <el-card class="section-card stages-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><DataAnalysis /></el-icon>
                深度分析阶段
                <span class="subtitle">配置后续分析流程（第四阶段为必需）</span>
              </span>
              <el-tag
                type="success"
                effect="plain"
                size="small"
                class="time-tag"
              >
                <el-icon><Timer /></el-icon>
                <span>预计 {{ estimateTime }} 分钟</span>
              </el-tag>
            </div>
          </template>

          <div class="stages-grid">
            <!-- 第二阶段 -->
            <div
              class="stage-item"
              :class="{ 'stage-enabled': stagesConfig.stage2.enabled }"
            >
              <div class="stage-header">
                <div class="stage-info">
                  <span class="stage-number">02</span>
                  <div>
                    <h4 class="stage-title">
                      多空博弈与投资决策
                    </h4>
                    <p class="stage-desc">
                      看涨/看跌研究员、投资组合经理、交易员共同参与决策
                    </p>
                  </div>
                </div>
                <el-switch
                  v-model="stagesConfig.stage2.enabled"
                  @change="onStage2Change"
                />
              </div>
              <div
                v-if="stagesConfig.stage2.enabled"
                class="stage-detail"
              >
                <div class="stage-tags">
                  <el-tag
                    v-for="role in ['看涨研究员', '看跌研究员', '投资组合经理', '交易员']"
                    :key="role"
                    size="small"
                  >
                    {{ role }}
                  </el-tag>
                </div>
                <div class="stage-config">
                  <span class="label">辩论轮次:</span>
                  <el-input-number
                    v-model="stagesConfig.stage2.debate.rounds"
                    :min="1"
                    :max="5"
                    size="small"
                    controls-position="right"
                  />
                </div>
              </div>
            </div>

            <!-- 第三阶段 -->
            <div
              class="stage-item"
              :class="{ 'stage-enabled': stagesConfig.stage3.enabled }"
            >
              <div class="stage-header">
                <div class="stage-info">
                  <span class="stage-number">03</span>
                  <div>
                    <h4 class="stage-title">
                      策略风格与风险评估
                    </h4>
                    <p class="stage-desc">
                      激进/中性/保守派辩论与风险管理主席评估
                    </p>
                  </div>
                </div>
                <el-switch
                  v-model="stagesConfig.stage3.enabled"
                  @change="onStage3Change"
                />
              </div>
              <div
                v-if="stagesConfig.stage3.enabled"
                class="stage-detail"
              >
                <div class="stage-tags">
                  <el-tag
                    v-for="role in ['激进派', '中性派', '保守派', '风险管理主席']"
                    :key="role"
                    size="small"
                  >
                    {{ role }}
                  </el-tag>
                </div>
                <div class="stage-config">
                  <span class="label">辩论轮次:</span>
                  <el-input-number
                    v-model="stagesConfig.stage3.debate.rounds"
                    :min="1"
                    :max="5"
                    size="small"
                    controls-position="right"
                  />
                </div>
              </div>
            </div>

            <!-- 第四阶段（必需） -->
            <div class="stage-item stage-enabled stage-required">
              <div class="stage-header">
                <div class="stage-info">
                  <span class="stage-number">04</span>
                  <div>
                    <h4 class="stage-title">
                      总结智能体
                    </h4>
                    <p class="stage-desc">
                      综合所有分析结果生成最终报告
                    </p>
                  </div>
                </div>
                <el-switch
                  :model-value="true"
                  disabled
                />
              </div>
              <div class="stage-detail">
                <div class="stage-tags">
                  <el-tag size="small">
                    总结智能体
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧列：分析预览 + AI模型配置 + 操作按钮 -->
      <div class="right-column">
        <div class="right-sticky-wrapper">
          <!-- 分析预览卡片 -->
          <el-card class="config-card preview-card">
            <template #header>
              <div class="card-header">
                <span class="header-title">
                  <el-icon><DataLine /></el-icon>
                  分析预览
                </span>
              </div>
            </template>
            <div class="preview-content">
              <!-- 股票信息 -->
              <div
                v-if="formData.stock_code"
                class="preview-item"
              >
                <span class="preview-label">股票信息</span>
                <div class="preview-stock-info">
                  <span class="stock-code">{{ formData.stock_code }}</span>
                  <span
                    v-if="stockName"
                    class="stock-name"
                  >{{ stockName }}</span>
                  <span
                    v-else
                    class="stock-name loading"
                  >加载中...</span>
                </div>
              </div>
              <div class="preview-item">
                <span class="preview-label">已选分析师</span>
                <el-tag
                  type="primary"
                  size="small"
                >
                  {{ stagesConfig.stage1.selected_agents.length }} 个
                </el-tag>
              </div>
              <div class="preview-item">
                <span class="preview-label">深度分析</span>
                <div class="preview-stages">
                  <el-tag
                    v-if="stagesConfig.stage2.enabled"
                    type="success"
                    size="small"
                  >
                    多空博弈
                  </el-tag>
                  <el-tag
                    v-if="stagesConfig.stage3.enabled"
                    type="warning"
                    size="small"
                  >
                    策略评估
                  </el-tag>
                  <el-tag
                    type="info"
                    size="small"
                  >
                    最终总结
                  </el-tag>
                </div>
              </div>
              <div class="preview-item">
                <span class="preview-label">预计耗时</span>
                <span class="preview-value">约 {{ estimateTime }} 分钟</span>
              </div>
            </div>
          </el-card>

          <!-- AI 模型配置卡片 -->
          <el-card class="config-card model-card">
            <template #header>
              <div class="card-header">
                <span class="header-title">
                  <el-icon><Cpu /></el-icon>
                  AI 模型配置
                </span>
                <el-tag
                  type="info"
                  size="small"
                >
                  可选
                </el-tag>
              </div>
            </template>
            <div class="model-config-grid">
              <div class="model-item">
                <label class="model-label">数据收集模型</label>
                <el-select
                  v-model="modelConfig.dataCollectionModel"
                  placeholder="使用默认模型"
                  clearable
                  size="large"
                  style="width: 100%"
                  @change="syncModelConfig"
                >
                  <el-option
                    v-for="model in enabledModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  />
                </el-select>
                <span class="model-tip">用于第一阶段数据收集</span>
              </div>
              <div class="model-item">
                <label class="model-label">深度决策模型</label>
                <el-select
                  v-model="modelConfig.deepDecisionModel"
                  placeholder="使用默认模型"
                  clearable
                  size="large"
                  style="width: 100%"
                  @change="syncModelConfig"
                >
                  <el-option
                    v-for="model in enabledModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  />
                </el-select>
                <span class="model-tip">用于辩论和总结阶段</span>
              </div>
            </div>
          </el-card>

          <!-- 开始智能分析按钮 -->
          <el-button
            type="primary"
            size="large"
            class="action-btn"
            :loading="submitting"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <el-icon><MagicStick /></el-icon>
            <span>开始智能分析</span>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Search,
  MagicStick,
  CircleCheckFilled,
  CircleCheck,
  TrendCharts,
  Tickets,
  User,
  Monitor,
  DataLine,
  Money,
  ChatLineSquare,
  DataAnalysis,
  Wallet,
  Document,
  Cpu,
  Timer,
} from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../../store'
import { useAIModelStore } from '@core/settings/stores/ai-model'
import { agentConfigApi, settingsApi, marketDataApi } from '../../api'
import {
  TaskStatusEnum,
  StockMarketEnum,
  type AnalysisTask,
  type AnalysisStagesConfig,
  type UserAgentConfig,
} from '../../types'

const router = useRouter()
const store = useTradingAgentsStore()
const aiModelStore = useAIModelStore()

// 表单引用
const formRef = ref<FormInstance>()

// 股票名称
const stockName = ref('')
const loadingStockName = ref(false)
let stockNameFetchTimer: ReturnType<typeof setTimeout> | null = null

// 提交状态
const submitting = ref(false)
const loadingConfig = ref(false)

// 智能体配置
const agentConfig = ref<UserAgentConfig | null>(null)

// 计算活跃的分析师列表
const activeAnalysts = computed(() => {
  if (!agentConfig.value?.phase1?.agents) return []
  return agentConfig.value.phase1.agents.filter(a => a.enabled)
})

// 计算启用的模型列表
const enabledModels = computed(() => {
  return aiModelStore.enabledModels
})

// 计算预计耗时(单位:分钟)
const estimateTime = computed(() => {
  let time = 0
  // 第一阶段: 根据选中的分析师数量计算,每个分析师约0.5分钟
  time += Math.ceil(stagesConfig.stage1.selected_agents.length * 0.5)
  // 第二阶段: 多空博弈,约2分钟
  if (stagesConfig.stage2.enabled) time += 2
  // 第三阶段: 策略风格评估,约2分钟
  if (stagesConfig.stage3.enabled) time += 2
  // 第四阶段: 总结,约1分钟
  time += 1
  // 至少显示1分钟
  return Math.max(time, 1)
})

// AI 模型配置
const modelConfig = reactive({
  dataCollectionModel: '',
  deepDecisionModel: '',
})

// 获取智能体图标
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

// 加载智能体配置
async function loadAgentConfig() {
  loadingConfig.value = true
  try {
    agentConfig.value = await agentConfigApi.getAgentConfig()

    // 从 TradingAgents 设置 API 加载默认配置
    const tradingAgentsSettings = await settingsApi.getSettings()
    const defaultDebateRounds = tradingAgentsSettings.default_debate_rounds ?? 3

    // 应用默认第一阶段智能体选择
    const defaultAgents = tradingAgentsSettings.default_phase1_agents || []
    if (defaultAgents.length > 0) {
      // 过滤掉已经被禁用的智能体
      const enabledAgentSlugs = activeAnalysts.value.map(a => a.slug)
      stagesConfig.stage1.selected_agents = defaultAgents.filter(slug =>
        enabledAgentSlugs.includes(slug)
      )
      // 如果过滤后没有智能体，使用所有启用的智能体
      if (stagesConfig.stage1.selected_agents.length === 0 && activeAnalysts.value.length > 0) {
        stagesConfig.stage1.selected_agents = activeAnalysts.value.map(a => a.slug)
      }
    } else if (stagesConfig.stage1.selected_agents.length === 0 && activeAnalysts.value.length > 0) {
      // 如果没有默认配置，使用所有启用的智能体
      stagesConfig.stage1.selected_agents = activeAnalysts.value.map(a => a.slug)
    }

    // 应用默认辩论轮次
    stagesConfig.stage2.debate.rounds = defaultDebateRounds
    stagesConfig.stage3.debate.rounds = defaultDebateRounds

    // 应用默认阶段启用状态
    stagesConfig.stage2.enabled = tradingAgentsSettings.default_phase2_enabled ?? true
    stagesConfig.stage2.debate.enabled = stagesConfig.stage2.enabled
    stagesConfig.stage3.enabled = tradingAgentsSettings.default_phase3_enabled ?? false
    stagesConfig.stage3.debate.enabled = stagesConfig.stage3.enabled

    // 从 TradingAgentsSettings 加载模型配置
    if (tradingAgentsSettings.data_collection_model_id) {
      modelConfig.dataCollectionModel = tradingAgentsSettings.data_collection_model_id
    }
    if (tradingAgentsSettings.debate_model_id) {
      modelConfig.deepDecisionModel = tradingAgentsSettings.debate_model_id
    }

    syncModelConfig()
  } catch (error) {
    console.error('Failed to load agent config:', error)
    ElMessage.error('无法加载智能体配置，请刷新重试')
  } finally {
    loadingConfig.value = false
  }
}

// 获取股票名称
async function fetchStockName() {
  // 清空之前的定时器
  if (stockNameFetchTimer) {
    clearTimeout(stockNameFetchTimer)
    stockNameFetchTimer = null
  }

  // 如果股票代码为空，清空名称
  if (!formData.stock_code || !formData.stock_code.trim()) {
    stockName.value = ''
    return
  }

  loadingStockName.value = true

  // 使用防抖，500ms 后执行
  stockNameFetchTimer = setTimeout(async () => {
    try {
      const result = await marketDataApi.getStockName({
        code: formData.stock_code.trim(),
        market: formData.market,
      })
      stockName.value = result.data.name
    } catch (error) {
      console.error('Failed to fetch stock name:', error)
      stockName.value = ''
    } finally {
      loadingStockName.value = false
    }
  }, 500)
}

// 切换智能体选中状态
function toggleAgent(agentId: string) {
  const index = stagesConfig.stage1.selected_agents.indexOf(agentId)
  if (index > -1) {
    if (stagesConfig.stage1.selected_agents.length > 1) {
      stagesConfig.stage1.selected_agents.splice(index, 1)
    } else {
      ElMessage.warning('至少选择一个分析师')
    }
  } else {
    stagesConfig.stage1.selected_agents.push(agentId)
  }
}

// 同步模型配置
function syncModelConfig() {
  formData.data_collection_model = modelConfig.dataCollectionModel
  formData.debate_model = modelConfig.deepDecisionModel
}

// 表单数据
const formData = reactive({
  market: StockMarketEnum.A_SHARE,
  stock_code: '',
  trade_date: new Date().toISOString().split('T')[0],
  data_collection_model: '',
  debate_model: '',
})

// 市场选项
const marketOptions = [
  { label: 'A股市场', value: StockMarketEnum.A_SHARE },
  { label: '港股市场', value: StockMarketEnum.HONG_KONG },
  { label: '美股市场', value: StockMarketEnum.US },
]

// 获取默认辩论轮次
const getDefaultDebateRounds = () => {
  const localSettingsStr = localStorage.getItem('trading_agents_settings')
  if (localSettingsStr) {
    try {
      const settings = JSON.parse(localSettingsStr)
      return settings.default_debate_rounds ?? 3
    } catch (error) {
      console.error('Failed to parse trading_agents_settings:', error)
    }
  }
  return 3
}

// 阶段配置
const stagesConfig = reactive<AnalysisStagesConfig>({
  stage1: {
    enabled: true,
    selected_agents: [],
  },
  stage2: {
    enabled: true,
    debate: {
      enabled: true,
      rounds: getDefaultDebateRounds(),
      concurrency: 1,  // 默认串行
    },
  },
  stage3: {
    enabled: false,
    debate: {
      enabled: false,
      rounds: getDefaultDebateRounds(),
      concurrency: 1,  // 默认串行
    },
    concurrency: 3,  // 默认全部一起
  },
  stage4: {
    enabled: true,
  },
})

// 是否可以提交
const canSubmit = computed(() => {
  return (
    formData.market &&
    formData.stock_code &&
    stagesConfig.stage1.selected_agents.length > 0
  )
})

// 表单验证规则
const formRules: FormRules = {
  market: [
    { required: true, message: '请选择股票市场', trigger: 'change' },
  ],
  stock_code: [
    { required: true, message: '请输入股票代码', trigger: 'blur' },
  ],
  trade_date: [
    { required: true, message: '请选择交易日期', trigger: 'change' },
  ],
}

function disabledDate(time: Date) {
  return time.getTime() > Date.now()
}

function onStage2Change(enabled: boolean | string | number) {
  const isEnabled = enabled === true
  if (!isEnabled) {
    stagesConfig.stage2.debate.enabled = false
  } else {
    stagesConfig.stage2.debate.enabled = true
  }
}

function onStage3Change(enabled: boolean | string | number) {
  const isEnabled = enabled === true
  if (!isEnabled) {
    stagesConfig.stage3.debate.enabled = false
  } else {
    stagesConfig.stage3.debate.enabled = true
  }
}

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

async function handleSubmit() {
  await formRef.value?.validate()
  if (stagesConfig.stage1.selected_agents.length === 0) {
    ElMessage.warning('请至少选择一个第一阶段智能体')
    return
  }

  syncModelConfig()

  submitting.value = true
  try {
    const { id } = await store.createTasks({
      stock_codes: [formData.stock_code],  // 单股作为数组传入
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
    router.push({
      name: 'AnalysisDetail',
      params: { taskId: id },  // 统一接口返回 task_id 或 batch_id
    })
  } catch (error) {
    console.error('创建任务失败:', error)
  } finally {
    submitting.value = false
  }
}

const storageEventHandler = (event: StorageEvent) => {
  if (event.key === 'trading_agents_settings' && event.newValue) {
    try {
      const newSettings = JSON.parse(event.newValue)
      if (newSettings.default_debate_rounds !== undefined) {
        stagesConfig.stage2.debate.rounds = newSettings.default_debate_rounds
        stagesConfig.stage3.debate.rounds = newSettings.default_debate_rounds
      }
    } catch (error) {
      console.error('Failed to parse trading_agents_settings:', error)
    }
  }
}

// 监听股票代码和市场类型变化
watch(
  () => [formData.stock_code, formData.market],
  () => {
    fetchStockName()
  }
)

onMounted(async () => {
  window.addEventListener('storage', storageEventHandler)
  await loadAgentConfig()
  await aiModelStore.fetchModels()
})

onUnmounted(() => {
  window.removeEventListener('storage', storageEventHandler)
  // 清理定时器
  if (stockNameFetchTimer) {
    clearTimeout(stockNameFetchTimer)
    stockNameFetchTimer = null
  }
})
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.single-analysis-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ==================== 页面标题 ==================== */
.page-header {
  margin-bottom: 20px;
  background: #fff;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff 0%, #5dadff 100%);
  color: #fff;
}

.header-content h2 {
  margin: 0 0 4px 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.description {
  margin: 0;
  color: #909399;
  font-size: 14px;
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

/* ==================== 配置卡片通用样式 ==================== */
.config-card {
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.config-card :deep(.el-card__header) {
  padding: 16px 20px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-header .el-tag {
  flex-shrink: 0;
  white-space: nowrap;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.header-title .subtitle {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
  margin-left: 8px;
}

/* ==================== 股票信息卡片 ==================== */
.stock-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

.stock-form-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 16px;
}

.form-item-flex {
  margin-bottom: 0;
}

/* ==================== AI 模型配置卡片 ==================== */
.model-config-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.model-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.model-tip {
  font-size: 12px;
  color: #909399;
}

/* ==================== 独立卡片区域 ==================== */
.section-card {
  margin-bottom: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-card:last-child {
  margin-bottom: 0;
}

.section-card :deep(.el-card__header) {
  padding: 16px 20px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

/* ==================== 分析师团队卡片 ==================== */
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

/* ==================== 深度分析阶段卡片 ==================== */
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

/* ==================== 时间标签样式 ==================== */
.time-tag {
  flex-shrink: 0;
  white-space: nowrap;
}

.time-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

/* ==================== 分析预览卡片（右侧） ==================== */
.preview-card {
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.preview-card :deep(.el-card__header) {
  padding: 16px 20px;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  font-size: 14px;
  color: #606266;
}

.preview-value {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

.preview-stages {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* 股票信息显示 */
.preview-stock-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-code {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

.stock-name {
  font-size: 14px;
  color: #606266;
}

.stock-name.loading {
  color: #909399;
  font-style: italic;
}

/* 开始按钮 */
.action-btn {
  width: 100%;
  height: 46px;
  padding: 0 24px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .main-content-grid {
    grid-template-columns: 1fr;
  }

  .right-sticky-wrapper {
    position: static;
  }

  .stages-grid {
    grid-template-columns: 1fr;
  }

  .agents-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  .stock-form-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .single-analysis-view {
    padding: 12px;
  }

  .agents-grid {
    grid-template-columns: 1fr;
  }

  .header-content h2 {
    font-size: 18px;
  }
}
</style>
