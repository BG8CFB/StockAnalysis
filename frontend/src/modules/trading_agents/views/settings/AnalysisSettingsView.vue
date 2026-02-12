<template>
  <div class="analysis-settings">
    <div class="settings-header">
      <div class="header-info">
        <el-icon
          color="#409eff"
          :size="20"
        >
          <InfoFilled />
        </el-icon>
        <span>管理员配置：此处配置由管理员设置，所有用户共享</span>
      </div>
      <div class="header-actions">
        <el-button @click="handleReset">
          重置
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          保存设置
        </el-button>
      </div>
    </div>

    <!-- Tab 切换 -->
    <el-tabs
      v-model="activeTab"
      class="settings-tabs"
    >
      <!-- 默认配置 Tab -->
      <el-tab-pane
        label="默认配置"
        name="default"
      >
        <div class="tab-content">
          <!-- AI 模型配置 -->
          <div class="config-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon><Cpu /></el-icon>
                AI 模型配置
              </h3>
              <el-tag
                size="small"
                type="info"
              >
                数据收集 vs 深度决策
              </el-tag>
            </div>
            <div class="card-body">
              <div class="model-config-grid">
                <div class="model-config-item">
                  <label class="model-label">
                    <span class="label-text">数据收集模型</span>
                    <span class="label-hint">第一阶段</span>
                  </label>
                  <el-select
                    v-model="formData.data_collection_model_id"
                    placeholder="使用默认模型"
                    clearable
                    size="default"
                    class="full-width"
                  >
                    <el-option
                      v-for="model in availableModels"
                      :key="model.id"
                      :label="model.name"
                      :value="model.id"
                    >
                      <div class="model-option">
                        <span class="model-name">{{ model.name }}</span>
                        <el-tag
                          size="small"
                          :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                        >
                          {{ getProviderLabel(model.provider) }}
                        </el-tag>
                      </div>
                    </el-option>
                  </el-select>
                  <div class="model-desc">
                    用于第一阶段（数据收集与基础分析）
                  </div>
                </div>

                <div class="model-config-item">
                  <label class="model-label">
                    <span class="label-text">深度决策模型</span>
                    <span class="label-hint">第二-四阶段</span>
                  </label>
                  <el-select
                    v-model="formData.debate_model_id"
                    placeholder="使用默认模型"
                    clearable
                    size="default"
                    class="full-width"
                  >
                    <el-option
                      v-for="model in availableModels"
                      :key="model.id"
                      :label="model.name"
                      :value="model.id"
                    >
                      <div class="model-option">
                        <span class="model-name">{{ model.name }}</span>
                        <el-tag
                          size="small"
                          :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                        >
                          {{ getProviderLabel(model.provider) }}
                        </el-tag>
                      </div>
                    </el-option>
                  </el-select>
                  <div class="model-desc">
                    用于第二、三、四阶段（分析辩论与总结）
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 中间区域：智能体选择 + 流程配置 + 辩论配置 -->
          <div class="middle-section">
            <!-- 左侧：智能体选择 -->
            <div class="config-card agents-card">
              <div class="card-header">
                <h3 class="card-title">
                  <el-icon><User /></el-icon>
                  第一阶段默认智能体
                </h3>
                <el-tag
                  size="small"
                  type="primary"
                >
                  已选 {{ formData.default_phase1_agents.length }}/{{ phase1Agents.length }}
                </el-tag>
              </div>
              <div class="card-body agents-card-body">
                <div
                  v-loading="loadingAgents"
                  class="agents-list"
                >
                  <div
                    v-for="agent in phase1Agents"
                    :key="agent.slug"
                    class="agent-item"
                    :class="{ 'agent-selected': formData.default_phase1_agents.includes(agent.slug) }"
                    @click="toggleAgent(agent.slug)"
                  >
                    <div class="agent-checkbox">
                      <el-icon
                        v-if="formData.default_phase1_agents.includes(agent.slug)"
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
                    <div class="agent-content">
                      <div class="agent-name">
                        {{ agent.name }}
                      </div>
                      <div class="agent-slug">
                        {{ agent.slug }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧：流程配置 + 辩论配置 -->
            <div class="right-column">
              <!-- 流程配置 -->
              <div class="config-card flow-card">
                <div class="card-header">
                  <h3 class="card-title">
                    <el-icon><Operation /></el-icon>
                    流程默认启用
                  </h3>
                </div>
                <div class="card-body">
                  <div class="flow-config-list">
                    <div class="flow-config-item">
                      <div class="flow-info">
                        <div class="flow-name">
                          第二阶段
                        </div>
                        <div class="flow-desc">
                          多空博弈与投资决策
                        </div>
                      </div>
                      <el-switch
                        v-model="formData.default_phase2_enabled"
                        size="default"
                      />
                    </div>

                    <div class="flow-config-item">
                      <div class="flow-info">
                        <div class="flow-name">
                          第三阶段
                        </div>
                        <div class="flow-desc">
                          策略风格与风险评估
                        </div>
                      </div>
                      <el-switch
                        v-model="formData.default_phase3_enabled"
                        size="default"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 辩论配置 -->
              <div class="config-card debate-card">
                <div class="card-header">
                  <h3 class="card-title">
                    <el-icon><ChatLineSquare /></el-icon>
                    辩论配置
                  </h3>
                </div>
                <div class="card-body">
                  <div class="debate-config-list">
                    <div class="debate-config-item">
                      <label class="debate-label">默认辩论轮次</label>
                      <el-input-number
                        v-model="formData.default_debate_rounds"
                        :min="0"
                        :max="10"
                        controls-position="right"
                        size="small"
                      />
                      <span class="debate-hint">第二、三阶段</span>
                    </div>

                    <div class="debate-config-item">
                      <label class="debate-label">最大辩论轮次</label>
                      <el-input-number
                        v-model="formData.max_debate_rounds"
                        :min="0"
                        :max="10"
                        controls-position="right"
                        size="small"
                      />
                      <span class="debate-hint">用户上限</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 超时配置 Tab -->
      <el-tab-pane
        label="超时配置"
        name="timeout"
      >
        <div class="tab-content">
          <div class="config-card timeout-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon><Clock /></el-icon>
                超时配置
              </h3>
            </div>
            <div class="card-body">
              <div class="timeout-config-grid">
                <div class="timeout-config-item">
                  <label class="timeout-label">单阶段超时</label>
                  <el-input-number
                    v-model="formData.phase_timeout_minutes"
                    :min="5"
                    :max="120"
                    controls-position="right"
                  />
                  <span class="timeout-unit">分钟</span>
                  <div class="timeout-desc">
                    单个分析阶段的最大执行时间
                  </div>
                </div>

                <div class="timeout-config-item">
                  <label class="timeout-label">单智能体超时</label>
                  <el-input-number
                    v-model="formData.agent_timeout_minutes"
                    :min="1"
                    :max="60"
                    controls-position="right"
                  />
                  <span class="timeout-unit">分钟</span>
                  <div class="timeout-desc">
                    单个智能体任务的最大执行时间
                  </div>
                </div>

                <div class="timeout-config-item">
                  <label class="timeout-label">工具调用超时</label>
                  <el-input-number
                    v-model="formData.tool_timeout_seconds"
                    :min="10"
                    :max="300"
                    controls-position="right"
                  />
                  <span class="timeout-unit">秒</span>
                  <div class="timeout-desc">
                    单次工具调用的最大等待时间
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 其他配置 Tab -->
      <el-tab-pane
        label="其他配置"
        name="other"
      >
        <div class="tab-content">
          <div class="config-card other-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon><MoreFilled /></el-icon>
                其他配置
              </h3>
            </div>
            <div class="card-body">
              <div class="other-config-grid">
                <div class="other-config-item">
                  <label class="other-label">任务过期时间</label>
                  <el-input-number
                    v-model="formData.task_expiry_hours"
                    :min="1"
                    :max="168"
                    controls-position="right"
                  />
                  <span class="other-unit">小时</span>
                  <div class="other-desc">
                    任务执行超时自动标记为过期
                  </div>
                </div>

                <div class="other-config-item">
                  <label class="other-label">报告归档天数</label>
                  <el-input-number
                    v-model="formData.archive_days"
                    :min="7"
                    :max="365"
                    controls-position="right"
                  />
                  <span class="other-unit">天</span>
                  <div class="other-desc">
                    超过此天数的报告将被自动归档
                  </div>
                </div>

                <div class="other-config-item">
                  <label class="other-label">工具循环检测</label>
                  <div class="switch-wrapper">
                    <el-switch v-model="formData.enable_loop_detection" />
                    <span class="switch-desc">自动检测并禁用循环调用的工具</span>
                  </div>
                </div>

                <div class="other-config-item">
                  <label class="other-label">实时进度推送</label>
                  <div class="switch-wrapper">
                    <el-switch v-model="formData.enable_progress_events" />
                    <span class="switch-desc">通过 WebSocket 实时推送分析进度</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Cpu,
  ChatLineSquare,
  Clock,
  Operation,
  Setting,
  InfoFilled,
  CircleCheckFilled,
  CircleCheck,
  User,
  MoreFilled,
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../../store'
import { useAIModelStore } from '@core/settings/stores/ai-model'
import { settingsApi, agentConfigApi } from '../../api'
import { PROVIDER_PRESETS, type TradingAgentsSettings, type AgentConfig } from '../../types'

const userStore = useUserStore()
const agentsStore = useTradingAgentsStore()
const aiModelStore = useAIModelStore()

// 可用的 AI 模型列表
const availableModels = computed(() => {
  return aiModelStore.enabledModels
})

// 获取提供商标签
function getProviderLabel(provider?: string): string {
  if (!provider) return '未知'
  return PROVIDER_PRESETS[provider as keyof typeof PROVIDER_PRESETS]?.name || provider
}

// 当前激活的 tab
const activeTab = ref('default')

// 保存状态
const saving = ref(false)
const loadingAgents = ref(false)

// 第一阶段智能体列表
const phase1Agents = ref<AgentConfig[]>([])

// 表单数据
const formData = reactive<TradingAgentsSettings>({
  // 默认 AI 模型配置
  data_collection_model_id: '',
  debate_model_id: '',

  // 辩论配置
  default_debate_rounds: 3,
  max_debate_rounds: 5,

  // 超时配置
  phase_timeout_minutes: 30,
  agent_timeout_minutes: 10,
  tool_timeout_seconds: 30,

  // 流程默认配置
  default_phase1_agents: [],
  default_phase2_enabled: true,
  default_phase3_enabled: false,

  // 其他配置
  task_expiry_hours: 24,
  archive_days: 30,
  enable_loop_detection: true,
  enable_progress_events: true,
})

// 获取第一个启用的模型 ID
function getFirstEnabledModelId(): string {
  const models = aiModelStore.enabledModels
  return models.length > 0 ? models[0].id : ''
}

// 切换智能体选中状态
function toggleAgent(agentId: string) {
  const index = formData.default_phase1_agents.indexOf(agentId)
  if (index > -1) {
    formData.default_phase1_agents.splice(index, 1)
  } else {
    formData.default_phase1_agents.push(agentId)
  }
}

// 加载智能体配置
async function loadAgentConfig() {
  loadingAgents.value = true
  try {
    const config = await agentConfigApi.getAgentConfig()
    phase1Agents.value = config.phase1.agents.filter(a => a.enabled)
  } catch (error) {
    console.error('Failed to load agent config:', error)
  } finally {
    loadingAgents.value = false
  }
}

// 加载设置
async function loadSettings() {
  try {
    const data = await settingsApi.getSettings()
    Object.assign(formData, data)

    // 确保 default_phase1_agents 是数组
    if (!Array.isArray(formData.default_phase1_agents)) {
      formData.default_phase1_agents = []
    }

    // 如果模型 ID 为空，自动使用第一个启用的模型
    if (!formData.data_collection_model_id) {
      const defaultModelId = getFirstEnabledModelId()
      if (defaultModelId) {
        formData.data_collection_model_id = defaultModelId
      }
    }
    if (!formData.debate_model_id) {
      const defaultModelId = getFirstEnabledModelId()
      if (defaultModelId) {
        formData.debate_model_id = defaultModelId
      }
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

// 保存设置
async function handleSave() {
  saving.value = true
  try {
    await settingsApi.updateSettings(formData)
    ElMessage.success('设置已保存')
  } catch (error) {
    console.error('Save error:', error)
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

// 重置设置
async function handleReset() {
  await loadSettings()
  ElMessage.info('设置已重置')
}

// 初始化
onMounted(async () => {
  await aiModelStore.fetchModels()
  await loadAgentConfig()
  await loadSettings()
})
</script>

<style scoped>
.analysis-settings {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

/* ==================== 顶部操作栏 ==================== */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* ==================== Tab 内容区域 ==================== */
.settings-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}

.settings-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

/* ==================== 配置卡片通用样式 ==================== */
.config-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafbfc;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.card-title .el-icon {
  font-size: 18px;
  color: #409eff;
}

.card-body {
  padding: 20px;
}

/* ==================== AI 模型配置 ==================== */
.model-config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.model-config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-text {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.label-hint {
  padding: 2px 8px;
  background: #ecf5ff;
  color: #409eff;
  font-size: 12px;
  border-radius: 4px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  flex: 1;
}

.model-desc {
  font-size: 12px;
  color: #909399;
  margin-top: -4px;
}

.full-width {
  width: 100%;
}

/* ==================== 中间区域 ==================== */
.middle-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* ==================== 智能体选择 ==================== */
.agents-card-body {
  padding: 16px;
}

.agents-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.agent-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.1);
}

.agent-item.agent-selected {
  background: #ecf5ff;
  border-color: #409eff;
}

.agent-checkbox {
  flex-shrink: 0;
}

.agent-content {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-slug {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==================== 右侧列 ==================== */
.right-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ==================== 流程配置 ==================== */
.flow-config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafbfc;
}

.flow-info {
  flex: 1;
}

.flow-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}

.flow-desc {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

/* ==================== 辩论配置 ==================== */
.debate-config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.debate-config-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.debate-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.debate-hint {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

/* ==================== 超时配置 ==================== */
.timeout-config-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.timeout-config-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timeout-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.timeout-unit {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

.timeout-desc {
  font-size: 12px;
  color: #909399;
  margin-top: -4px;
}

/* ==================== 其他配置 ==================== */
.other-config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.other-config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.other-config-item.full-width {
  grid-column: 1 / -1;
}

.other-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.other-unit {
  font-size: 13px;
  color: #909399;
}

.other-desc {
  font-size: 12px;
  color: #909399;
  margin-top: -4px;
}

.switch-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-desc {
  font-size: 13px;
  color: #606266;
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .middle-section {
    grid-template-columns: 1fr;
  }

  .model-config-grid {
    grid-template-columns: 1fr;
  }

  .timeout-config-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .other-config-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .settings-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .header-actions {
    flex-direction: column;
  }

  .header-actions .el-button {
    width: 100%;
  }

  .agents-list {
    grid-template-columns: 1fr;
  }

  .timeout-config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
