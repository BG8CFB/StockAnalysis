<template>
  <div class="ai-model-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2>AI 模型管理</h2>
        <p class="page-description">
          配置 AI 模型用于智能分析和 TradingAgents
        </p>
      </div>
      <div class="header-actions">
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
            :data="userModels"
            stripe
            class="model-table"
          >
            <!-- 模型信息 -->
            <el-table-column min-width="300" label="模型信息">
              <template #default="{ row }">
                <div class="model-info-cell">
                  <div class="model-icon user">
                    <el-icon :size="22">
                      <component :is="getModelIcon(row.provider)" />
                    </el-icon>
                  </div>
                  <div class="model-details">
                    <div class="model-name-row">
                      <span class="model-name">{{ row.name }}</span>
                      <el-tag
                        type="primary"
                        size="small"
                        effect="plain"
                      >
                        个人
                      </el-tag>
                    </div>
                    <div class="model-meta">
                      <span class="model-id">{{ row.model_id }}</span>
                      <el-divider direction="vertical" />
                      <span class="provider">{{ getProviderLabel(row.provider || 'custom') }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 平台类型 -->
            <el-table-column width="120" align="center" label="平台类型">
              <template #default="{ row }">
                <el-tag
                  :type="row.platform_type === 'preset' ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.platform_type === 'preset' ? '预设平台' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- API 地址 -->
            <el-table-column min-width="220" show-overflow-tooltip label="API 地址">
              <template #default="{ row }">
                <span class="api-url">{{ row.api_base_url }}</span>
              </template>
            </el-table-column>

            <!-- 并发配置 -->
            <el-table-column width="160" align="center" label="并发配置">
              <template #default="{ row }">
                <div class="concurrency-info">
                  <el-tooltip content="最大并发" placement="top">
                    <span class="concurrency-item">
                      <span class="label">总</span>
                      <span class="value">{{ row.max_concurrency }}</span>
                    </span>
                  </el-tooltip>
                  <el-divider direction="vertical" />
                  <el-tooltip content="任务并发" placement="top">
                    <span class="concurrency-item">
                      <span class="label">任务</span>
                      <span class="value">{{ row.task_concurrency }}</span>
                    </span>
                  </el-tooltip>
                  <el-divider direction="vertical" />
                  <el-tooltip content="批量并发" placement="top">
                    <span class="concurrency-item">
                      <span class="label">批量</span>
                      <span class="value">{{ row.batch_concurrency }}</span>
                    </span>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>

            <!-- 特性 -->
            <el-table-column width="150" label="特性">
              <template #default="{ row }">
                <div class="feature-tags">
                  <el-tag
                    v-if="row.thinking_enabled"
                    type="warning"
                    size="small"
                    effect="plain"
                  >
                    思考模式
                  </el-tag>
                  <el-tag
                    v-if="row.custom_input_price || row.custom_output_price"
                    type="success"
                    size="small"
                    effect="plain"
                  >
                    自定义价格
                  </el-tag>
                </div>
              </template>
            </el-table-column>

            <!-- 状态 -->
            <el-table-column width="90" align="center" label="状态">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  @change="handleToggleEnabled(row)"
                  :active-icon="CircleCheck"
                  :inactive-icon="CircleClose"
                />
              </template>
            </el-table-column>

            <!-- 操作 -->
            <el-table-column width="220" align="center" fixed="right" label="操作">
              <template #default="{ row }">
                <div class="action-buttons">
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

          <!-- 空状态 -->
          <div v-if="userModels.length === 0 && !store.modelsLoading" class="empty-state">
            <el-empty description="您还没有添加个人模型">
              <el-button
                type="primary"
                :icon="Plus"
                @click="openAddModelDialog()"
              >
                添加我的第一个模型
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <!-- 系统模型 -->
        <el-tab-pane
          label="系统模型"
          name="system"
        >
          <el-table
            v-loading="store.modelsLoading"
            :data="systemModels"
            stripe
          >
            <el-table-column
              prop="name"
              label="名称"
              width="160"
            />
            <el-table-column
              prop="model_id"
              label="模型ID"
              min-width="200"
              show-overflow-tooltip
            />
            <el-table-column
              prop="platform_type"
              label="平台类型"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.platform_type === 'preset' ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.platform_type === 'preset' ? '预设平台' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="api_base_url"
              label="API 地址"
              min-width="220"
              show-overflow-tooltip
            />
            <el-table-column
              prop="enabled"
              label="启用"
              width="70"
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
              width="280"
              fixed="right"
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
                <!-- 编辑按钮 - 管理员可见 -->
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
                <!-- 删除按钮 - 管理员可见 -->
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
                <!-- 普通用户看到的提示 -->
                <el-tooltip
                  v-if="!canManageSystemModels"
                  content="系统模型由管理员管理"
                  placement="top"
                >
                  <el-button
                    link
                    type="info"
                    :icon="Lock"
                    size="small"
                  >
                    系统
                  </el-button>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>

          <!-- 空状态 -->
          <div v-if="systemModels.length === 0 && !store.modelsLoading" class="empty-state">
            <el-empty description="暂无系统模型" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="dialogTitle"
      width="1200px"
      top="5vh"
      destroy-on-close
      @close="handleDialogClose"
      class="model-dialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-position="top"
        class="model-form"
      >
        <div class="form-container">
          <!-- 左侧列 -->
          <div class="form-column">
            <!-- 基础信息卡片 -->
            <el-card shadow="never" class="form-card">
              <template #header>
                <div class="card-header">
                  <el-icon class="header-icon" :size="18"><InfoFilled /></el-icon>
                  <span class="header-title">基础信息</span>
                </div>
              </template>

              <el-form-item label="模型名称" prop="name">
                <el-input
                  v-model="formData.name"
                  placeholder="例如: GPT-4 生产环境"
                  clearable
                >
                  <template #prefix>
                    <el-icon><Edit /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="平台类型" prop="platform_type">
                <el-segmented
                  v-model="formData.platform_type"
                  :options="[
                    { label: '预设平台', value: 'preset' },
                    { label: '自定义', value: 'custom' },
                  ]"
                  class="w-full"
                  @change="handlePlatformTypeChange"
                />
              </el-form-item>

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
                    <div class="platform-option">
                      <el-icon><component :is="platform.icon" /></el-icon>
                      <span>{{ platform.name }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item
                v-if="canManageSystemModels && !isEdit"
                label="模型范围"
              >
                <el-segmented
                  v-model="formData.is_system"
                  :options="[
                    { label: '个人私有', value: false },
                    { label: '系统共享', value: true },
                  ]"
                  class="w-full"
                />
                <div class="form-tip">
                  <el-icon><InfoFilled /></el-icon>
                  <span>{{ formData.is_system ? '系统模型对所有用户可见' : '个人模型仅您自己可见' }}</span>
                </div>
              </el-form-item>

              <el-form-item label="启用状态">
                <el-switch
                  v-model="formData.enabled"
                  active-text="启用"
                  inactive-text="禁用"
                  :active-value="true"
                  :inactive-value="false"
                />
              </el-form-item>
            </el-card>

            <!-- 连接配置卡片 -->
            <el-card shadow="never" class="form-card">
              <template #header>
                <div class="card-header required">
                  <el-icon class="header-icon" :size="18"><Connection /></el-icon>
                  <span class="header-title">连接配置</span>
                  <el-tag type="danger" size="small" effect="plain">必填</el-tag>
                </div>
              </template>

              <el-form-item label="API 地址" prop="api_base_url">
                <el-input
                  v-model="formData.api_base_url"
                  placeholder="https://api.openai.com/v1"
                  :readonly="formData.platform_type === 'preset'"
                >
                  <template #prefix>
                    <el-icon><Link /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="API Key" prop="api_key">
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

              <el-form-item label="模型 ID" prop="model_id">
                <template v-if="formData.platform_type === 'preset' && !manualInputModel">
                  <div class="model-select-group">
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
                      <el-icon><Refresh /></el-icon>
                      获取
                    </el-button>
                  </div>
                  <div class="form-tip">
                    <el-link type="primary" :underline="false" @click="manualInputModel = true">
                      <el-icon><Edit /></el-icon>
                      手动输入模型ID
                    </el-link>
                  </div>
                </template>
                <template v-else>
                  <el-input
                    v-model="formData.model_id"
                    placeholder="例如: gpt-4o"
                  >
                    <template #prefix>
                      <el-icon><MagicStick /></el-icon>
                    </template>
                  </el-input>
                  <el-button
                    v-if="formData.platform_type === 'preset'"
                    link
                    type="primary"
                    size="small"
                    class="mt-1"
                    @click="manualInputModel = false"
                  >
                    <el-icon><Monitor /></el-icon>
                    从列表选择
                  </el-button>
                </template>
              </el-form-item>
            </el-card>
          </div>

          <!-- 右侧列 -->
          <div class="form-column">
            <!-- 运行参数卡片 -->
            <el-card shadow="never" class="form-card">
              <template #header>
                <div class="card-header">
                  <el-icon class="header-icon" :size="18"><Operation /></el-icon>
                  <span class="header-title">运行参数</span>
                </div>
              </template>

              <el-form-item label="并发配置">
                <div class="concurrency-grid">
                  <div class="concurrency-item">
                    <div class="concurrency-label">
                      <span>最大并发</span>
                      <el-tooltip content="模型可同时处理的最大请求数" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                    <el-input-number
                      v-model="formData.max_concurrency"
                      :min="1"
                      :max="200"
                      class="w-full"
                      controls-position="right"
                    />
                  </div>
                  <div class="concurrency-item">
                    <div class="concurrency-label">
                      <span>任务并发</span>
                      <el-tooltip content="单个任务可同时运行的智能体数量" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                    <el-input-number
                      v-model="formData.task_concurrency"
                      :min="1"
                      :max="10"
                      class="w-full"
                      controls-position="right"
                    />
                  </div>
                  <div class="concurrency-item">
                    <div class="concurrency-label">
                      <span>批量并发</span>
                      <el-tooltip content="用户可同时运行的批量任务数" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                    <el-input-number
                      v-model="formData.batch_concurrency"
                      :min="1"
                      :max="50"
                      class="w-full"
                      controls-position="right"
                    />
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="超时设置">
                <div class="timeout-config">
                  <el-input-number
                    v-model="formData.timeout_seconds"
                    :min="10"
                    :max="600"
                    :controls-position="right"
                  />
                  <span class="unit-label">秒</span>
                </div>
              </el-form-item>

              <el-form-item label="温度参数">
                <el-slider
                  v-model="formData.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  :marks="{ 0: '0', 1: '1', 2: '2' }"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>
            </el-card>

            <!-- 高级选项卡片 -->
            <el-card shadow="never" class="form-card">
              <template #header>
                <div class="card-header">
                  <el-icon class="header-icon" :size="18"><Cpu /></el-icon>
                  <span class="header-title">高级选项</span>
                </div>
              </template>

              <!-- 思考模式 -->
              <div class="advanced-item">
                <div class="advanced-header">
                  <span class="advanced-label">思考模式</span>
                  <el-tooltip content="启用后，模型会展示推理过程，思考内容会返回给用户" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="advanced-control">
                  <el-switch
                    v-model="formData.thinking_enabled"
                    active-text="已启用"
                    inactive-text="未启用"
                    :active-value="true"
                    :inactive-value="false"
                  />
                  <span class="advanced-desc">模型将返回推理过程</span>
                </div>
              </div>

              <el-divider class="my-4" />

              <!-- 价格配置 -->
              <div class="advanced-item">
                <div class="advanced-header">
                  <span class="advanced-label">价格配置</span>
                  <el-tag
                    v-if="currentModelPrice"
                    type="success"
                    size="small"
                    effect="plain"
                  >
                    已内置
                  </el-tag>
                </div>

                <div v-if="currentModelPrice" class="builtin-price-info">
                  <div class="builtin-price-label">
                    <el-icon><CircleCheck /></el-icon>
                    <span>内置价格（元/百万tokens）</span>
                  </div>
                  <div class="builtin-price-values">
                    <span class="price-tag">输入 {{ currentModelPrice.input_price }}</span>
                    <el-divider direction="vertical" />
                    <span class="price-tag">输出 {{ currentModelPrice.output_price }}</span>
                    <template v-if="currentModelPrice.thinking_price">
                      <el-divider direction="vertical" />
                      <span class="price-tag">思考 {{ currentModelPrice.thinking_price }}</span>
                    </template>
                  </div>
                </div>

                <div class="price-grid">
                  <div class="price-item">
                    <label>输入价格</label>
                    <el-input-number
                      v-model="formData.custom_input_price"
                      :min="0"
                      :precision="4"
                      :step="0.1"
                      :controls="false"
                      placeholder="使用内置"
                      class="w-full"
                    />
                  </div>
                  <div class="price-item">
                    <label>输出价格</label>
                    <el-input-number
                      v-model="formData.custom_output_price"
                      :min="0"
                      :precision="4"
                      :step="0.1"
                      :controls="false"
                      placeholder="使用内置"
                      class="w-full"
                    />
                  </div>
                  <div class="price-item">
                    <label>思考价格</label>
                    <el-input-number
                      v-model="formData.custom_thinking_price"
                      :min="0"
                      :precision="4"
                      :step="0.1"
                      :controls="false"
                      placeholder="选填"
                      class="w-full"
                    />
                  </div>
                </div>
              </div>

              <el-divider class="my-4" />

              <!-- 自定义请求头 -->
              <div class="advanced-item">
                <div class="advanced-header">
                  <span class="advanced-label">自定义请求头</span>
                  <el-tooltip content="为API请求添加自定义HTTP头" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>

                <div class="custom-headers-list">
                  <div
                    v-for="(value, key) in formData.custom_headers"
                    :key="key"
                    class="header-row"
                  >
                    <el-input
                      :model-value="key"
                      readonly
                      placeholder="Header Key"
                      class="header-key"
                    />
                    <el-input
                      v-model="formData.custom_headers[key]"
                      placeholder="Header Value"
                      class="header-value"
                    />
                    <el-button
                      type="danger"
                      :icon="Delete"
                      circle
                      plain
                      size="small"
                      @click="removeCustomHeader(key as string)"
                    />
                  </div>

                  <el-button
                    type="primary"
                    plain
                    :icon="Plus"
                    size="small"
                    @click="addCustomHeader"
                  >
                    添加请求头
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button size="large" @click="showCreateDialog = false">
            取消
          </el-button>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            @click="handleSubmit"
          >
            {{ isEdit ? '保存更改' : '创建模型' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 测试连接对话框 -->
    <el-dialog
      v-model="showTestDialog"
      title="测试连接"
      width="480px"
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
            <p v-if="testResult.latency_ms" class="latency">
              延迟: <strong>{{ testResult.latency_ms }}ms</strong>
            </p>
          </template>
        </el-result>
      </div>
      <div
        v-else
        class="test-loading"
      >
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>正在测试连接...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Edit, Delete, Connection, Link, Key, Operation, Cpu,
  QuestionFilled, Refresh, CircleCheck, CircleClose,
  Lock, Monitor, Platform, ChatDotRound, Tools, Sunny, InfoFilled,
  Loading, MagicStick
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useAIModelStore } from '../stores/ai-model'
import {
  PROVIDER_PRESETS,
  ModelProviderEnum,
  PlatformTypeEnum,
  type AIModelConfig,
  type AIModelConfigCreate
} from '../types/ai-model'
import { PRESET_PLATFORMS, getPresetPlatforms } from '@core/model/platforms'
import { modelApi } from '../api/ai-model'

const userStore = useUserStore()
const store = useAIModelStore()

// 是否为管理员或超管（可以管理系统模型）
const canManageSystemModels = computed(() =>
  userStore.userInfo?.role === 'ADMIN' || userStore.userInfo?.role === 'SUPER_ADMIN'
)

// 所有模型（合并系统和个人）
const allModels = computed(() => store.allModels)

// 当前标签页
const activeTab = ref('user')

// 个人模型
const userModels = computed(() => allModels.value.filter(m => !m.is_system))

// 系统模型
const systemModels = computed(() => allModels.value.filter(m => m.is_system))

// 对话框状态
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)
const isCreatingSystemModel = ref(false)

// 对话框标题
const dialogTitle = computed(() => {
  if (isEdit.value) {
    return '编辑 AI 模型'
  }
  return isCreatingSystemModel.value ? '添加系统模型' : '添加个人模型'
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
  thinking_enabled: false,
  custom_input_price: null,
  custom_output_price: null,
  custom_thinking_price: null,
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

// 内置模型价格
const BUILTIN_MODEL_PRICES: Record<string, { input_price: number; output_price: number; thinking_price?: number }> = {
  'glm-4.5': { input_price: 0.8, output_price: 2 },
  'glm-4-plus': { input_price: 5, output_price: 15 },
  'glm-4-plus-coder': { input_price: 5, output_price: 15 },
  'glm-4-air': { input_price: 1, output_price: 2 },
  'glm-4-flash': { input_price: 0.1, output_price: 0.2 },
  'glm-4.7': { input_price: 5, output_price: 15, thinking_price: 15 },
  'glm-4.6': { input_price: 5, output_price: 15 },
  'glm-4': { input_price: 5, output_price: 15 },
  'deepseek-chat': { input_price: 4, output_price: 12 },
  'deepseek-coder': { input_price: 4, output_price: 12 },
  'deepseek-reasoner': { input_price: 4, output_price: 12 },
  'qwen-max': { input_price: 2.4, output_price: 9.6 },
  'qwen-plus': { input_price: 0.8, output_price: 2 },
  'qwen-turbo': { input_price: 0.4, output_price: 1 },
  'moonshot-v1-8k': { input_price: 1.2, output_price: 3 },
  'moonshot-v1-32k': { input_price: 2.4, output_price: 6 },
  'moonshot-v1-128k': { input_price: 10, output_price: 30 },
}

// 当前选中模型的内置价格
const currentModelPrice = computed(() => {
  if (formData.model_id && formData.model_id in BUILTIN_MODEL_PRICES) {
    return BUILTIN_MODEL_PRICES[formData.model_id]
  }
  return null
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' },
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

// 获取提供商标签
function getProviderLabel(provider: ModelProviderEnum | string): string {
  return PROVIDER_PRESETS[provider as ModelProviderEnum]?.name || provider
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
  formData.is_system = false
  isCreatingSystemModel.value = false
  editingId.value = null

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
    thinking_enabled: false,
    custom_input_price: null,
    custom_output_price: null,
    custom_thinking_price: null,
    is_system: false,
  })

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
    custom_input_price: model.custom_input_price || null,
    custom_output_price: model.custom_output_price || null,
    custom_thinking_price: model.custom_thinking_price || null,
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
.ai-model-management {
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

/* 空状态 */
.empty-state {
  padding: 60px 20px;
  text-align: center;
}

/* ========================================
   对话框样式优化
   ======================================== */

.model-dialog {
  border-radius: 12px;
}

.model-dialog .el-dialog__body {
  padding: 20px;
}

.model-dialog .el-dialog__footer {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
}

/* 表单容器布局 */
.form-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 表单卡片 */
.form-card {
  height: fit-content;
}

.form-card :deep(.el-card__header) {
  padding: 14px 18px;
  background: #fafbfc;
  border-bottom: 1px solid #ebeef5;
}

.form-card :deep(.el-card__body) {
  padding: 18px;
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header .header-icon {
  color: #409eff;
}

.card-header .header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.card-header.required .header-title::after {
  content: '*';
  color: #f56c6c;
  margin-left: 4px;
}

/* 表单优化 */
.model-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.model-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

/* 提示信息 */
.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  display: flex;
  align-items: center;
  gap: 4px;
}

.form-tip .el-icon {
  font-size: 14px;
}

/* 模型选择组 */
.model-select-group {
  display: flex;
  gap: 10px;
}

.model-select-group .flex-1 {
  flex: 1;
}

/* 平台选项 */
.platform-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 并发配置网格 */
.concurrency-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.concurrency-item {
  display: flex;
  flex-direction: column;
}

.concurrency-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.concurrency-label .el-icon {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

/* 超时配置 */
.timeout-config {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timeout-config .el-input-number {
  flex: 1;
}

.timeout-config .unit-label {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

/* 高级选项 */
.advanced-item {
  margin-bottom: 8px;
}

.advanced-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.advanced-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.advanced-header .el-icon {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

.advanced-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.advanced-desc {
  font-size: 13px;
  color: #606266;
}

/* 内置价格信息 */
.builtin-price-info {
  padding: 10px 14px;
  background-color: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  margin-bottom: 12px;
}

.builtin-price-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #0369a1;
  margin-bottom: 6px;
  font-weight: 500;
}

.builtin-price-label .el-icon {
  color: #0ea5e9;
}

.builtin-price-values {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.price-tag {
  font-size: 12px;
  color: #0369a1;
}

/* 价格输入网格 */
.price-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.price-item {
  display: flex;
  flex-direction: column;
}

.price-item label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

/* 自定义请求头列表 */
.custom-headers-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.header-row {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 10px;
  align-items: center;
}

.header-key {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.header-value {
  font-size: 13px;
}

/* 分隔线 */
.my-4 {
  margin: 16px 0;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 测试结果 */
.test-result,
.test-loading {
  text-align: center;
  padding: 20px 0;
}

.test-loading .el-icon {
  font-size: 32px;
  color: #409eff;
}

.test-loading p {
  margin: 12px 0 0 0;
  color: #909399;
}

.test-result .latency {
  color: #67c23a;
  font-size: 14px;
}

/* 通用样式 */
.w-full { width: 100%; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
</style>
