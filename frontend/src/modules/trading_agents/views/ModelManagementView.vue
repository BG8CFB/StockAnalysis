<template>
  <div class="model-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>AI 模型管理</h2>
      <el-button
        type="primary"
        :icon="Plus"
        @click="showCreateDialog = true"
      >
        添加模型
      </el-button>
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
              width="120"
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
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEdit ? '编辑模型' : '添加模型'"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
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

        <el-form-item
          label="提供商"
          prop="provider"
        >
          <el-select
            v-model="formData.provider"
            placeholder="选择提供商"
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
          label="最大并发数"
          prop="max_concurrency"
        >
          <el-input-number
            v-model="formData.max_concurrency"
            :min="1"
            :max="100"
          />
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
          <el-slider
            v-model="formData.temperature"
            :min="0"
            :max="1"
            :step="0.1"
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
import { useTradingAgentsStore } from '../store'
import { PROVIDER_PRESETS, ModelProviderEnum, type AIModelConfig, type AIModelConfigCreate } from '../types'

const store = useTradingAgentsStore()

// 当前标签页
const activeTab = ref('user')

// 对话框状态
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)

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
  max_concurrency: 1,
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

// 提交表单
async function handleSubmit() {
  await formRef.value?.validate()
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

// 编辑模型
function handleEdit(model: AIModelConfig) {
  isEdit.value = true
  editingId.value = model.id
  Object.assign(formData, {
    name: model.name,
    provider: model.provider,
    api_base_url: model.api_base_url,
    api_key: model.api_key,
    model_id: model.model_id,
    max_concurrency: model.max_concurrency,
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
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}
</style>
