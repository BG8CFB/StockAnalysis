<template>
  <div class="model-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2>AI 模型管理</h2>
        <p class="page-description">
          配置 AI 模型用于 TradingAgents 智能体分析
        </p>
      </div>
      <div class="header-actions">
        <!-- 添加个人模型 - 所有用户可用 -->
        <el-button
          type="primary"
          :icon="Plus"
          @click="openAddModelDialog(false)"
        >
          添加个人模型
        </el-button>
        <!-- 添加系统模型 - 管理员和超管可见 -->
        <el-button
          v-if="canManageSystemModels"
          type="warning"
          :icon="Plus"
          @click="openAddModelDialog(true)"
        >
          添加系统模型
        </el-button>
      </div>
    </div>

    <!-- 模型列表 -->
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 我的模型 -->
        <el-tab-pane
          label="我的模型"
          name="user"
        >
          <el-table
            v-loading="store.modelsLoading"
            :data="store.userModels"
            stripe
          >
            <el-table-column
              prop="name"
              label="名称"
              width="180"
            />
            <el-table-column
              prop="provider"
              label="提供商"
              width="120"
            >
              <template #default="{ row }">
                <el-tag size="small">
                  {{ getProviderLabel(row.provider) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="model_id"
              label="模型 ID"
              width="150"
            />
            <el-table-column
              prop="api_base_url"
              label="API 地址"
              show-overflow-tooltip
            />
            <el-table-column
              prop="max_concurrency"
              label="并发数"
              width="80"
            />
            <el-table-column
              prop="enabled"
              label="状态"
              width="80"
            >
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  @change="handleToggleEnabled(row)"
                />
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="200"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Edit"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 系统模型 -->
        <el-tab-pane
          label="系统模型"
          name="system"
        >
          <el-table
            v-loading="store.modelsLoading"
            :data="store.systemModels"
            stripe
          >
            <el-table-column
              prop="name"
              label="名称"
              width="180"
            />
            <el-table-column
              prop="provider"
              label="提供商"
              width="120"
            >
              <template #default="{ row }">
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ getProviderLabel(row.provider) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="model_id"
              label="模型 ID"
              width="150"
            />
            <el-table-column
              prop="max_concurrency"
              label="并发数"
              width="80"
            />
            <el-table-column
              label="操作"
              width="250"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  size="small"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <!-- 编辑和删除按钮 - 仅管理员和超管可见 -->
                <el-button
                  v-if="canManageSystemModels"
                  link
                  type="primary"
                  :icon="Edit"
                  size="small"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <el-button
                  v-if="canManageSystemModels"
                  link
                  type="danger"
                  :icon="Delete"
                  size="small"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #title>
          {{ dialogDescription }}
        </template>
      </el-alert>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="140px"
      >
        <el-form-item
          label="模型名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="请输入模型名称"
          />
        </el-form-item>

        <!-- 模型类型 - 仅管理员和超管可见且仅在创建时显示 -->
        <el-form-item
          v-if="canManageSystemModels && !isEdit"
          label="模型类型"
        >
          <el-radio-group v-model="formData.is_system">
            <el-radio :label="false">
              <strong>个人模型</strong>
              <span class="radio-desc">（仅自己可用）</span>
            </el-radio>
            <el-radio :label="true">
              <strong>系统模型</strong>
              <span class="radio-desc">（所有用户可用）</span>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          label="提供商"
          prop="provider"
        >
          <el-select
            v-model="formData.provider"
            placeholder="选择提供商"
            style="width: 200px"
            @change="handleProviderChange"
          >
            <el-option
              v-for="preset in providerOptions"
              :key="preset.value"
              :label="preset.name"
              :value="preset.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="API 地址"
          prop="api_base_url"
        >
          <el-input
            v-model="formData.api_base_url"
            placeholder="https://api.example.com/v1"
          />
        </el-form-item>

        <el-form-item
          label="模型 ID"
          prop="model_id"
        >
          <el-input
            v-model="formData.model_id"
            placeholder="例如: gpt-4"
          />
        </el-form-item>

        <el-form-item
          label="API Key"
          prop="api_key"
        >
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="请输入 API Key"
            show-password
          />
        </el-form-item>

        <el-form-item
          label="模型最大并发数"
          prop="max_concurrency"
        >
          <el-input-number
            v-model="formData.max_concurrency"
            :min="1"
            :max="200"
          />
          <span class="form-tip">该模型在平台上的总并发能力</span>
        </el-form-item>

        <el-form-item
          label="单任务并发数"
          prop="task_concurrency"
        >
          <el-input-number
            v-model="formData.task_concurrency"
            :min="1"
            :max="10"
          />
          <span class="form-tip">单个任务可同时运行的智能体数</span>
        </el-form-item>

        <el-form-item
          label="批量任务并发数"
          prop="batch_concurrency"
        >
          <el-input-number
            v-model="formData.batch_concurrency"
            :min="1"
            :max="50"
          />
          <span class="form-tip">用户可同时运行的批量任务数（公共模型由管理员控制）</span>
        </el-form-item>

        <el-form-item
          label="超时时间(秒)"
          prop="timeout_seconds"
        >
          <el-input-number
            v-model="formData.timeout_seconds"
            :min="10"
            :max="600"
          />
        </el-form-item>

        <el-form-item
          label="温度参数"
          prop="temperature"
        >
          <el-input-number
            v-model="formData.temperature"
            :min="0"
            :max="1"
            :step="0.1"
            :precision="1"
            :controls="true"
            placeholder="0.0 - 1.0"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试连接对话框 -->
    <el-dialog
      v-model="showTestDialog"
      title="测试连接"
      width="500px"
    >
      <div
        v-if="testResult"
        class="test-result"
      >
        <el-result
          :icon="testResult.success ? 'success' : 'error'"
          :title="testResult.success ? '连接成功' : '连接失败'"
        >
          <template #sub-title>
            <p>{{ testResult.message }}</p>
            <p v-if="testResult.latency_ms">
              延迟: {{ testResult.latency_ms }}ms
            </p>
          </template>
        </el-result>
      </div>
      <div
        v-else
        class="test-loading"
      >
        <p>正在测试连接...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Connection } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../store'
import { PROVIDER_PRESETS, ModelProviderEnum, type AIModelConfig, type AIModelConfigCreate } from '../types'

const userStore = useUserStore()
const store = useTradingAgentsStore()

// 是否为管理员或超管（可以管理系统模型）
const canManageSystemModels = computed(() =>
  userStore.userInfo?.role === 'ADMIN' || userStore.userInfo?.role === 'SUPER_ADMIN'
)

// 当前标签页
const activeTab = ref('user')

// 对话框状态
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)
const isCreatingSystemModel = ref(false) // 是否正在创建系统模型

// 对话框标题和描述
const dialogTitle = computed(() => {
  if (isEdit.value) {
    return '编辑 AI 模型'
  }
  return isCreatingSystemModel.value ? '添加系统模型' : '添加个人模型'
})

const dialogDescription = computed(() => {
  if (isEdit.value) {
    return '修改模型配置后点击保存'
  }
  return isCreatingSystemModel.value
    ? '系统模型将对所有用户可用（包括管理员和普通用户）'
    : '个人模型仅您自己可用'
})

// 表单引用
const formRef = ref()

// 提交状态
const submitting = ref(false)

// 测试结果
const testResult = ref<{ success: boolean; message: string; latency_ms?: number } | null>(null)

// 表单数据
const formData = reactive<AIModelConfigCreate>({
  name: '',
  provider: ModelProviderEnum.ZHIPU,
  api_base_url: '',
  api_key: '',
  model_id: '',
  max_concurrency: 40,
  task_concurrency: 2,
  batch_concurrency: 1,
  timeout_seconds: 60,
  temperature: 0.5,
  enabled: true,
  is_system: false,
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' },
  ],
  provider: [
    { required: true, message: '请选择提供商', trigger: 'change' },
  ],
  api_base_url: [
    { required: true, message: '请输入 API 地址', trigger: 'blur' },
  ],
  api_key: [
    { required: true, message: '请输入 API Key', trigger: 'blur' },
  ],
  model_id: [
    { required: true, message: '请输入模型 ID', trigger: 'blur' },
  ],
}

// 提供商选项
const providerOptions = computed(() => Object.values(PROVIDER_PRESETS))

// 获取提供商标签
function getProviderLabel(provider: ModelProviderEnum): string {
  return PROVIDER_PRESETS[provider]?.name || provider
}

// 提供商变更时自动填充
function handleProviderChange(provider: ModelProviderEnum) {
  const preset = PROVIDER_PRESETS[provider]
  if (preset) {
    formData.api_base_url = preset.defaultBaseUrl
    formData.model_id = preset.exampleModelId
  }
}

// 验证并发参数
function validateConcurrency(): boolean {
  if (formData.task_concurrency > formData.max_concurrency) {
    ElMessage.error(`单任务并发数(${formData.task_concurrency})不能大于模型最大并发数(${formData.max_concurrency})`)
    return false
  }

  if (formData.batch_concurrency * formData.task_concurrency > formData.max_concurrency) {
    ElMessage.error(
      `批量任务并发数(${formData.batch_concurrency}) × 单任务并发数(${formData.task_concurrency}) ` +
      `不能超过模型最大并发数(${formData.max_concurrency})`
    )
    return false
  }

  return true
}

// 提交表单
async function handleSubmit() {
  await formRef.value?.validate()

  if (!validateConcurrency()) {
    return
  }

  submitting.value = true

  try {
    if (isEdit.value && editingId.value) {
      await store.updateModel(editingId.value, formData)
    } else {
      await store.createModel(formData)
    }
    showCreateDialog.value = false
  } finally {
    submitting.value = false
  }
}

// 打开添加模型对话框
function openAddModelDialog(isSystem: boolean) {
  isEdit.value = false
  isCreatingSystemModel.value = isSystem
  editingId.value = null

  // 重置表单数据
  Object.assign(formData, {
    name: '',
    provider: ModelProviderEnum.ZHIPU,
    api_base_url: '',
    api_key: '',
    model_id: '',
    max_concurrency: 40,
    task_concurrency: 2,
    batch_concurrency: 1,
    timeout_seconds: 60,
    temperature: 0.5,
    enabled: true,
    is_system: isSystem, // 设置is_system
  })

  showCreateDialog.value = true
}

// 编辑模型
function handleEdit(model: AIModelConfig) {
  isEdit.value = true
  isCreatingSystemModel.value = model.is_system
  editingId.value = model.id
  Object.assign(formData, {
    name: model.name,
    provider: model.provider,
    api_base_url: model.api_base_url,
    api_key: model.api_key,
    model_id: model.model_id,
    max_concurrency: model.max_concurrency,
    task_concurrency: model.task_concurrency,
    batch_concurrency: model.batch_concurrency,
    timeout_seconds: model.timeout_seconds,
    temperature: model.temperature,
    enabled: model.enabled,
    is_system: model.is_system,
  })
  showCreateDialog.value = true
}

// 删除模型
async function handleDelete(model: AIModelConfig) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await store.deleteModel(model.id)
  } catch {
    // 用户取消
  }
}

// 切换启用状态
async function handleToggleEnabled(model: AIModelConfig) {
  try {
    await store.updateModel(model.id, { enabled: model.enabled })
  } catch (error) {
    // 恢复原状态
    model.enabled = !model.enabled
  }
}

// 测试连接
async function handleTest(model: AIModelConfig) {
  showTestDialog.value = true
  testResult.value = null

  try {
    const result = await store.testModel(model.id)
    testResult.value = result
  } catch (error) {
    testResult.value = {
      success: false,
      message: '测试请求失败',
    }
  }
}

// 关闭对话框
function handleDialogClose() {
  isEdit.value = false
  isCreatingSystemModel.value = false
  editingId.value = null
  formRef.value?.resetFields()
}

// 初始化
onMounted(() => {
  store.fetchModels()
})
</script>

<style scoped>
.model-management {
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

.radio-desc {
  margin-left: 8px;
  font-size: 13px;
  color: #909399;
  font-weight: normal;
}

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}
</style>
