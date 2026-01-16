<template>
  <div class="analysis-settings">
    <el-tabs
      v-model="activeTab"
      class="settings-tabs"
    >
      <!-- AI 模型 -->
      <el-tab-pane
        name="model"
        label="AI 模型"
      >
        <template #label>
          <div class="tab-label">
            <el-icon><Cpu /></el-icon>
            <span>AI 模型</span>
          </div>
        </template>
        <div class="tab-content">
          <el-card shadow="never">
            <el-form
              ref="formRef"
              :model="formData"
              label-width="140px"
            >
              <el-form-item label="数据收集模型">
                <el-select
                  v-model="formData.data_collection_model_id"
                  placeholder="使用默认模型"
                  clearable
                  style="width: 320px"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  >
                    <span class="option-name">{{ model.name }}</span>
                    <el-tag
                      size="small"
                      style="margin-left: 8px"
                      :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                    >
                      {{ getProviderLabel(model.provider) }}
                    </el-tag>
                  </el-option>
                </el-select>
                <div class="form-desc">用于数据收集、基本面分析等阶段</div>
              </el-form-item>

              <el-form-item label="辩论阶段模型">
                <el-select
                  v-model="formData.debate_model_id"
                  placeholder="使用默认模型"
                  clearable
                  style="width: 320px"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  >
                    <span class="option-name">{{ model.name }}</span>
                    <el-tag
                      size="small"
                      style="margin-left: 8px"
                      :type="model.provider === 'zhipu' ? 'primary' : 'info'"
                    >
                      {{ getProviderLabel(model.provider) }}
                    </el-tag>
                  </el-option>
                </el-select>
                <div class="form-desc">用于看涨/看跌辩论、最终总结阶段</div>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 辩论配置 -->
      <el-tab-pane
        name="debate"
        label="辩论配置"
      >
        <template #label>
          <div class="tab-label">
            <el-icon><ChatLineSquare /></el-icon>
            <span>辩论配置</span>
          </div>
        </template>
        <div class="tab-content">
          <el-card shadow="never">
            <el-form
              ref="formRef"
              :model="formData"
              label-width="140px"
            >
              <el-form-item label="默认辩论轮次">
                <el-input-number
                  v-model="formData.default_debate_rounds"
                  :min="0"
                  :max="10"
                  controls-position="right"
                />
                <div class="form-desc">辩论阶段默认进行的辩论轮数</div>
              </el-form-item>

              <el-form-item label="最大辩论轮次">
                <el-input-number
                  v-model="formData.max_debate_rounds"
                  :min="0"
                  :max="10"
                  controls-position="right"
                />
                <div class="form-desc">用户可设置的最大辩论轮次限制</div>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 超时配置 -->
      <el-tab-pane
        name="timeout"
        label="超时配置"
      >
        <template #label>
          <div class="tab-label">
            <el-icon><Clock /></el-icon>
            <span>超时配置</span>
          </div>
        </template>
        <div class="tab-content">
          <el-card shadow="never">
            <el-form
              ref="formRef"
              :model="formData"
              label-width="140px"
            >
              <el-form-item label="单阶段超时">
                <el-input-number
                  v-model="formData.phase_timeout_minutes"
                  :min="5"
                  :max="120"
                  controls-position="right"
                />
                <span class="form-unit">分钟</span>
                <div class="form-desc">单个阶段最大执行时间</div>
              </el-form-item>

              <el-form-item label="单智能体超时">
                <el-input-number
                  v-model="formData.agent_timeout_minutes"
                  :min="1"
                  :max="60"
                  controls-position="right"
                />
                <span class="form-unit">分钟</span>
                <div class="form-desc">单个智能体最大执行时间</div>
              </el-form-item>

              <el-form-item label="工具调用超时">
                <el-input-number
                  v-model="formData.tool_timeout_seconds"
                  :min="10"
                  :max="300"
                  controls-position="right"
                />
                <span class="form-unit">秒</span>
                <div class="form-desc">单个工具调用最大等待时间</div>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 其他配置 -->
      <el-tab-pane
        name="other"
        label="其他配置"
      >
        <template #label>
          <div class="tab-label">
            <el-icon><Operation /></el-icon>
            <span>其他配置</span>
          </div>
        </template>
        <div class="tab-content">
          <el-card shadow="never">
            <el-form
              ref="formRef"
              :model="formData"
              label-width="140px"
            >
              <el-form-item label="任务过期时间">
                <el-input-number
                  v-model="formData.task_expiry_hours"
                  :min="1"
                  :max="168"
                  controls-position="right"
                />
                <span class="form-unit">小时</span>
                <div class="form-desc">任务执行超时自动标记为过期</div>
              </el-form-item>

              <el-form-item label="报告归档天数">
                <el-input-number
                  v-model="formData.archive_days"
                  :min="7"
                  :max="365"
                  controls-position="right"
                />
                <span class="form-unit">天</span>
                <div class="form-desc">超过此天数的报告将被自动归档</div>
              </el-form-item>

              <el-divider />

              <el-form-item label="工具循环检测">
                <el-switch v-model="formData.enable_loop_detection" />
                <div class="form-desc">自动检测并禁用循环调用的工具</div>
              </el-form-item>

              <el-form-item label="实时进度推送">
                <el-switch v-model="formData.enable_progress_events" />
                <div class="form-desc">通过 WebSocket 实时推送分析进度</div>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 底部操作按钮 -->
    <div class="form-actions">
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
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, ChatLineSquare, Clock, Operation } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../../store'
import { useAIModelStore } from '@core/settings/stores/ai-model'
import { settingsApi } from '../../api'
import { PROVIDER_PRESETS, type TradingAgentsSettings } from '../../types'

const userStore = useUserStore()
const agentsStore = useTradingAgentsStore()
const aiModelStore = useAIModelStore()

// 当前激活的标签
const activeTab = ref('model')

// 可用的 AI 模型列表
const availableModels = computed(() => {
  return aiModelStore.enabledModels
})

// 获取提供商标签
function getProviderLabel(provider: string): string {
  return PROVIDER_PRESETS[provider as keyof typeof PROVIDER_PRESETS]?.name || provider
}

// 表单引用
const formRef = ref()

// 保存状态
const saving = ref(false)
const loading = ref(false)

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

  // 其他配置
  task_expiry_hours: 24,
  archive_days: 30,
  enable_loop_detection: true,
  enable_progress_events: true,
})

// 加载用户设置
async function loadSettings() {
  loading.value = true
  try {
    const data = await settingsApi.getSettings()
    Object.assign(formData, data.settings)
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
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
  await loadSettings()
})
</script>

<style scoped>
.analysis-settings {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ==================== 标签页样式 ==================== */
.settings-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.settings-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.settings-tabs :deep(.el-tabs__nav-wrap) {
  padding: 12px 0;
}

.settings-tabs :deep(.el-tabs__item) {
  padding: 0 20px;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  color: #606266;
}

.settings-tabs :deep(.el-tabs__item:hover) {
  color: #409eff;
}

.settings-tabs :deep(.el-tabs__item.is-active) {
  color: #409eff;
  font-weight: 500;
}

.settings-tabs :deep(.el-tabs__active-bar) {
  background-color: #409eff;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-label .el-icon {
  font-size: 16px;
}

/* ==================== 标签页内容 ==================== */
.settings-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}

.tab-content {
  max-width: 800px;
  margin: 0 auto;
}

.tab-content .el-card {
  border: 1px solid #e4e7ed;
}

.tab-content .el-card__body {
  padding: 32px;
}

/* ==================== 表单样式 ==================== */
:deep(.el-form-item) {
  margin-bottom: 28px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

:deep(.el-input-number) {
  width: 180px;
}

.form-desc {
  margin-top: 6px;
  margin-left: 0;
  color: #909399;
  font-size: 13px;
  line-height: 1.5;
}

.form-unit {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}

/* ==================== 选项样式 ==================== */
.option-name {
  flex: 1;
}

/* ==================== 操作按钮 ==================== */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px 20px 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

/* ==================== 分割线 ==================== */
:deep(.el-divider) {
  margin: 24px 0;
}
</style>
