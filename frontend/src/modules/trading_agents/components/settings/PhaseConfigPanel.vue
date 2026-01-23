<template>
  <div class="phase-config-panel">
    <!-- 智能体列表区域 -->
    <div class="agents-container">
      <!-- 头部操作栏 -->
      <div class="agents-header">
        <div class="header-info">
          <h3>智能体配置</h3>
          <p class="stats">
            <span>共 {{ localConfig.agents.length }} 个智能体</span>
            <span class="divider">|</span>
            <span class="enabled-count">{{ enabledAgentsCount }} 个已启用</span>
          </p>
        </div>
        <!-- 只有第一阶段才显示添加按钮 -->
        <el-button
          v-if="phase === 1"
          type="primary"
          :icon="Plus"
          @click="handleAddAgent"
        >
          添加智能体
        </el-button>
      </div>

      <!-- 智能体卡片网格 -->
      <div
        v-if="localConfig.agents.length > 0"
        class="agents-grid"
      >
        <div
          v-for="(agent, index) in localConfig.agents"
          :key="agent.slug"
          class="agent-card"
          :class="{ 'is-disabled': !agent.enabled }"
        >
          <!-- 卡片头部 -->
          <div class="agent-card-header">
            <div class="agent-avatar">
              <el-icon :size="22">
                <component :is="getAgentIcon(agent.slug)" />
              </el-icon>
            </div>
            <div class="agent-header-info">
              <h4 class="agent-name">{{ agent.name }}</h4>
              <p class="agent-slug">{{ agent.slug }}</p>
            </div>
            <el-switch
              v-model="agent.enabled"
              size="small"
              @change="handleToggleAgent(agent)"
            />
          </div>

          <!-- 卡片内容 -->
          <div class="agent-card-body">
            <div
              v-if="agent.when_to_use"
              class="agent-description"
            >
              <el-icon class="desc-icon"><InfoFilled /></el-icon>
              <span>{{ agent.when_to_use }}</span>
            </div>

            <!-- MCP 服务器标签 -->
            <div
              v-if="agent.enabled_mcp_servers && agent.enabled_mcp_servers.length > 0"
              class="agent-servers"
            >
              <el-icon class="servers-icon"><Connection /></el-icon>
              <el-tag
                v-for="server in agent.enabled_mcp_servers.slice(0, 2)"
                :key="server"
                size="small"
                effect="plain"
              >
                {{ server }}
              </el-tag>
              <el-tag
                v-if="agent.enabled_mcp_servers.length > 2"
                size="small"
                effect="plain"
              >
                +{{ agent.enabled_mcp_servers.length - 2 }}
              </el-tag>
            </div>
          </div>

          <!-- 卡片操作 -->
          <div class="agent-card-footer">
            <el-button
              link
              type="primary"
              :icon="Edit"
              @click="handleEditAgent(agent, index)"
            >
              {{ isPhase1 ? '编辑' : '修改提示词' }}
            </el-button>
            <el-button
              v-if="isPhase1"
              link
              type="danger"
              :icon="Delete"
              @click="handleDeleteAgent(index)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div
        v-else
        class="empty-state"
      >
        <el-empty description="暂无智能体配置">
          <el-button
            v-if="phase === 1"
            type="primary"
            :icon="Plus"
            @click="handleAddAgent"
          >
            添加第一个智能体
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- 智能体编辑对话框 -->
    <el-dialog
      v-model="showAgentDialog"
      :title="dialogTitle"
      width="960px"
      @close="handleAgentDialogClose"
      class="agent-edit-dialog"
    >
      <el-form
        ref="agentFormRef"
        :model="agentForm"
        :rules="agentRules"
        label-width="80px"
        class="agent-form"
      >
        <!-- 第一阶段：允许修改所有字段 -->
        <template v-if="isPhase1">
          <!-- 两列布局 -->
          <div class="dialog-two-column">
            <!-- 左列：基本信息 + 角色定义 -->
            <div class="dialog-left">
              <el-form-item label="名称" prop="name">
                <el-input v-model="agentForm.name" placeholder="技术分析师" clearable />
              </el-form-item>

              <el-form-item label="标识符" prop="slug">
                <el-input
                  v-model="agentForm.slug"
                  placeholder="technical_analyst"
                  :disabled="isEditAgent"
                  clearable
                />
              </el-form-item>

              <el-form-item label="使用场景">
                <el-input
                  v-model="agentForm.when_to_use"
                  type="textarea"
                  :rows="2"
                  placeholder="用于分析股票的技术指标..."
                  maxlength="100"
                  show-word-limit
                />
              </el-form-item>

              <el-divider content-position="left">角色定义</el-divider>

              <el-form-item label="系统提示词" prop="role_definition" class="full-width-item">
                <el-input
                  v-model="agentForm.role_definition"
                  type="textarea"
                  :rows="14"
                  placeholder="你是一位专业的股票分析师，负责..."
                  show-word-limit
                />
              </el-form-item>
            </div>

            <!-- 右列：工具配置 -->
            <div class="dialog-right">
              <div class="right-section-title">
                <span>工具配置</span>
              </div>

              <!-- MCP 服务器 -->
              <div class="right-section-block">
                <div class="section-header">MCP 服务器</div>
                <div class="mcp-server-list">
                  <div
                    v-for="server in serverOptions"
                    :key="server.name"
                    class="mcp-server-item"
                    :class="{ 'is-selected': agentForm.enabled_mcp_servers.includes(server.name) }"
                    @click="toggleMCPServer(server.name)"
                  >
                    <div class="server-main">
                      <el-checkbox
                        :model-value="agentForm.enabled_mcp_servers.includes(server.name)"
                        @click.stop.native="toggleMCPServer(server.name)"
                      />
                      <div class="server-info">
                        <div class="server-name">{{ server.name }}</div>
                        <div class="server-desc">{{ getServerDescription(server.name) }}</div>
                      </div>
                    </div>
                    <el-tag v-if="server.enabled" size="small" type="success">已启用</el-tag>
                    <el-tag v-else size="small" type="info">未启用</el-tag>
                  </div>
                </div>
                <div class="section-tip">未选择时使用所有已启用的服务器</div>
              </div>

              <!-- 本地工具 -->
              <div class="right-section-block">
                <div class="section-header">本地工具</div>
                <div class="local-tools-list">
                  <el-checkbox-group v-model="selectedLocalTools" class="tools-checkbox-list">
                    <el-checkbox
                      v-for="tool in localToolOptions"
                      :key="tool.key"
                      :label="tool.key"
                      :disabled="!tool.available"
                    >
                      <div class="tool-checkbox-label">
                        <span class="tool-name">{{ tool.name }}</span>
                        <span v-if="!tool.available" class="tool-pending">（待实现）</span>
                      </div>
                    </el-checkbox>
                  </el-checkbox-group>
                </div>
                <div class="section-tip">预加载到上下文的数据类型</div>
              </div>

              <!-- 本地工具参数 -->
              <div v-if="selectedLocalTools.length > 0" class="right-section-block params-block">
                <div class="section-header">参数配置</div>
                <div class="tools-params-compact">
                  <div v-if="selectedLocalTools.includes('news')" class="param-row">
                    <span class="param-label">新闻</span>
                    <el-input-number v-model="localToolParams.news.limit" :min="5" :max="100" :step="5" size="small" />
                    <span class="param-sep">条</span>
                    <el-input-number v-model="localToolParams.news.days" :min="1" :max="90" size="small" />
                    <span class="param-sep">天内</span>
                  </div>
                  <div v-if="selectedLocalTools.includes('quotes')" class="param-row">
                    <span class="param-label">行情</span>
                    <el-input-number v-model="localToolParams.quotes.days" :min="7" :max="365" size="small" />
                    <span class="param-sep">天</span>
                    <el-checkbox v-model="localToolParams.quotes.include_realtime" size="small">含实时</el-checkbox>
                  </div>
                  <div v-if="selectedLocalTools.includes('financials')" class="param-row">
                    <span class="param-label">财报</span>
                    <el-input-number v-model="localToolParams.financials.quarters" :min="1" :max="12" size="small" />
                    <span class="param-sep">个季度</span>
                  </div>
                  <div v-if="selectedLocalTools.includes('indicators')" class="param-row">
                    <span class="param-label">指标</span>
                    <el-input-number v-model="localToolParams.indicators.periods" :min="1" :max="12" size="small" />
                    <span class="param-sep">个季度</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 第二、三、四阶段：只能修改提示词 -->
        <template v-else>
          <el-alert
            title="只能修改角色定义"
            type="info"
            :closable="false"
            style="margin-bottom: 16px"
          />

          <el-form-item label="智能体">
            <span>{{ agentForm.name }} ({{ agentForm.slug }})</span>
          </el-form-item>

          <el-form-item label="角色定义" prop="role_definition">
            <el-input
              v-model="agentForm.role_definition"
              type="textarea"
              :rows="12"
              placeholder="你是一位专业的股票分析师，负责..."
              show-word-limit
            />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showAgentDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveAgent">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  InfoFilled,
  Connection,
  User,
  TrendCharts,
  ChatLineSquare,
  Money,
  DataAnalysis,
  Document,
  Monitor,
  Wallet,
  Setting,
  Reading,
  TrendCharts as ChartIcon,
} from '@element-plus/icons-vue'
import type { AgentConfig, Phase1Config, Phase2Config, Phase3Config, Phase4Config, AIModelConfig, MCPServerConfig } from '../types'

interface Props {
  phase: number
  config?: Phase1Config | Phase2Config | Phase3Config | Phase4Config | null
  modelOptions: AIModelConfig[]
  serverOptions: MCPServerConfig[]
}

interface Emits {
  (e: 'save', data: Phase1Config | Phase2Config | Phase3Config | Phase4Config): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 是否为第一阶段
const isPhase1 = computed(() => props.phase === 1)

// 已启用的智能体数量
const enabledAgentsCount = computed(() => {
  return localConfig.agents.filter(a => a.enabled).length
})

// 获取智能体图标
function getAgentIcon(slug: string) {
  const s = slug.toLowerCase()
  if (s.includes('news') || s.includes('新闻')) return Reading
  if (s.includes('financial') || s.includes('fundamental') || s.includes('财务') || s.includes('基本面')) return Money
  if (s.includes('market') || s.includes('market') || s.includes('市场') || s.includes('技术')) return TrendCharts
  if (s.includes('social') || s.includes('sentiment') || s.includes('情绪')) return ChatLineSquare
  if (s.includes('capital') || s.includes('fund') || s.includes('short') || s.includes('资金')) return Wallet
  if (s.includes('bull') || s.includes('bear') || s.includes('debate') || s.includes('辩论')) return ChatLineSquare
  if (s.includes('risk') || s.includes('manager') || s.includes('conservative') || s.includes('risk')) return Monitor
  return User
}

// 切换智能体启用状态
function handleToggleAgent(agent: AgentConfig) {
  // 状态切换会自动更新，这里可以添加额外的逻辑
  ElMessage.success(`${agent.name} 已${agent.enabled ? '启用' : '禁用'}`)
}

// 阶段标题
const phaseTitle = computed(() => {
  const titles = ['', '信息收集与基础分析', '多空博弈与投资决策', '策略风格与风险评估', '总结智能体']
  return titles[props.phase] || ''
})

// 对话框标题
const dialogTitle = computed(() => {
  if (isPhase1.value) {
    return isEditAgent.value ? '编辑智能体' : '添加智能体'
  } else {
    return '修改提示词'
  }
})

// 本地配置
const localConfig = reactive<Phase1Config | Phase2Config | Phase3Config | Phase4Config>(
  getDefaultConfig()
)

// 监听配置变化（深拷贝确保数据同步）
watch(() => props.config, (newConfig) => {
  if (newConfig) {
    // 使用深拷贝避免引用问题
    localConfig.enabled = newConfig.enabled
    // 深拷贝 agents 数组，确保引用变化时能触发更新
    localConfig.agents = newConfig.agents.map(agent => ({ ...agent }))
    // Phase 1 特有属性
    if (props.phase === 1 && 'max_concurrency' in newConfig) {
      (localConfig as any).max_concurrency = newConfig.max_concurrency
    }
    // Phase 2 特有属性
    if (props.phase === 2 && 'debate_rounds' in newConfig) {
      (localConfig as any).debate_rounds = newConfig.debate_rounds
    }
  }
}, { deep: true, immediate: true })

// 默认配置（模型选择已与智能体配置分离）
function getDefaultConfig(): Phase1Config | Phase2Config | Phase3Config | Phase4Config {
  return {
    enabled: true,
    agents: [],
  }
}

// 智能体对话框
const showAgentDialog = ref(false)
const isEditAgent = ref(false)
const editingAgentIndex = ref(-1)
const agentFormRef = ref()

const agentForm = reactive<AgentConfig>({
  slug: '',
  name: '',
  role_definition: undefined, // 可选字段，非管理员用户不会获取到此数据
  when_to_use: '',
  enabled_mcp_servers: [],
  enabled_local_tools: [],
  enabled: true,
})

const agentRules = {
  name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入唯一标识符', trigger: 'blur' },
    { pattern: /^[a-z0-9_-]+$/, message: '只能包含小写字母、数字、下划线和连字符', trigger: 'blur' },
  ],
  // role_definition 不再是必填字段（管理员界面可能需要，但在前端表单中不强制）
}

// ==================== 本地工具配置 ====================
// 选中的本地工具类型
const selectedLocalTools = ref<string[]>([])

// 本地工具参数配置
const localToolParams = reactive({
  news: { limit: 20, days: 7 },
  quotes: { days: 30, include_realtime: true },
  financials: { quarters: 4 },
  indicators: { periods: 4 },
  technical: { days: 30, indicators: ['MA', 'MACD', 'KDJ', 'RSI', 'BOLL'] },
  company: {},
  macro: {},
})

// 本地工具选项
const localToolOptions = [
  { key: 'news', name: '新闻信息', desc: '个股相关新闻和市场快讯', icon: Document, available: true },
  { key: 'quotes', name: '行情数据', desc: '历史行情和实时报价', icon: ChartIcon, available: true },
  { key: 'financials', name: '财务报表', desc: '利润表、资产负债表、现金流量表', icon: Money, available: true },
  { key: 'indicators', name: '财务指标', desc: 'ROE、资产负债率等关键指标', icon: DataAnalysis, available: true },
  { key: 'company', name: '公司信息', desc: '公司基本信息和业务描述', icon: InfoFilled, available: true },
  { key: 'technical', name: '技术指标', desc: 'MA、MACD、KDJ、RSI、BOLL', icon: TrendCharts, available: false },
  { key: 'macro', name: '宏观经济', desc: 'CPI、PMI、GDP 等宏观数据', icon: Monitor, available: false },
]

// 保存状态
const saving = ref(false)

// 添加智能体
function handleAddAgent() {
  isEditAgent.value = false
  Object.assign(agentForm, {
    slug: '',
    name: '',
    role_definition: '',
    when_to_use: '',
    enabled_mcp_servers: [],
    enabled_local_tools: [],
    enabled: true,
  })
  showAgentDialog.value = true
}

// 编辑智能体
function handleEditAgent(agent: AgentConfig, index: number) {
  isEditAgent.value = true
  editingAgentIndex.value = index  // 保存当前编辑的索引
  // 将 MCPServerConfig 对象转换为字符串列表（兼容后端返回的对象格式）
  const mcpServers = agent.enabled_mcp_servers.map((s: any) =>
    typeof s === 'string' ? s : s.name
  )
  // 清空并重新赋值，确保响应式
  Object.assign(agentForm, {
    slug: '',
    name: '',
    role_definition: undefined,
    when_to_use: '',
    enabled_mcp_servers: [],
    enabled_local_tools: [],
    enabled: true,
  })
  Object.assign(agentForm, {
    ...agent,
    enabled_mcp_servers: mcpServers,
  })
  showAgentDialog.value = true
}

// 删除智能体
function handleDeleteAgent(index: number) {
  localConfig.agents.splice(index, 1)
}

// 保存智能体（直接保存到后端）
async function handleSaveAgent() {
  await agentFormRef.value?.validate()

  saving.value = true
  try {
    if (isPhase1.value) {
      // 第一阶段：保存所有字段
      const agentData: AgentConfig = {
        slug: agentForm.slug,
        name: agentForm.name,
        role_definition: agentForm.role_definition,
        when_to_use: agentForm.when_to_use,
        enabled_mcp_servers: [...agentForm.enabled_mcp_servers],
        enabled_local_tools: [],
        enabled: agentForm.enabled,
      }

      if (isEditAgent.value) {
        // 使用 splice 替换数组元素，确保 Vue 响应式能够追踪变化
        localConfig.agents.splice(editingAgentIndex.value, 1, agentData)
      } else {
        localConfig.agents.push(agentData)
      }
    } else {
      // 第二、三、四阶段：只保存 role_definition 和 enabled
      if (isEditAgent.value) {
        const existingAgent = localConfig.agents[editingAgentIndex.value]
        // 使用 splice 触发响应式更新
        localConfig.agents.splice(editingAgentIndex.value, 1, {
          ...existingAgent,
          role_definition: agentForm.role_definition,
          enabled: agentForm.enabled
        })
      }
    }

    // 直接保存到后端
    emit('save', { ...localConfig })
    showAgentDialog.value = false
  } finally {
    saving.value = false
  }
}

// 关闭智能体对话框
function handleAgentDialogClose() {
  agentFormRef.value?.resetFields()
}

// MCP 服务器相关
function toggleMCPServer(serverName: string) {
  const index = agentForm.enabled_mcp_servers.indexOf(serverName)
  if ( index > -1) {
    agentForm.enabled_mcp_servers.splice(index, 1)
  } else {
    agentForm.enabled_mcp_servers.push(serverName)
  }
}

function getServerDescription(serverName: string): string {
  const descriptions: Record<string, string> = {
    'finnhub': '美股金融数据，提供实时行情、财务数据、新闻',
    'alpha_vantage': '全球股票、外汇、加密货币数据和技术指标',
    'polygon': '美股实时数据和Historical数据，机构级质量',
    'yahoo-finance': '全球股票、ETF、期权数据，覆盖面广',
    'tushare': 'A股数据，提供行情、财务、宏观经济数据',
    'akshare': '中国金融市场数据，包含股票、基金、期货',
    'eastmoney': '东方财富数据，A股行情、财务、研报',
    'baostock': 'A股证券历史数据，适合回测研究',
    'news-api': '全球新闻和舆情数据，支持多语言',
    'crypto-api': '加密货币实时行情和交易数据',
  }
  return descriptions[serverName] || 'MCP 服务器工具'
}
</script>

<style scoped>
/* ==================== 智能体容器 ==================== */
.phase-config-panel {
  /* padding 由父容器控制 */
}

.agents-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ==================== 头部操作栏 ==================== */
.agents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-info h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.stats {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stats .divider {
  color: #dcdfe6;
}

.stats .enabled-count {
  color: #67c23a;
  font-weight: 500;
}

/* ==================== 智能体卡片网格 ==================== */
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  padding: 20px;
}

.agent-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.25s;
}

.agent-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.12);
  transform: translateY(-2px);
}

.agent-card.is-disabled {
  opacity: 0.6;
  background: #fafbfc;
}

.agent-card.is-disabled:hover {
  border-color: #e4e7ed;
  box-shadow: none;
  transform: none;
}

/* ==================== 卡片头部 ==================== */
.agent-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #5dadff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
}

.agent-card.is-disabled .agent-avatar {
  background: #e4e7ed;
  color: #909399;
  box-shadow: none;
}

.agent-header-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  margin: 0 0 2px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-slug {
  margin: 0;
  font-size: 12px;
  color: #909399;
  font-family: 'Monaco', 'Courier New', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ==================== 卡片内容 ==================== */
.agent-card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-description {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.agent-description .desc-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: #909399;
  font-size: 16px;
}

.agent-description span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.agent-servers {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.agent-servers .servers-icon {
  color: #909399;
  font-size: 16px;
}

/* ==================== 卡片操作 ==================== */
.agent-card-footer {
  display: flex;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px dashed #e4e7ed;
}

/* ==================== 空状态 ==================== */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  background: #fff;
}

/* ==================== 对话框样式优化 ==================== */
:deep(.el-dialog) {
  border-radius: 12px;
}

:deep(.el-dialog__header) {
  padding: 18px 24px 12px;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-dialog__title) {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-dialog__body) {
  padding: 20px 24px;
}

:deep(.el-dialog__footer) {
  padding: 12px 24px 16px;
  border-top: 1px solid #e4e7ed;
}

/* ==================== 对话框两列布局 ==================== */
.dialog-two-column {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.dialog-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.full-width-item :deep(.el-form-item__content) {
  flex-direction: column;
  align-items: flex-start;
}

/* ==================== 右侧区域样式 ==================== */
.right-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.right-section-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  padding-bottom: 4px;
}

.section-tip {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

/* ==================== MCP 服务器列表 ==================== */
.mcp-server-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

/* 自定义滚动条样式 */
.mcp-server-list::-webkit-scrollbar,
.local-tools-list::-webkit-scrollbar {
  width: 6px;
}

.mcp-server-list::-webkit-scrollbar-track,
.local-tools-list::-webkit-scrollbar-track {
  background: #f5f7fa;
  border-radius: 3px;
}

.mcp-server-list::-webkit-scrollbar-thumb,
.local-tools-list::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.mcp-server-list::-webkit-scrollbar-thumb:hover,
.local-tools-list::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}

.mcp-server-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.mcp-server-item:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.mcp-server-item.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.server-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.server-info {
  display: flex;
  flex-direction: column;
  gap: 0px;
  min-width: 0;
}

.server-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.server-desc {
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}

/* ==================== 本地工具列表 ==================== */
.local-tools-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

.tools-checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

:deep(.tools-checkbox-list .el-checkbox) {
  margin-right: 0;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  transition: all 0.2s;
}

:deep(.tools-checkbox-list .el-checkbox:hover) {
  border-color: #409eff;
  background: #f0f7ff;
}

:deep(.tools-checkbox-list .el-checkbox.is-checked) {
  border-color: #409eff;
  background: #ecf5ff;
}

:deep(.tools-checkbox-list .el-checkbox.is-disabled) {
  background: #fafafa;
  opacity: 0.6;
}

:deep(.tools-checkbox-list .el-checkbox.is-disabled:hover) {
  border-color: #e4e7ed;
  background: #fafafa;
}

:deep(.tools-checkbox-list .el-checkbox__label) {
  width: 100%;
  padding-left: 0;
}

.tool-checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tool-name {
  font-size: 13px;
  color: #606266;
}

:deep(.tools-checkbox-list .el-checkbox.is-disabled .tool-name) {
  color: #c0c4cc;
}

.tool-pending {
  color: #909399;
  font-size: 11px;
}

/* ==================== 参数配置 ==================== */
.params-block {
  background: #f9fafb;
  border-radius: 6px;
  padding: 10px;
}

.tools-params-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  flex-wrap: wrap;
}

.param-label {
  color: #606266;
  font-weight: 500;
  min-width: 32px;
}

.param-sep {
  color: #909399;
  font-size: 11px;
}

:deep(.param-row .el-input-number) {
  width: 70px;
}

:deep(.param-row .el-input-number .el-input__inner) {
  padding-left: 6px;
  padding-right: 6px;
  text-align: center;
}

/* ==================== 分隔线 ==================== */
:deep(.el-divider) {
  margin: 8px 0 8px;
}

:deep(.el-divider__text) {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  background: transparent;
}

/* ==================== 表单提示 ==================== */
.form-tip {
  margin-top: 4px;
  color: #909399;
  font-size: 11px;
  line-height: 1.4;
}

/* ==================== 响应式 ==================== */
@media (max-width: 900px) {
  :deep(.el-dialog) {
    width: 95vw !important;
  }

  .dialog-two-column {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .dialog-right {
    order: -1;
  }

  .mcp-server-list,
  .local-tools-list {
    max-height: 180px;
  }
}
</style>
