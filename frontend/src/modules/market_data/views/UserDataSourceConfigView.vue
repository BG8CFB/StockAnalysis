<template>
  <div class="user-data-source-config-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon
          class="header-icon"
          :size="24"
        >
          <Connection />
        </el-icon>
        <div>
          <h2>数据源配置</h2>
          <p class="description">
            管理您的金融数据接入点
          </p>
        </div>
      </div>
      <el-button
        type="primary"
        :icon="Plus"
        @click="handleCreate"
      >
        添加数据源
      </el-button>
    </div>

    <!-- 市场切换标签 -->
    <el-card
      shadow="never"
      class="market-card"
    >
      <el-radio-group
        v-model="activeMarket"
        size="large"
        @change="handleMarketChange"
      >
        <el-radio-button
          v-for="market in markets"
          :key="market.value"
          :value="market.value"
        >
          {{ market.label }}
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- 数据源卡片列表 -->
    <el-row
      v-loading="loading"
      :gutter="16"
    >
      <el-col
        v-for="(config, index) in filteredConfigs"
        :key="`${config.source_id}-${config.market}`"
        :xs="24"
        :sm="12"
        :lg="8"
        :xl="6"
      >
        <el-card
          shadow="hover"
          :class="['source-card', { disabled: !config.enabled }]"
        >
          <!-- 卡片头部 -->
          <template #header>
            <div class="card-header">
              <div class="source-info">
                <div
                  class="source-icon"
                  :class="`icon-${config.source_id}`"
                >
                  {{ getSourceIcon(config.source_id) }}
                </div>
                <div class="source-details">
                  <h4 class="source-name">
                    {{ getDataSourceDisplayName(config.source_id) }}
                  </h4>
                  <p class="source-market">
                    {{ MarketTypeName[config.market as MarketType] }}
                  </p>
                </div>
              </div>
              <el-tag
                :type="config.enabled ? 'success' : 'info'"
                size="small"
                effect="plain"
              >
                {{ config.enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </div>
          </template>

          <!-- 卡片内容 -->
          <div class="card-content">
            <div class="info-item">
              <span class="info-label">优先级</span>
              <el-rate
                v-model="config.priority"
                disabled
                show-score
                score-template="{value}"
                size="small"
              />
            </div>

            <div class="info-item">
              <span class="info-label">API Token</span>
              <span class="token-masked">••••••••••••</span>
            </div>

            <div
              v-if="config.last_test_time"
              class="info-item"
            >
              <span class="info-label">最后检查</span>
              <span class="info-value">{{ formatTime(config.last_test_time) }}</span>
            </div>

            <div
              v-if="config.last_test_status"
              class="info-item"
            >
              <span class="info-label">连接状态</span>
              <el-tag
                :type="config.last_test_status === 'success' ? 'success' : 'danger'"
                size="small"
                effect="plain"
              >
                {{ config.last_test_status === 'success' ? '正常' : '异常' }}
              </el-tag>
            </div>
          </div>

          <!-- 卡片操作 -->
          <template #footer>
            <div class="card-actions">
              <el-button
                type="primary"
                link
                :loading="testing === config.source_id"
                @click="handleTest(config)"
              >
                <el-icon><Connection /></el-icon>
                测试连接
              </el-button>
              <el-button
                type="primary"
                link
                @click="handleEdit(config)"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button
                type="danger"
                link
                @click="handleDelete(config)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- 添加新数据源卡片 -->
      <el-col
        v-if="!loading"
        :xs="24"
        :sm="12"
        :lg="8"
        :xl="6"
      >
        <el-card
          shadow="hover"
          class="add-card"
          @click="handleCreate"
        >
          <div class="add-card-content">
            <el-icon
              :size="48"
              color="var(--color-text-tertiary)"
            >
              <Plus />
            </el-icon>
            <p class="add-text">
              添加新数据源
            </p>
            <p class="add-hint">
              {{ MarketTypeName[activeMarket as MarketType] }}
            </p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && filteredConfigs.length === 0"
      description="暂无数据源配置"
      :image-size="120"
    >
      <el-button
        type="primary"
        @click="handleCreate"
      >
        立即添加
      </el-button>
    </el-empty>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '添加数据源' : '编辑数据源'"
      width="600px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="left"
      >
        <el-form-item
          label="市场类型"
          prop="market"
        >
          <el-select
            v-model="formData.market"
            placeholder="选择市场"
            :disabled="dialogMode === 'edit'"
            style="width: 100%"
          >
            <el-option
              v-for="market in markets"
              :key="market.value"
              :label="market.label"
              :value="market.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="数据源"
          prop="source_id"
        >
          <el-select
            v-model="formData.source_id"
            placeholder="选择数据源"
            :disabled="dialogMode === 'edit'"
            style="width: 100%"
            @change="handleSourceChange"
          >
            <el-option
              v-for="source in availableDataSources"
              :key="source.id"
              :label="source.name"
              :value="source.id"
            >
              <div class="source-option">
                <span class="option-icon">{{ getSourceIcon(source.id) }}</span>
                <span class="option-label">{{ source.name }}</span>
              </div>
            </el-option>
          </el-select>
          <div
            v-if="selectedDataSourceInfo"
            class="form-tip"
          >
            <el-text
              type="info"
              size="small"
            >
              {{ selectedDataSourceInfo.description }}
            </el-text>
            <el-link
              :href="selectedDataSourceInfo.doc_url"
              target="_blank"
              type="primary"
              :underline="false"
            >
              查看文档
            </el-link>
          </div>
        </el-form-item>

        <el-form-item
          label="API Key"
          prop="api_key"
        >
          <el-input
            v-model="formData.api_key"
            placeholder="请输入 API Key"
            :type="showApiKey ? 'text' : 'password'"
            show-password
          >
            <template #suffix>
              <el-icon
                class="password-toggle"
                @click="showApiKey = !showApiKey"
              >
                <View v-if="!showApiKey" />
                <Hide v-else />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item
          label="优先级"
          prop="priority"
        >
          <el-select
            v-model="formData.priority"
            style="width: 100%"
          >
            <el-option
              :label="'优先级 1（最高）'"
              :value="1"
            />
            <el-option
              :label="'优先级 2'"
              :value="2"
            />
            <el-option
              :label="'优先级 3'"
              :value="3"
            />
            <el-option
              :label="'优先级 4'"
              :value="4"
            />
            <el-option
              :label="'优先级 5（最低）'"
              :value="5"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="启用状态"
          prop="enabled"
        >
          <el-switch
            v-model="formData.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  Connection,
  Edit,
  Delete,
  View,
  Hide,
} from '@element-plus/icons-vue'
import userDataSourceApi from '../api/userDataSourceApi'
import { MarketType, MarketTypeName } from '../types'
import type {
  UserDataSourceConfig,
  CreateUserDataSourceConfigRequest,
  UpdateUserDataSourceConfigRequest,
} from '../api/userDataSourceApi'

// 状态
const loading = ref(false)
const testing = ref<string | null>(null)
const submitting = ref(false)
const activeMarket = ref<MarketType>(MarketType.A_STOCK)
const configs = ref<UserDataSourceConfig[]>([])
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const showApiKey = ref(false)
const formRef = ref<FormInstance>()

// 市场选项
const markets: Array<{ label: string; value: MarketType }> = [
  { label: 'A股', value: MarketType.A_STOCK },
  { label: '美股', value: MarketType.US_STOCK },
  { label: '港股', value: MarketType.HK_STOCK },
]

// 数据源选项（仅包含需要用户配置 API Key 的付费数据源）
// 注意：AkShare、Yahoo Finance 等免费数据源是系统内置的备用数据源，
// 当付费数据源失败时会自动降级使用，不需要用户配置
const dataSources = [
  {
    id: 'tushare',
    name: 'TuShare Pro',
    market: MarketType.A_STOCK,
    description: 'A股数据最全面的专业财经数据接口，需要 API Token',
    doc_url: 'https://tushare.pro',
  },
  {
    id: 'alpha_vantage',
    name: 'Alpha Vantage',
    market: MarketType.US_STOCK,
    description: '提供美股、外汇、加密货币等金融数据API，需要 API Key',
    doc_url: 'https://www.alphavantage.co',
  },
]

// 表单数据
const formData = ref<CreateUserDataSourceConfigRequest>({
  source_id: '',
  market: MarketType.A_STOCK,
  api_key: '',
  enabled: true,
  priority: 3,
})

// 当前编辑的配置
const currentEditConfig = ref<UserDataSourceConfig | null>(null)

// 表单验证规则
const formRules: FormRules = {
  market: [{ required: true, message: '请选择市场类型', trigger: 'change' }],
  source_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  api_key: [
    { required: true, message: '请输入 API Key', trigger: 'blur' },
    { min: 1, message: 'API Key 不能为空', trigger: 'blur' },
  ],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
}

// 可用数据源（根据选中的市场过滤）
const availableDataSources = computed(() => {
  return dataSources.filter(s => s.market === formData.value.market)
})

// 选中的数据源信息
const selectedDataSourceInfo = computed(() => {
  return dataSources.find(s => s.id === formData.value.source_id)
})

// 过滤后的配置列表
const filteredConfigs = computed(() => {
  return configs.value.filter(c => c.market === activeMarket.value)
})

// 获取数据源显示名称
const getDataSourceDisplayName = (sourceId: string) => {
  const source = dataSources.find(s => s.id === sourceId)
  return source?.name || sourceId
}

// 获取数据源图标
const getSourceIcon = (sourceId: string) => {
  const icons: Record<string, string> = {
    tushare: '📊',
    alpha_vantage: '🔔',
  }
  return icons[sourceId] || '📡'
}

// 格式化时间
const formatTime = (timeStr?: string | null) => {
  if (!timeStr) return '-'
  try {
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`

    return date.toLocaleDateString('zh-CN')
  } catch {
    return timeStr
  }
}

// 获取配置列表
const fetchConfigs = async () => {
  try {
    loading.value = true
    const data = await userDataSourceApi.getConfigs(activeMarket.value, false)
    configs.value = data
  } catch (error: any) {
    ElMessage.error(`获取配置失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

// 市场变更
const handleMarketChange = () => {
  fetchConfigs()
}

// 创建新配置
const handleCreate = () => {
  dialogMode.value = 'create'
  formData.value = {
    source_id: '',
    market: activeMarket.value,
    api_key: '',
    enabled: true,
    priority: 3,
  }
  currentEditConfig.value = null
  dialogVisible.value = true
}

// 编辑配置
const handleEdit = (config: UserDataSourceConfig) => {
  dialogMode.value = 'edit'
  formData.value = {
    source_id: config.source_id,
    market: config.market as MarketType,
    api_key: config.config.api_key,
    enabled: config.enabled,
    priority: config.priority,
  }
  currentEditConfig.value = config
  dialogVisible.value = true
}

// 删除配置
const handleDelete = async (config: UserDataSourceConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${getDataSourceDisplayName(config.source_id)} 吗？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await userDataSourceApi.deleteConfig(config.source_id, config.market)
    ElMessage.success('删除成功')
    await fetchConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message || '未知错误'}`)
    }
  }
}

// 测试连接
const handleTest = async (config: UserDataSourceConfig) => {
  try {
    testing.value = config.source_id
    const result = await userDataSourceApi.testConfig(config.source_id, config.market)

    if (result.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(`连接测试失败: ${result.error || '未知错误'}`)
    }

    await fetchConfigs()
  } catch (error: any) {
    ElMessage.error(`测试失败: ${error.message || '未知错误'}`)
  } finally {
    testing.value = null
  }
}

// 数据源变更
const handleSourceChange = () => {
  // 数据源变更时的处理逻辑
}

// 关闭对话框
const closeDialog = () => {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (dialogMode.value === 'create') {
      await userDataSourceApi.createConfig(formData.value)
      ElMessage.success('创建成功')
    } else {
      const updateData: UpdateUserDataSourceConfigRequest = {
        api_key: formData.value.api_key,
        enabled: formData.value.enabled,
        priority: formData.value.priority,
      }
      await userDataSourceApi.updateConfig(
        currentEditConfig.value!.source_id,
        currentEditConfig.value!.market,
        updateData
      )
      ElMessage.success('保存成功')
    }

    closeDialog()
    await fetchConfigs()
  } catch (error: any) {
    if (error !== false) {
      ElMessage.error(`${dialogMode.value === 'create' ? '创建' : '保存'}失败: ${error.message || '未知错误'}`)
    }
  } finally {
    submitting.value = false
  }
}

// 初始化
onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="scss">
.user-data-source-config-view {
  padding: var(--space-5);

  // 页面标题
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-5);

    .header-content {
      display: flex;
      align-items: center;
      gap: var(--space-3);

      .header-icon {
        color: var(--color-primary);
      }

      h2 {
        margin: 0;
        font-size: var(--font-size-xxl);
        font-weight: var(--font-weight-semibold);
        color: var(--color-text-primary);
      }

      .description {
        margin: var(--space-1) 0 0 0;
        font-size: var(--font-size-sm);
        color: var(--color-text-tertiary);
      }
    }
  }

  // 市场切换卡片
  .market-card {
    margin-bottom: var(--space-5);

    :deep(.el-card__body) {
      padding: var(--space-4);
    }
  }

  // 数据源卡片
  .source-card {
    margin-bottom: var(--space-4);
    transition: all var(--duration-base) var(--ease-out-cubic);

    &.disabled {
      opacity: 0.6;
    }

    :deep(.el-card__header) {
      padding: var(--space-4);
      background-color: var(--color-bg-spotlight);
      border-bottom: 1px solid var(--color-border-secondary);
    }

    :deep(.el-card__body) {
      padding: var(--space-4);
    }

    :deep(.el-card__footer) {
      padding: var(--space-3) var(--space-4);
      background-color: var(--color-bg-spotlight);
      border-top: 1px solid var(--color-border-secondary);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .source-info {
        display: flex;
        align-items: center;
        gap: var(--space-3);

        .source-icon {
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          background: var(--gradient-primary);
          border-radius: var(--radius-lg);
          color: white;
        }

        .source-details {
          .source-name {
            margin: 0;
            font-size: var(--font-size-base);
            font-weight: var(--font-weight-semibold);
            color: var(--color-text-primary);
          }

          .source-market {
            margin: var(--space-1) 0 0 0;
            font-size: var(--font-size-xs);
            color: var(--color-text-tertiary);
          }
        }
      }
    }

    .card-content {
      .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-2) 0;

        &:not(:last-child) {
          border-bottom: 1px solid var(--color-border-tertiary);
        }

        .info-label {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
        }

        .token-masked {
          font-family: var(--font-family-code);
          font-size: var(--font-size-sm);
          color: var(--color-text-tertiary);
          letter-spacing: 2px;
        }

        .info-value {
          font-size: var(--font-size-sm);
          color: var(--color-text-primary);
        }

        :deep(.el-rate) {
          .el-rate__icon {
            font-size: 14px;
          }
        }
      }
    }

    .card-actions {
      display: flex;
      gap: var(--space-2);
      justify-content: flex-end;

      .el-button {
        margin: 0;
      }
    }
  }

  // 添加卡片
  .add-card {
    margin-bottom: var(--space-4);
    cursor: pointer;
    transition: all var(--duration-base) var(--ease-out-cubic);

    &:hover {
      border-color: var(--color-primary);
      box-shadow: var(--shadow-primary);
    }

    :deep(.el-card__body) {
      padding: var(--space-8);
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 200px;
    }

    .add-card-content {
      text-align: center;

      .add-text {
        margin: var(--space-3) 0 var(--space-1);
        font-size: var(--font-size-base);
        font-weight: var(--font-weight-medium);
        color: var(--color-text-primary);
      }

      .add-hint {
        margin: 0;
        font-size: var(--font-size-sm);
        color: var(--color-text-tertiary);
      }
    }
  }

  // 空状态
  .el-empty {
    padding: var(--space-16) 0;
  }

  // 对话框
  .form-tip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--space-2);
  }

  .password-toggle {
    cursor: pointer;
    color: var(--color-text-tertiary);
    transition: color var(--duration-fast) var(--ease-out-cubic);

    &:hover {
      color: var(--color-primary);
    }
  }

  .source-option {
    display: flex;
    align-items: center;
    gap: var(--space-2);

    .option-icon {
      font-size: var(--font-size-lg);
    }

    .option-label {
      font-size: var(--font-size-base);
    }
  }
}

// 响应式
@media (max-width: 768px) {
  .user-data-source-config-view {
    padding: var(--space-3);

    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-3);

      .header-content {
        width: 100%;
      }

      .el-button {
        width: 100%;
      }
    }
  }
}
</style>
