<template>
  <div class="batch-analysis-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon
          class="header-icon"
          :size="28"
        >
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
          >
            <!-- 股票代码：单独占一行 -->
            <el-form-item
              label="股票代码"
              prop="stock_codes"
            >
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

            <!-- 任务名称：单独占一行 -->
            <el-form-item
              label="任务名称"
              prop="batch_name"
            >
              <el-input
                v-model="formData.batch_name"
                placeholder="为这次批量任务命名，便于识别和管理（可选）"
                clearable
                maxlength="100"
                show-word-limit
              />
              <div class="form-tip">
                例如：蓝筹股分析、科技股筛选、A股全面扫描等
              </div>
            </el-form-item>

            <!-- 市场类型 + 交易日期：同一行 -->
            <div class="stock-form-row">
              <el-form-item
                label="股票市场"
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
                label="交易日期"
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

        <!-- 分析师团队卡片 -->
        <el-card class="section-card analyst-card">
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

          <div
            v-if="!loadingConfig && activeAnalysts.length === 0"
            class="validation-hint"
          >
            <el-icon color="#f56c6c">
              <WarningFilled />
            </el-icon>
            <span>未获取到第一阶段智能体，请到「智能体管理」启用</span>
          </div>
          <div
            v-if="stagesConfig.stage1.selected_agents.length === 0"
            class="validation-hint"
          >
            <el-icon color="#f56c6c">
              <WarningFilled />
            </el-icon>
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
              <!-- 股票列表预览 -->
              <div
                v-if="codesList.length > 0"
                class="preview-stocks-section"
              >
                <div class="preview-label">股票列表</div>
                <div class="preview-stocks-list">
                  <div
                    v-for="stock in stockNamesPreview"
                    :key="stock.code"
                    class="stock-preview-item"
                  >
                    <span class="stock-code">{{ stock.code }}</span>
                    <span
                      v-if="stock.name"
                      class="stock-name"
                    >{{ stock.name }}</span>
                    <span
                      v-else
                      class="stock-name loading"
                    >加载中...</span>
                  </div>
                  <div
                    v-if="codesList.length > 5"
                    class="stock-more"
                  >
                    ... 还有 {{ codesList.length - 5 }} 只股票
                  </div>
                </div>
              </div>
              <div class="preview-item">
                <span class="preview-label">股票数量</span>
                <el-tag
                  type="primary"
                  size="small"
                >
                  {{ codesList.length }} 只
                </el-tag>
              </div>
              <div class="preview-item">
                <span class="preview-label">已选分析师</span>
                <el-tag
                  type="success"
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
                <span class="model-tip">用于多空博弈、策略评估与总结阶段</span>
              </div>
            </div>
          </el-card>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button
              size="large"
              style="width: 100%"
              @click="handleReset"
            >
              重置
            </el-button>
            <el-button
              type="primary"
              size="large"
              class="action-btn"
              :loading="submitting"
              :disabled="!canSubmit"
              style="width: 100%"
              @click="handleSubmit"
            >
              <el-icon><MagicStick /></el-icon>
              开始批量分析 ({{ codesList.length }} 只股票)
            </el-button>
          </div>
        </div>
      </div>
    </div>

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
  User,
  Tickets,
  Timer,
} from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../../store'
import { useAIModelStore } from '@core/settings/stores/ai-model'
import { agentConfigApi, settingsApi, marketDataApi } from '../../api'
import { PROVIDER_PRESETS } from '../../types'
import {
  TaskStatusEnum,
  StockMarketEnum,
  type AnalysisStagesConfig,
  type UserAgentConfig,
  type AgentConfig,
  type AIModelConfig,
} from '../../types'

const router = useRouter()
const store = useTradingAgentsStore()
const aiModelStore = useAIModelStore()

// 表单引用
const formRef = ref<FormInstance>()

// 提交状态
const submitting = ref(false)

// 股票名称相关状态
const stockNamesMap = ref<Record<string, string>>({})
const loadingStockNames = ref(false)
let stockNamesFetchTimer: ReturnType<typeof setTimeout> | null = null

// 股票名称预览（最多显示5个）
const stockNamesPreview = computed(() => {
  return codesList.value.slice(0, 5).map(code => ({
    code,
    name: stockNamesMap.value[code] || ''
  }))
})

const loadingConfig = ref(false)
const agentConfig = ref<UserAgentConfig | null>(null)

const activeAnalysts = computed(() => {
  if (!agentConfig.value?.phase1?.agents) return []
  return agentConfig.value.phase1.agents.filter(a => a.enabled)
})

// 可用的 AI 模型列表
const availableModels = computed(() => {
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
      formData.data_collection_model = tradingAgentsSettings.data_collection_model_id
    }
    if (tradingAgentsSettings.debate_model_id) {
      formData.debate_model = tradingAgentsSettings.debate_model_id
    }
  } catch (error) {
    console.error('Failed to load agent config:', error)
    ElMessage.error('无法加载智能体配置，请刷新重试')
  } finally {
    loadingConfig.value = false
  }
}

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

// 批量获取股票名称
async function fetchBatchStockNames() {
  // 清空之前的定时器
  if (stockNamesFetchTimer) {
    clearTimeout(stockNamesFetchTimer)
    stockNamesFetchTimer = null
  }

  // 如果股票代码列表为空，清空名称
  if (codesList.value.length === 0) {
    stockNamesMap.value = {}
    return
  }

  loadingStockNames.value = true

  // 使用防抖，500ms 后执行
  stockNamesFetchTimer = setTimeout(async () => {
    try {
      const result = await marketDataApi.getBatchStockNames({
        codes: codesList.value,
        market: formData.market,
      })
      // 将结果转换为 Map
      const newMap: Record<string, string> = {}
      result.data.forEach(item => {
        newMap[item.code] = item.name
      })
      stockNamesMap.value = newMap
    } catch (error) {
      console.error('Failed to fetch stock names:', error)
    } finally {
      loadingStockNames.value = false
    }
  }, 500)
}

// 表单数据
const formData = reactive({
  market: StockMarketEnum.A_SHARE,
  stock_codes: [] as string[],
  trade_date: new Date().toISOString().split('T')[0],
  data_collection_model: '', // 数据收集阶段模型
  debate_model: '', // 辩论阶段模型
  batch_name: '', // 批量任务名称（可选，用于分类和识别批量任务）
})

// 市场选项
const marketOptions = [
  { label: 'A股', value: StockMarketEnum.A_SHARE },
  { label: '港股', value: StockMarketEnum.HONG_KONG },
  { label: '美股', value: StockMarketEnum.US },
]

// 输入的文本
const codesText = ref('')

// 阶段配置（默认状态）
// 注意：初始值使用默认的 3 轮辩论，稍后会在 loadAgentConfig 中从设置 API 加载真实值
const stagesConfig = reactive<AnalysisStagesConfig>({
  stage1: {
    enabled: true,
    selected_agents: [],
  },
  stage2: {
    enabled: true, // 默认启用
    debate: {
      enabled: true,
      rounds: 3, // 默认 3 轮，稍后会被覆盖
      concurrency: 1, // 默认串行
    },
  },
  stage3: {
    enabled: false, // 默认不启用
    debate: {
      enabled: false,
      rounds: 3, // 默认 3 轮，稍后会被覆盖
      concurrency: 1, // 默认串行
    },
    concurrency: 3, // 默认全部一起
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
    const { id } = await store.createTasks({
      stock_codes: formData.stock_codes,
      market: formData.market,
      trade_date: formData.trade_date,
      data_collection_model: formData.data_collection_model || undefined,
      debate_model: formData.debate_model || undefined,
      batch_name: formData.batch_name || undefined, // 批量任务名称
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

    // 跳转到任务中心，带上 batch_id 筛选参数
    ElMessage.success(`批量分析任务已创建，共 ${formData.stock_codes.length} 只股票`)
    router.push({
      name: 'TaskCenter',
      query: { batch_id: id },
    })

    // 清空表单（包括任务名称）
    codesText.value = ''
    formData.batch_name = ''
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
  stagesConfig.stage2.debate.rounds = 3 // 使用默认值
  stagesConfig.stage3.enabled = false
  stagesConfig.stage3.debate.enabled = false
  stagesConfig.stage3.debate.rounds = 3 // 使用默认值
  formData.trade_date = new Date().toISOString().split('T')[0]
  formData.batch_name = '' // 重置任务名称
}

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

// 监听股票代码列表和市场类型变化
watch(
  () => [codesList.value, formData.market],
  () => {
    fetchBatchStockNames()
  }
)

onMounted(async () => {
  // 注册 storage 事件监听
  window.addEventListener('storage', storageEventHandler)

  await loadAgentConfig()
  // 加载模型列表
  await aiModelStore.fetchModels()
})

onUnmounted(() => {
  // 移除 storage 事件监听
  window.removeEventListener('storage', storageEventHandler)
  // 清理定时器
  if (stockNamesFetchTimer) {
    clearTimeout(stockNamesFetchTimer)
    stockNamesFetchTimer = null
  }
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

.card-header .el-tag {
  flex-shrink: 0;
  white-space: nowrap;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  flex: 1;
  min-width: 0;
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
  border-radius: 8px;
}

.preview-card :deep(.el-card__header) {
  padding: 14px 16px;
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
  font-size: 13px;
  color: #606266;
}

.preview-stages {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* 股票列表预览 */
.preview-stocks-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed #e4e7ed;
}

.preview-stocks-section:last-child {
  border-bottom: none;
}

.preview-stocks-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stock-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.stock-preview-item .stock-code {
  font-weight: 600;
  color: #409eff;
  min-width: 60px;
}

.stock-preview-item .stock-name {
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stock-preview-item .stock-name.loading {
  color: #909399;
  font-style: italic;
}

.stock-more {
  font-size: 12px;
  color: #909399;
  font-style: italic;
  padding-left: 68px;
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
