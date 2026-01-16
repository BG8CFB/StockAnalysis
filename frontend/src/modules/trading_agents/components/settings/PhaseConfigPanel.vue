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
      width="700px"
      @close="handleAgentDialogClose"
    >
      <el-form
        ref="agentFormRef"
        :model="agentForm"
        :rules="agentRules"
        label-width="120px"
      >
        <!-- 第一阶段：允许修改所有字段 -->
        <template v-if="isPhase1">
          <el-form-item
            label="智能体名称"
            prop="name"
          >
            <el-input
              v-model="agentForm.name"
              placeholder="例如: 技术分析师"
            />
          </el-form-item>

          <el-form-item
            label="唯一标识符"
            prop="slug"
          >
            <el-input
              v-model="agentForm.slug"
              placeholder="例如: technical_analyst"
              :disabled="isEditAgent"
            />
            <span class="form-tip">只能包含字母、数字和下划线</span>
          </el-form-item>

          <el-form-item
            label="角色定义"
            prop="role_definition"
          >
            <el-input
              v-model="agentForm.role_definition"
              type="textarea"
              :rows="6"
              placeholder="你是一位专业的股票分析师，负责..."
            />
            <span class="form-tip">系统提示词，定义智能体的角色和职责</span>
          </el-form-item>

          <el-form-item label="使用场景">
            <el-input
              v-model="agentForm.when_to_use"
              type="textarea"
              :rows="2"
              placeholder="用于分析股票的技术指标..."
            />
          </el-form-item>

          <el-form-item label="启用的 MCP 服务器">
            <el-select
              v-model="agentForm.enabled_mcp_servers"
              multiple
              placeholder="选择 MCP 服务器（未选择时使用所有已启用的服务器）"
              style="width: 100%"
            >
              <el-option
                v-for="server in serverOptions"
                :key="server.name"
                :label="server.name"
                :value="server.name"
              />
            </el-select>
            <span class="form-tip">该智能体可使用的 MCP 服务器。未选择时，可使用所有已启用的 MCP 服务器。</span>
          </el-form-item>

          <el-form-item label="启用状态">
            <el-switch v-model="agentForm.enabled" />
          </el-form-item>
        </template>

        <!-- 第二、三、四阶段：只能修改提示词 -->
        <template v-else>
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            style="margin-bottom: 16px"
          >
            本阶段只能修改智能体的提示词（角色定义），其他字段不可修改。
          </el-alert>

          <el-form-item label="智能体名称">
            <el-input
              v-model="agentForm.name"
              disabled
            />
          </el-form-item>

          <el-form-item label="唯一标识符">
            <el-input
              v-model="agentForm.slug"
              disabled
            />
          </el-form-item>

          <el-form-item
            label="角色定义"
            prop="role_definition"
          >
            <el-input
              v-model="agentForm.role_definition"
              type="textarea"
              :rows="10"
              placeholder="你是一位专业的股票分析师，负责..."
            />
            <span class="form-tip">系统提示词，定义智能体的角色和职责</span>
          </el-form-item>

          <el-form-item label="启用状态">
            <el-switch v-model="agentForm.enabled" />
            <span class="form-tip">可以启用或禁用此智能体</span>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showAgentDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveAgent"
        >
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
  if (s.includes('news') || s.includes('新闻')) return Document
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
    { pattern: /^[a-z0-9_]+$/, message: '只能包含小写字母、数字和下划线', trigger: 'blur' },
  ],
  // role_definition 不再是必填字段（管理员界面可能需要，但在前端表单中不强制）
}

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
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-dialog__title) {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px 20px;
  border-top: 1px solid #e4e7ed;
}

/* ==================== 表单提示 ==================== */
.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

/* ==================== 响应式 ==================== */
@media (max-width: 768px) {
  .agents-grid {
    grid-template-columns: 1fr;
    padding: 16px;
    gap: 12px;
  }

  .agents-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
  }

  .agent-card {
    padding: 14px;
  }

  .agent-avatar {
    width: 42px;
    height: 42px;
  }
}
</style>
