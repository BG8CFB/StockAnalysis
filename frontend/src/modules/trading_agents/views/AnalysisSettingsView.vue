<template>
  <div class="analysis-settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>分析设置</h2>
    </div>

    <el-card shadow="never">
      <el-form
        ref="formRef"
        :model="formData"
        label-width="180px"
        style="max-width: 800px"
      >
        <!-- 阶段开关配置 -->
        <div class="form-section">
          <h3>阶段开关</h3>
          <p class="section-desc">
            控制分析流程中各个阶段的启用状态
          </p>

          <el-form-item label="第二阶段（辩论）">
            <el-switch v-model="formData.phase2_enabled" />
            <span class="form-tip">启用研究辩论阶段</span>
          </el-form-item>

          <el-form-item label="第三阶段（风险评估）">
            <el-switch v-model="formData.phase3_enabled" />
            <span class="form-tip">启用风险评估阶段</span>
          </el-form-item>

          <el-form-item label="第四阶段（总结）">
            <el-switch v-model="formData.phase4_enabled" />
            <span class="form-tip">启用总结输出阶段</span>
          </el-form-item>
        </div>

        <el-divider />

        <!-- 并发配置 -->
        <div class="form-section">
          <h3>并发控制</h3>
          <p class="section-desc">
            控制分析任务的并发执行数量
          </p>

          <el-form-item label="第一阶段并发数">
            <el-input-number
              v-model="formData.phase1_concurrency"
              :min="1"
              :max="10"
            />
            <span class="form-tip">第一阶段智能体最大并行执行数量</span>
          </el-form-item>

          <el-form-item label="批量任务并发数">
            <el-input-number
              v-model="formData.batch_concurrency"
              :min="1"
              :max="10"
            />
            <span class="form-tip">批量任务同时执行的最大数量</span>
          </el-form-item>
        </div>

        <el-divider />

        <!-- 辩论配置 -->
        <div class="form-section">
          <h3>辩论配置</h3>
          <p class="section-desc">
            控制第二阶段辩论轮次和深度
          </p>

          <el-form-item label="默认辩论轮次">
            <el-input-number
              v-model="formData.default_debate_rounds"
              :min="0"
              :max="10"
            />
            <span class="form-tip">辩论阶段默认进行多少轮辩论</span>
          </el-form-item>

          <el-form-item label="最大辩论轮次">
            <el-input-number
              v-model="formData.max_debate_rounds"
              :min="0"
              :max="10"
            />
            <span class="form-tip">用户可设置的最大辩论轮次限制</span>
          </el-form-item>
        </div>

        <el-divider />

        <!-- 超时配置 -->
        <div class="form-section">
          <h3>超时配置</h3>
          <p class="section-desc">
            控制各阶段和智能体的执行超时时间
          </p>

          <el-form-item label="单阶段超时（分钟）">
            <el-input-number
              v-model="formData.phase_timeout_minutes"
              :min="5"
              :max="120"
            />
            <span class="form-tip">单个阶段最大执行时间</span>
          </el-form-item>

          <el-form-item label="单智能体超时（分钟）">
            <el-input-number
              v-model="formData.agent_timeout_minutes"
              :min="1"
              :max="60"
            />
            <span class="form-tip">单个智能体最大执行时间</span>
          </el-form-item>

          <el-form-item label="工具调用超时（秒）">
            <el-input-number
              v-model="formData.tool_timeout_seconds"
              :min="10"
              :max="300"
            />
            <span class="form-tip">单个工具调用最大等待时间</span>
          </el-form-item>
        </div>

        <el-divider />

        <!-- 其他配置 -->
        <div class="form-section">
          <h3>其他配置</h3>

          <el-form-item label="任务过期时间（小时）">
            <el-input-number
              v-model="formData.task_expiry_hours"
              :min="1"
              :max="168"
            />
            <span class="form-tip">任务执行超时自动标记为过期的时间</span>
          </el-form-item>

          <el-form-item label="报告归档天数">
            <el-input-number
              v-model="formData.archive_days"
              :min="7"
              :max="365"
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
        </div>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            保存设置
          </el-button>
          <el-button @click="handleReset">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@core/auth/store'

const userStore = useUserStore()

// 表单引用
const formRef = ref()

// 保存状态
const saving = ref(false)

// 表单数据
const formData = reactive({
  // 阶段开关
  phase2_enabled: true,
  phase3_enabled: true,
  phase4_enabled: true,

  // 并发配置
  phase1_concurrency: 3,
  batch_concurrency: 3,

  // 辩论配置
  default_debate_rounds: 1,
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

// 加载用户偏好设置
function loadSettings() {
  const prefs = userStore.userPreferences
  if (prefs) {
    // 从用户偏好中加载设置
    const tradingAgentsSettings = (prefs as any).trading_agents || {}
    Object.assign(formData, {
      phase2_enabled: tradingAgentsSettings.phase2_enabled ?? true,
      phase3_enabled: tradingAgentsSettings.phase3_enabled ?? true,
      phase4_enabled: tradingAgentsSettings.phase4_enabled ?? true,
      phase1_concurrency: tradingAgentsSettings.phase1_concurrency ?? 3,
      batch_concurrency: tradingAgentsSettings.batch_concurrency ?? 3,
      default_debate_rounds: tradingAgentsSettings.default_debate_rounds ?? 1,
      max_debate_rounds: tradingAgentsSettings.max_debate_rounds ?? 5,
      phase_timeout_minutes: tradingAgentsSettings.phase_timeout_minutes ?? 30,
      agent_timeout_minutes: tradingAgentsSettings.agent_timeout_minutes ?? 10,
      tool_timeout_seconds: tradingAgentsSettings.tool_timeout_seconds ?? 30,
      task_expiry_hours: tradingAgentsSettings.task_expiry_hours ?? 24,
      archive_days: tradingAgentsSettings.archive_days ?? 30,
      enable_loop_detection: tradingAgentsSettings.enable_loop_detection ?? true,
      enable_progress_events: tradingAgentsSettings.enable_progress_events ?? true,
    })
  }
}

// 保存设置
async function handleSave() {
  saving.value = true

  try {
    // 更新用户偏好设置
    const currentPrefs = userStore.userPreferences || {}
    await userStore.updatePreferences({
      ...currentPrefs,
      trading_agents: { ...formData },
    })
    ElMessage.success('设置已保存')
  } catch (error) {
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

// 重置设置
function handleReset() {
  loadSettings()
  ElMessage.info('设置已重置')
}

// 初始化
onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.analysis-settings {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.form-section {
  margin-bottom: 24px;
}

.form-section h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
}

.section-desc {
  margin: 0 0 16px 0;
  color: #909399;
  font-size: 13px;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
