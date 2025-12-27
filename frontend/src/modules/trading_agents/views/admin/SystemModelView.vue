<template>
  <div class="system-model-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>系统 AI 模型管理</h2>
      <el-button
        type="primary"
        :icon="Plus"
        @click="showCreateDialog = true"
      >
        创建系统模型
      </el-button>
    </div>

    <!-- 统计信息 -->
    <el-row
      :gutter="16"
      class="stats-row"
    >
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="总模型数"
            :value="stats.total"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="系统模型"
            :value="stats.system"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="用户模型"
            :value="stats.user"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="已启用"
            :value="stats.enabled"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选 -->
    <el-card
      shadow="never"
      class="filter-card"
    >
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 140px"
            @change="fetchData"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="已启用"
              value="enabled"
            />
            <el-option
              label="已禁用"
              value="disabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="提供商">
          <el-select
            v-model="filters.provider"
            placeholder="全部"
            clearable
            style="width: 150px"
            @change="fetchData"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              v-for="p in providerOptions"
              :key="p.value"
              :label="p.name"
              :value="p.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :icon="Refresh"
            @click="fetchData"
          >
            刷新
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 模型列表 -->
    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="models"
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
              :type="row.is_system ? 'info' : ''"
              size="small"
            >
              {{ getProviderLabel(row.provider) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="model_id"
          label="模型 ID"
          width="150"
          show-overflow-tooltip
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
          prop="timeout_seconds"
          label="超时(秒)"
          width="80"
        />
        <el-table-column
          prop="temperature"
          label="温度"
          width="80"
        />
        <el-table-column
          prop="enabled"
          label="状态"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.enabled ? 'success' : 'danger'"
              size="small"
            >
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="is_system"
          label="类型"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.is_system ? 'warning' : ''"
              size="small"
            >
              {{ row.is_system ? '系统' : '用户' }}
            </el-tag>
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
              v-if="row.is_system"
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

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建系统模型"
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
              v-for="p in providerOptions"
              :key="p.value"
              :label="p.name"
              :value="p.value"
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
          <span class="form-tip">用户可同时运行的批量任务数</span>
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
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Connection, Delete } from '@element-plus/icons-vue'
import { httpGet, httpPost, httpDelete } from '@/core/api/http'
import { PROVIDER_PRESETS, type AIModelConfig } from '../../types'

// 状态
const loading = ref(false)
const submitting = ref(false)
const models = ref<AIModelConfig[]>([])

// 统计
const stats = ref({
  total: 0,
  system: 0,
  user: 0,
  enabled: 0,
})

// 筛选
const filters = reactive({
  status: '',
  provider: '',
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0,
})

// 对话框
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const testResult = ref<{ success: boolean; message: string; latency_ms?: number } | null>(null)

// 表单
const formRef = ref()
const formData = reactive({
  name: '',
  provider: 'zhipu',
  api_base_url: '',
  api_key: '',
  model_id: '',
  max_concurrency: 40,
  task_concurrency: 2,
  batch_concurrency: 1,
  timeout_seconds: 60,
  temperature: 0.5,
})

const formRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_base_url: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }],
  model_id: [{ required: true, message: '请输入模型 ID', trigger: 'blur' }],
}

// 提供商选项
const providerOptions = computed(() => Object.values(PROVIDER_PRESETS))

// 获取提供商标签
function getProviderLabel(provider: string): string {
  return PROVIDER_PRESETS[provider]?.name || provider
}

// 提供商变更
function handleProviderChange(provider: string) {
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

// 获取数据
async function fetchData() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(pagination.size),
      offset: String((pagination.page - 1) * pagination.size),
    })

    const response = await httpGet<any>(`/api/admin/trading-agents/models?${params}`)
    models.value = [...response.system, ...response.user]

    // 更新统计
    stats.value = {
      total: response.total,
      system: response.system.length,
      user: response.user.length,
      enabled: models.value.filter(m => m.enabled).length,
    }

    pagination.total = response.total
  } finally {
    loading.value = false
  }
}

// 提交表单
async function handleSubmit() {
  await formRef.value?.validate()

  if (!validateConcurrency()) {
    return
  }

  submitting.value = true

  try {
    await httpPost('/api/admin/trading-agents/models', null, {
      params: {
        name: formData.name,
        provider: formData.provider,
        api_base_url: formData.api_base_url,
        api_key: formData.api_key,
        model_id: formData.model_id,
        max_concurrency: formData.max_concurrency,
        task_concurrency: formData.task_concurrency,
        batch_concurrency: formData.batch_concurrency,
        timeout_seconds: formData.timeout_seconds,
        temperature: formData.temperature,
      }
    })
    ElMessage.success('系统模型创建成功')
    showCreateDialog.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

// 删除模型
async function handleDelete(model: AIModelConfig) {
  try {
    await ElMessageBox.confirm(`确定要删除系统模型 "${model.name}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await httpDelete(`/api/admin/trading-agents/models/${model.id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // 用户取消
  }
}

// 测试连接
async function handleTest(model: AIModelConfig) {
  showTestDialog.value = true
  testResult.value = null

  try {
    // 使用普通用户的测试接口
    const result = await httpPost(`/api/trading-agents/models/${model.id}/test`, {})
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
  formRef.value?.resetFields()
}

// 初始化
onMounted(fetchData)
</script>

<style scoped>
.system-model-view {
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

.stats-row {
  margin-bottom: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}
</style>
