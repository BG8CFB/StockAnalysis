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
        <!-- 添加模型 -->
        <el-button
          type="primary"
          :icon="Plus"
          @click="openAddModelDialog()"
        >
          添加模型
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
              prop="platform_type"
              label="类型"
              width="80"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.platform_type === 'preset' ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.platform_type === 'preset' ? '预设' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>
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
              width="240"
              fixed="right"
            >
              <template #default="{ row }">
                <div style="display: flex; gap: 8px; align-items: center;">
                  <el-button
                    link
                    type="primary"
                    :icon="Connection"
                    size="small"
                    @click="handleTest(row)"
                  >
                    测试
                  </el-button>
                  <el-button
                    link
                    type="primary"
                    :icon="Edit"
                    size="small"
                    @click="handleEdit(row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    :icon="Delete"
                    size="small"
                    @click="handleDelete(row)"
                  >
                    删除
                  </el-button>
                </div>
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
              prop="platform_type"
              label="类型"
              width="80"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.platform_type === 'preset' ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.platform_type === 'preset' ? '预设' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>
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
              width="240"
            >
              <template #default="{ row }">
                <div style="display: flex; gap: 8px; align-items: center;">
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
                </div>
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
      width="960px"
      top="5vh"
      destroy-on-close
      @close="handleDialogClose"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <template #title>
          {{ dialogDescription }}
        </template>
      </el-alert>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="top"
        class="model-form"
      >
        <el-row :gutter="24">
          <!-- 左侧列：基础配置与连接 -->
          <el-col :span="12">
            <!-- 基础设置 -->
            <div class="form-section">
              <div class="section-title">
                <el-icon><Setting /></el-icon>
                <span>基础设置</span>
              </div>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item
                    label="模型名称"
                    prop="name"
                  >
                    <el-input
                      v-model="formData.name"
                      placeholder="给模型起个名字"
                      clearable
                    />
                  </el-form-item>
                </el-col>
                <el-col
                  v-if="canManageSystemModels && !isEdit"
                  :span="12"
                >
                  <el-form-item label="模型范围">
                    <el-radio-group v-model="formData.is_system">
                      <el-radio :label="false">
                        个人私有
                      </el-radio>
                      <el-radio :label="true">
                        系统共享
                      </el-radio>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item
                    label="平台类型"
                    prop="platform_type"
                  >
                    <el-radio-group
                      v-model="formData.platform_type"
                      class="w-full"
                      @change="handlePlatformTypeChange"
                    >
                      <el-radio-button value="preset">
                        预设平台
                      </el-radio-button>
                      <el-radio-button value="custom">
                        自定义
                      </el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    v-if="formData.platform_type === 'preset'"
                    label="选择平台"
                    prop="platform_name"
                  >
                    <el-select
                      v-model="formData.platform_name"
                      placeholder="请选择平台"
                      class="w-full"
                      @change="handlePresetPlatformChange"
                    >
                      <el-option
                        v-for="platform in presetPlatforms"
                        :key="platform.id"
                        :label="platform.name"
                        :value="platform.id"
                      >
                        <div class="flex items-center gap-2">
                          <el-icon><component :is="platform.icon" /></el-icon>
                          <span>{{ platform.name }}</span>
                        </div>
                      </el-option>
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </div>

            <!-- 连接配置 -->
            <div class="form-section">
              <div class="section-title">
                <el-icon><Connection /></el-icon>
                <span>连接配置</span>
              </div>

              <el-row :gutter="20">
                <el-col :span="24">
                  <el-form-item
                    label="API 地址"
                    prop="api_base_url"
                  >
                    <el-input
                      v-model="formData.api_base_url"
                      placeholder="例如: https://api.openai.com/v1"
                      :readonly="formData.platform_type === 'preset'"
                    >
                      <template #prefix>
                        <el-icon><Link /></el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                </el-col>
                <el-col :span="24">
                  <el-form-item
                    label="API Key"
                    prop="api_key"
                  >
                    <el-input
                      v-model="formData.api_key"
                      type="password"
                      show-password
                      placeholder="sk-..."
                    >
                      <template #prefix>
                        <el-icon><Key /></el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item
                v-if="formData.platform_type === 'preset' && !manualInputModel"
                label="模型 ID"
                prop="model_id"
              >
                <div class="flex gap-2 w-full">
                  <el-select
                    v-model="formData.model_id"
                    placeholder="选择或输入模型ID"
                    class="flex-1"
                    filterable
                    allow-create
                    @change="handleModelChange"
                  >
                    <el-option
                      v-for="model in availableModels"
                      :key="model"
                      :label="model"
                      :value="model"
                    />
                  </el-select>
                  <el-button
                    :loading="loadingModels"
                    :disabled="!formData.api_key"
                    @click="fetchModels"
                  >
                    获取列表
                  </el-button>
                </div>
                <div class="mt-1">
                  <el-link
                    type="primary"
                    :underline="false"
                    style="font-size: 12px"
                    @click="manualInputModel = true"
                  >
                    切换到手动输入模式
                  </el-link>
                </div>
              </el-form-item>

              <el-form-item
                v-else
                label="模型 ID"
                prop="model_id"
              >
                <div class="flex gap-2 w-full">
                  <el-input
                    v-model="formData.model_id"
                    placeholder="例如: gpt-4o"
                    class="flex-1"
                  />
                  <el-button
                    v-if="formData.platform_type === 'preset'"
                    link
                    type="primary"
                    @click="manualInputModel = false"
                  >
                    返回列表选择
                  </el-button>
                </div>
              </el-form-item>
            </div>
          </el-col>

          <!-- 右侧列：参数与高级 -->
          <el-col :span="12">
            <!-- 运行参数 (直接展开) -->
            <div class="form-section">
              <div class="section-title">
                <div class="flex items-center gap-1">
                  <el-icon><Operation /></el-icon>
                  <span>运行参数</span>
                </div>
              </div>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item
                    label="最大并发"
                    prop="max_concurrency"
                  >
                    <el-input-number
                      v-model="formData.max_concurrency"
                      :min="1"
                      :max="200"
                      class="w-full"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    label="任务并发"
                    prop="task_concurrency"
                  >
                    <el-input-number
                      v-model="formData.task_concurrency"
                      :min="1"
                      :max="10"
                      class="w-full"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item
                    label="批量并发"
                    prop="batch_concurrency"
                  >
                    <el-input-number
                      v-model="formData.batch_concurrency"
                      :min="1"
                      :max="50"
                      class="w-full"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    label="超时(秒)"
                    prop="timeout_seconds"
                  >
                    <el-input-number
                      v-model="formData.timeout_seconds"
                      :min="10"
                      :max="600"
                      class="w-full"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item
                    label="温度 (Temperature)"
                    prop="temperature"
                  >
                    <el-input-number
                      v-model="formData.temperature"
                      :min="0"
                      :max="2"
                      :step="0.1"
                      class="w-full"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="启用状态">
                    <el-switch
                      v-model="formData.enabled"
                      active-text="启用"
                      inactive-text="停用"
                      inline-prompt
                    />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>

            <!-- 高级功能 -->
            <div class="form-section">
              <div class="section-title">
                <el-icon><Cpu /></el-icon>
                <span>高级功能</span>
              </div>

              <el-form-item>
                <template #label>
                  <div class="flex items-center gap-1">
                    <span>思考模式 (Chain of Thought)</span>
                    <el-tag
                      v-if="formData.thinking_enabled"
                      size="small"
                      type="success"
                      effect="plain"
                    >
                      已启用
                    </el-tag>
                  </div>
                </template>
                <div class="thinking-mode-container">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-xs text-gray-500">启用模型推理过程</span>
                    <el-switch v-model="formData.thinking_enabled" />
                  </div>
                  
                  <div
                    v-if="formData.thinking_enabled"
                    class="thinking-options"
                  >
                    <div 
                      v-for="mode in [
                        { val: ThinkingModeEnum.PRESERVED, icon: Document, label: '保留式', desc: '对话保留思考', tags: ['Claude'] },
                        { val: ThinkingModeEnum.CLEAR_ON_NEW, icon: Refresh, label: '轮次清除', desc: '新轮次清空', tags: ['DeepSeek'] },
                        { val: ThinkingModeEnum.AUTO, icon: MagicStick, label: '自动托管', desc: '模型自主管理', tags: ['O1'] }
                      ]"
                      :key="mode.val"
                      class="thinking-option-item"
                      :class="{ active: formData.thinking_mode === mode.val }"
                      @click="formData.thinking_mode = mode.val"
                    >
                      <div class="option-header">
                        <el-icon><component :is="mode.icon" /></el-icon>
                        <span class="font-medium">{{ mode.label }}</span>
                      </div>
                      <div class="option-desc">
                        {{ mode.desc }}
                      </div>
                    </div>
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="自定义请求头">
                <div class="w-full">
                  <div
                    v-for="(value, key) in formData.custom_headers"
                    :key="key"
                    class="flex gap-2 mb-2"
                  >
                    <el-input
                      :model-value="key"
                      readonly
                      class="w-1/3"
                      placeholder="Key"
                    />
                    <el-input
                      v-model="formData.custom_headers[key]"
                      class="flex-1"
                      placeholder="Value"
                    />
                    <el-button
                      type="danger"
                      :icon="Delete"
                      circle
                      plain
                      @click="removeCustomHeader(key as string)"
                    />
                  </div>
                  <el-button
                    type="primary"
                    link
                    :icon="Plus"
                    style="padding: 0;"
                    @click="addCustomHeader"
                  >
                    添加 Header
                  </el-button>
                </div>
              </el-form-item>
            </div>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
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
        </div>
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
import { Plus, Edit, Delete, Connection, QuestionFilled, InfoFilled, Document, Refresh, MagicStick, Setting, Link, Key, Operation, ArrowDown, Cpu } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../store'
import { PROVIDER_PRESETS, ModelProviderEnum, PlatformTypeEnum, PresetPlatformEnum, ThinkingModeEnum, type AIModelConfig, type AIModelConfigCreate } from '../types'
import { PRESET_PLATFORMS, getPresetPlatforms, type PlatformMetadata } from '@core/model/platforms'
import { modelApi } from '../api'

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
const showAdvancedParams = ref(false) // 是否显示高级参数

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
  platform_type: PlatformTypeEnum.CUSTOM,
  platform_name: undefined,
  provider: undefined,
  api_base_url: '',
  api_key: '',
  model_id: '',
  custom_headers: {},
  max_concurrency: 40,
  task_concurrency: 2,
  batch_concurrency: 1,
  timeout_seconds: 60,
  temperature: 0.5,
  enabled: true,
  thinking_enabled: false,  // 是否启用思考模式
  thinking_mode: null,  // 思考模式类型
  is_system: false,
})

// 获取预设平台列表
const presetPlatforms = computed(() => getPresetPlatforms())

// 当前选中的预设平台配置
const currentPresetPlatform = computed(() => {
  if (formData.platform_type === PlatformTypeEnum.PRESET && formData.platform_name) {
    return PRESET_PLATFORMS[formData.platform_name]
  }
  return null
})

// 模型列表
const availableModels = ref<string[]>([])
const loadingModels = ref(false)
const manualInputModel = ref(false)

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

// 当平台类型改变时
function handlePlatformTypeChange() {
  if (formData.platform_type === PlatformTypeEnum.CUSTOM) {
    formData.platform_name = undefined
  }
  availableModels.value = []
  manualInputModel.value = false
}

// 当预设平台改变时
function handlePresetPlatformChange() {
  const platform = currentPresetPlatform.value
  if (platform) {
    formData.api_base_url = platform.baseUrl
    // ❌ 删除：formData.custom_headers = { ...platform.defaultHeaders }
    // ✅ 保持空对象，用户需要额外添加请求头时才显示
    formData.custom_headers = {}
  }
  availableModels.value = []
  manualInputModel.value = false
}

// 获取模型列表
async function fetchModels() {
  if (formData.platform_type !== PlatformTypeEnum.PRESET || !formData.platform_name) {
    return
  }

  loadingModels.value = true
  try {
    const platform = currentPresetPlatform.value

    // 合并默认请求头和用户自定义请求头
    const mergedHeaders = {
      ...(platform?.defaultHeaders || {}),
      ...formData.custom_headers
    }

    const response = await modelApi.listAvailableModels({
      platform_type: formData.platform_type,
      platform_name: formData.platform_name,
      api_base_url: formData.api_base_url,
      api_key: formData.api_key,
      custom_headers: mergedHeaders,
    })

    if (response.success) {
      availableModels.value = response.models.map(m => m.id)
      ElMessage.success(response.message)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取模型列表失败')
  } finally {
    loadingModels.value = false
  }
}

// 当模型选择改变时
function handleModelChange() {
  // 可以在这里添加逻辑
}

// 添加自定义请求头
function addCustomHeader() {
  const key = `custom-header-${Object.keys(formData.custom_headers).length + 1}`
  formData.custom_headers[key] = ''
}

// 删除自定义请求头
function removeCustomHeader(key: string) {
  delete formData.custom_headers[key]
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
function openAddModelDialog() {
  isEdit.value = false
  // 普通用户默认创建个人模型
  formData.is_system = false
  isCreatingSystemModel.value = false
  editingId.value = null

  // 重置表单数据
  Object.assign(formData, {
    name: '',
    platform_type: PlatformTypeEnum.CUSTOM,
    platform_name: undefined,
    provider: undefined,
    api_base_url: '',
    api_key: '',
    model_id: '',
    custom_headers: {},
    max_concurrency: 40,
    task_concurrency: 2,
    batch_concurrency: 1,
    timeout_seconds: 60,
    temperature: 0.5,
    enabled: true,
    is_system: false, // 普通用户默认创建个人模型
  })

  // 重置响应式状态
  availableModels.value = []
  manualInputModel.value = false

  showCreateDialog.value = true
}

// 编辑模型
function handleEdit(model: AIModelConfig) {
  isEdit.value = true
  isCreatingSystemModel.value = model.is_system
  editingId.value = model.id
  Object.assign(formData, {
    name: model.name,
    platform_type: model.platform_type,
    platform_name: model.platform_name,
    provider: model.provider,
    api_base_url: model.api_base_url,
    api_key: model.api_key,
    model_id: model.model_id,
    custom_headers: model.custom_headers || {},
    max_concurrency: model.max_concurrency,
    task_concurrency: model.task_concurrency,
    batch_concurrency: model.batch_concurrency,
    timeout_seconds: model.timeout_seconds,
    temperature: model.temperature,
    enabled: model.enabled,
    thinking_enabled: model.thinking_enabled || false,
    thinking_mode: model.thinking_mode || null,
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

/* Tailwind-like utility classes */
.mb-4 { margin-bottom: 16px; }
.mt-1 { margin-top: 4px; }
.w-full { width: 100%; }
.w-1\/3 { width: 33.33%; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.gap-2 { gap: 8px; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.rotate-180 { transform: rotate(180deg); transition: transform 0.3s; }

/* Form Styling */
.model-form {
  padding: 0 10px;
}

.form-section {
  margin-bottom: 24px;
  background-color: #fcfcfc;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.section-title .el-icon {
  font-size: 18px;
  color: #409eff;
}

/* Thinking Mode Styling */
.thinking-mode-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
  background-color: #fff;
}

.thinking-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.thinking-option-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.thinking-option-item:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.thinking-option-item.active {
  border-color: #409eff;
  background-color: #ecf5ff;
  box-shadow: 0 0 0 1px #409eff inset;
}

.option-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  color: #303133;
}

.option-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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

.form-tip {
  margin-left: 12px;
  font-size: 13px;
  color: #909399;
}

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}
</style>