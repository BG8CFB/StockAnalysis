<template>
  <div class="mcp-settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2>MCP 系统配置</h2>
        <p class="page-description">
          配置 MCP 模块的全局参数，保存后立即对所有用户生效
        </p>
      </div>
      <div class="header-actions">
        <el-button
          :icon="RefreshLeft"
          @click="handleReset"
        >
          恢复默认
        </el-button>
        <el-button
          type="primary"
          :icon="Check"
          :loading="saving"
          @click="handleSave"
        >
          保存配置
        </el-button>
      </div>
    </div>

    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="180px"
      class="settings-form"
    >
      <!-- 连接池配置 -->
      <el-card
        shadow="never"
        class="settings-card"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>连接池配置</span>
          </div>
        </template>

        <el-form-item
          label="个人并发上限"
          prop="pool_personal_max_concurrency"
        >
          <el-input-number
            v-model="formData.pool_personal_max_concurrency"
            :min="1"
            :max="1000"
            :step="10"
          />
          <span class="form-item-desc">每个用户的个人 MCP 最大并发连接数</span>
        </el-form-item>

        <el-form-item
          label="公共并发上限"
          prop="pool_public_per_user_max"
        >
          <el-input-number
            v-model="formData.pool_public_per_user_max"
            :min="1"
            :max="100"
            :step="1"
          />
          <span class="form-item-desc">每个用户使用公共 MCP 的最大并发连接数</span>
        </el-form-item>

        <el-form-item
          label="个人队列大小"
          prop="pool_personal_queue_size"
        >
          <el-input-number
            v-model="formData.pool_personal_queue_size"
            :min="10"
            :max="1000"
            :step="10"
          />
          <span class="form-item-desc">个人 MCP 请求队列最大容量</span>
        </el-form-item>

        <el-form-item
          label="公共队列大小"
          prop="pool_public_queue_size"
        >
          <el-input-number
            v-model="formData.pool_public_queue_size"
            :min="10"
            :max="500"
            :step="10"
          />
          <span class="form-item-desc">公共 MCP 请求队列最大容量</span>
        </el-form-item>
      </el-card>

      <!-- 连接生命周期配置 -->
      <el-card
        shadow="never"
        class="settings-card"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Timer /></el-icon>
            <span>连接生命周期</span>
          </div>
        </template>

        <el-form-item
          label="完成超时时间"
          prop="connection_complete_timeout"
        >
          <el-input-number
            v-model="formData.connection_complete_timeout"
            :min="1"
            :max="300"
            :step="1"
          />
          <span class="form-item-desc">任务完成后连接销毁等待时间（秒）</span>
        </el-form-item>

        <el-form-item
          label="失败超时时间"
          prop="connection_failed_timeout"
        >
          <el-input-number
            v-model="formData.connection_failed_timeout"
            :min="1"
            :max="600"
            :step="1"
          />
          <span class="form-item-desc">任务失败后连接销毁等待时间（秒）</span>
        </el-form-item>
      </el-card>

      <!-- 健康检查配置 -->
      <el-card
        shadow="never"
        class="settings-card"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Monitor /></el-icon>
            <span>健康检查</span>
          </div>
        </template>

        <el-form-item
          label="启用健康检查"
          prop="health_check_enabled"
        >
          <el-switch v-model="formData.health_check_enabled" />
          <span class="form-item-desc">自动检测 MCP 服务器状态</span>
        </el-form-item>

        <el-form-item
          label="检查间隔时间"
          prop="health_check_interval"
        >
          <el-input-number
            v-model="formData.health_check_interval"
            :min="10"
            :max="3600"
            :step="10"
            :disabled="!formData.health_check_enabled"
          />
          <span class="form-item-desc">健康检查间隔时间（秒）</span>
        </el-form-item>

        <el-form-item
          label="检查超时时间"
          prop="health_check_timeout"
        >
          <el-input-number
            v-model="formData.health_check_timeout"
            :min="5"
            :max="300"
            :step="1"
            :disabled="!formData.health_check_enabled"
          />
          <span class="form-item-desc">单次健康检查超时时间（秒）</span>
        </el-form-item>
      </el-card>
    </el-form>

    <!-- 最后更新时间 -->
    <div
      v-if="settings.updated_at"
      class="last-updated"
    >
      <el-text
        type="info"
        size="small"
      >
        最后更新时间: {{ formatUpdateTime(settings.updated_at) }}
      </el-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Check,
  RefreshLeft,
  Connection,
  Timer,
  Monitor,
} from '@element-plus/icons-vue'
import { getMCPSettings, updateMCPSettings, resetMCPSettings, type MCPSystemSettings } from '../api/mcp'

// 表单引用
const formRef = ref<FormInstance>()

// 保存状态
const saving = ref(false)

// 当前配置
const settings = ref<MCPSystemSettings>({
  pool_personal_max_concurrency: 100,
  pool_public_per_user_max: 10,
  pool_personal_queue_size: 200,
  pool_public_queue_size: 50,
  connection_complete_timeout: 10,
  connection_failed_timeout: 30,
  health_check_enabled: true,
  health_check_interval: 300,
  health_check_timeout: 30,
})

// 表单数据
const formData = reactive<MCPSystemSettings>({ ...settings.value })

// 表单验证规则
const formRules: FormRules<MCPSystemSettings> = {
  pool_personal_max_concurrency: [
    { required: true, message: '请输入个人并发上限', trigger: 'blur' },
    { type: 'number', min: 1, max: 1000, message: '范围为 1-1000', trigger: 'blur' },
  ],
  pool_public_per_user_max: [
    { required: true, message: '请输入公共并发上限', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '范围为 1-100', trigger: 'blur' },
  ],
  pool_personal_queue_size: [
    { required: true, message: '请输入个人队列大小', trigger: 'blur' },
    { type: 'number', min: 10, max: 1000, message: '范围为 10-1000', trigger: 'blur' },
  ],
  pool_public_queue_size: [
    { required: true, message: '请输入公共队列大小', trigger: 'blur' },
    { type: 'number', min: 10, max: 500, message: '范围为 10-500', trigger: 'blur' },
  ],
  connection_complete_timeout: [
    { required: true, message: '请输入完成超时时间', trigger: 'blur' },
    { type: 'number', min: 1, max: 300, message: '范围为 1-300', trigger: 'blur' },
  ],
  connection_failed_timeout: [
    { required: true, message: '请输入失败超时时间', trigger: 'blur' },
    { type: 'number', min: 1, max: 600, message: '范围为 1-600', trigger: 'blur' },
  ],
  health_check_interval: [
    { required: true, message: '请输入检查间隔时间', trigger: 'blur' },
    { type: 'number', min: 10, max: 3600, message: '范围为 10-3600', trigger: 'blur' },
  ],
  health_check_timeout: [
    { required: true, message: '请输入检查超时时间', trigger: 'blur' },
    { type: 'number', min: 5, max: 300, message: '范围为 5-300', trigger: 'blur' },
  ],
}

// 加载配置
async function loadSettings() {
  try {
    const data = await getMCPSettings()
    settings.value = data
    Object.assign(formData, data)
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

// 保存配置
async function handleSave() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const data = await updateMCPSettings(formData)
      settings.value = data
      ElMessage.success('配置已保存，已对所有用户生效')
    } catch (error) {
      ElMessage.error('保存配置失败')
    } finally {
      saving.value = false
    }
  })
}

// 恢复默认配置
async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复为默认配置吗？当前配置将被清空，系统将使用 YAML 默认值。',
      '恢复默认配置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await resetMCPSettings()
    await loadSettings()
    ElMessage.success('已恢复为默认配置')
  } catch {
    // 用户取消
  }
}

// 格式化更新时间
function formatUpdateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 初始化
onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.mcp-settings {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}

.page-description {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.settings-form {
  max-width: 800px;
}

.settings-card {
  margin-bottom: 20px;
}

.settings-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.form-item-desc {
  margin-left: 12px;
  font-size: 13px;
  color: #909399;
}

.last-updated {
  margin-top: 20px;
  text-align: right;
}
</style>
