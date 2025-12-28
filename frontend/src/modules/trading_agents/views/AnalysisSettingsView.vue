<template>
  <div class="analysis-settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon
          class="header-icon"
          :size="28"
        >
          <Setting />
        </el-icon>
        <div>
          <h2>分析设置</h2>
          <p class="description">
            配置 AI 分析的默认参数和行为
          </p>
        </div>
      </div>
    </div>

    <!-- 设置卡片网格 -->
    <div class="settings-grid">
      <!-- AI 模型配置 -->
      <el-card class="setting-card">
        <template #header>
          <div class="card-header">
            <span class="header-title">
              <el-icon><Cpu /></el-icon>
              默认 AI 模型
            </span>
          </div>
        </template>
        <el-form
          ref="formRef1"
          :model="formData"
          label-position="top"
        >
          <el-form-item label="数据收集模型">
            <el-select
              v-model="formData.data_collection_model_id"
              placeholder="使用默认模型"
              clearable
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
            <span class="form-tip">数据收集、基本面分析等阶段</span>
          </el-form-item>

          <el-form-item label="辩论阶段模型">
            <el-select
              v-model="formData.debate_model_id"
              placeholder="使用默认模型"
              clearable
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
            <span class="form-tip">看涨/看跌辩论、最终总结阶段</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 辩论配置 -->
      <el-card class="setting-card">
        <template #header>
          <div class="card-header">
            <span class="header-title">
              <el-icon><ChatLineSquare /></el-icon>
              辩论配置
            </span>
          </div>
        </template>
        <el-form
          ref="formRef2"
          :model="formData"
          label-position="top"
        >
          <el-form-item label="默认辩论轮次">
            <el-input-number
              v-model="formData.default_debate_rounds"
              :min="0"
              :max="10"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">辩论阶段默认进行多少轮辩论</span>
          </el-form-item>

          <el-form-item label="最大辩论轮次">
            <el-input-number
              v-model="formData.max_debate_rounds"
              :min="0"
              :max="10"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">用户可设置的最大辩论轮次限制</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 超时配置 -->
      <el-card class="setting-card">
        <template #header>
          <div class="card-header">
            <span class="header-title">
              <el-icon><Clock /></el-icon>
              超时配置
            </span>
          </div>
        </template>
        <el-form
          ref="formRef3"
          :model="formData"
          label-position="top"
        >
          <el-form-item label="单阶段超时（分钟）">
            <el-input-number
              v-model="formData.phase_timeout_minutes"
              :min="5"
              :max="120"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">单个阶段最大执行时间</span>
          </el-form-item>

          <el-form-item label="单智能体超时（分钟）">
            <el-input-number
              v-model="formData.agent_timeout_minutes"
              :min="1"
              :max="60"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">单个智能体最大执行时间</span>
          </el-form-item>

          <el-form-item label="工具调用超时（秒）">
            <el-input-number
              v-model="formData.tool_timeout_seconds"
              :min="10"
              :max="300"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">单个工具调用最大等待时间</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 其他配置 -->
      <el-card class="setting-card">
        <template #header>
          <div class="card-header">
            <span class="header-title">
              <el-icon><Operation /></el-icon>
              其他配置
            </span>
          </div>
        </template>
        <el-form
          ref="formRef4"
          :model="formData"
          label-position="top"
        >
          <el-form-item label="任务过期时间（小时）">
            <el-input-number
              v-model="formData.task_expiry_hours"
              :min="1"
              :max="168"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">任务执行超时自动标记为过期的时间</span>
          </el-form-item>

          <el-form-item label="报告归档天数">
            <el-input-number
              v-model="formData.archive_days"
              :min="7"
              :max="365"
              controls-position="right"
              style="width: 100%"
            />
            <span class="form-tip">超过此天数的报告将被自动归档</span>
          </el-form-item>

          <el-form-item label="启用工具循环检测">
            <el-switch v-model="formData.enable_loop_detection" />
            <span class="form-tip">自动检测并禁用循环调用的工具</span>
          </el-form-item>

          <el-form-item label="启用实时进度推送">
            <el-switch v-model="formData.enable_progress_events" />
            <span class="form-tip">通过 WebSocket 实时推送分析进度</span>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button
        size="large"
        @click="handleReset"
      >
        重置
      </el-button>
      <el-button
        type="primary"
        size="large"
        class="action-btn"
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
import { Setting, Cpu, ChatLineSquare, Clock, Operation } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../store'
import { settingsApi } from '../api'
import { PROVIDER_PRESETS, type TradingAgentsSettings } from '../types'

const userStore = useUserStore()
const agentsStore = useTradingAgentsStore()

// 可用的 AI 模型列表
const availableModels = computed(() => {
  return agentsStore.enabledModels
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
  default_debate_rounds: 3, // 与单股分析和批量分析的默认值一致
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
    // 从后端加载的设置映射到表单
    Object.assign(formData, data.settings)
  } catch (error) {
    console.error('Failed to load settings:', error)
    // 如果加载失败，保持默认值
  } finally {
    loading.value = false
  }
}

// 保存设置
async function handleSave() {
  saving.value = true

  try {
    // 保存到后端
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
  // 加载模型列表
  await agentsStore.fetchModels()
  // 加载用户设置
  await loadSettings()
})
</script>

<style scoped>
/* ==================== 基础布局 ==================== */
.analysis-settings {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ==================== 页面标题 ==================== */
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

/* ==================== 设置卡片网格 ==================== */
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.setting-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.header-title .el-icon {
  color: #409eff;
}

/* ==================== 响应式调整 ==================== */
@media (max-width: 1024px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

/* ==================== 表单区域 ==================== */
.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

/* ==================== 操作按钮 ==================== */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.action-btn {
  height: 40px;
  padding: 0 24px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 8px;
}

/* ==================== 深度样式调整 ==================== */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-select) {
  --el-select-input-focus-border-color: #409eff;
}
</style>
