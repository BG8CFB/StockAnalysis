<template>
  <div class="user-data-source-config-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>数据源配置</h2>
      <el-button type="primary" @click="handleCreate" :icon="Plus">
        添加数据源
      </el-button>
    </div>

    <!-- 市场标签页 -->
    <el-tabs v-model="activeMarket" @tab-change="handleMarketChange" class="market-tabs">
      <el-tab-pane label="A股" :name="MarketType.A_STOCK" />
      <el-tab-pane label="美股" :name="MarketType.US_STOCK" />
      <el-tab-pane label="港股" :name="MarketType.HK_STOCK" />
    </el-tabs>

    <!-- 数据源卡片列表 -->
    <div v-loading="loading" class="cards-container">
      <div
        v-for="config in filteredConfigs"
        :key="`${config.source_id}-${config.market}`"
        class="source-card"
      >
        <!-- 卡片头部 -->
        <div class="card-header">
          <h3 class="card-title">{{ getDataSourceDisplayName(config.source_id) }}</h3>
          <p class="card-description">{{ getDataSourceDescription(config.source_id) }}</p>
        </div>

        <!-- 状态信息 -->
        <div class="card-status">
          <div class="status-item">
            <span class="status-label">状态:</span>
            <el-tag
              v-if="config.last_test_time && config.last_test_status === 'success'"
              type="success"
              size="small"
            >
              ✅ 已连接
            </el-tag>
            <el-tag
              v-else-if="config.last_test_time && config.last_test_status === 'failed'"
              type="danger"
              size="small"
            >
              ❌ 连接失败
            </el-tag>
            <el-tag v-else type="info" size="small">
              未连接
            </el-tag>
          </div>
          <div class="status-item">
            <span class="status-label">最后检查:</span>
            <span class="status-value">{{ config.last_test_time ? formatTime(config.last_test_time) : '未测试' }}</span>
          </div>
        </div>

        <!-- 配置信息 -->
        <div class="card-config">
          <div class="config-item">
            <span class="config-label">API Token:</span>
            <span class="config-value masked">••••••••••••••••</span>
          </div>
          <div class="config-item">
            <span class="config-label">优先级:</span>
            <el-tag type="primary" size="small">{{ config.priority }}</el-tag>
          </div>
          <div class="config-item">
            <span class="config-label">启用状态:</span>
            <el-tag :type="config.enabled ? 'success' : 'info'" size="small">
              {{ config.enabled ? '✅ 启用' : '已禁用' }}
            </el-tag>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="card-actions">
          <el-button
            type="primary"
            link
            size="small"
            @click="handleTest(config)"
            :loading="testing === config.source_id"
          >
            测试连接
          </el-button>
          <el-button type="primary" link size="small" @click="handleEdit(config)">
            编辑
          </el-button>
          <el-button type="danger" link size="small" @click="handleDelete(config)">
            删除
          </el-button>
        </div>
      </div>

      <!-- 添加新数据源卡片 -->
      <div v-if="filteredConfigs.length === 0" class="source-card add-card" @click="handleCreate">
        <div class="add-card-content">
          <el-icon :size="48" color="#909399">
            <Plus />
          </el-icon>
          <p>添加新的数据源</p>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && filteredConfigs.length === 0"
      :description="`暂无${MarketTypeName[activeMarket]}用户数据源配置`"
    />

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '添加数据源' : '编辑数据源'"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        size="small"
      >
        <el-form-item label="市场类型" prop="market">
          <el-select
            v-model="formData.market"
            placeholder="请选择市场类型"
            :disabled="dialogMode === 'edit'"
            style="width: 100%"
          >
            <el-option label="A股" value="A_STOCK" />
            <el-option label="美股" value="US_STOCK" />
            <el-option label="港股" value="HK_STOCK" :disabled="true" />
          </el-select>
        </el-form-item>

        <el-form-item label="数据源" prop="source_id">
          <el-select
            v-model="formData.source_id"
            placeholder="请选择数据源"
            :disabled="dialogMode === 'edit'"
            style="width: 100%"
            @change="handleDataSourceChange"
          >
            <el-option
              v-for="source in availableDataSources"
              :key="source.id"
              :label="source.name"
              :value="source.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="请输入 API Key"
            show-password
            clearable
          />
          <div v-if="selectedDataSourceInfo" class="form-tip">
            <el-text type="info" size="small">
              {{ selectedDataSourceInfo.description }}
            </el-text>
            <el-link
              :href="selectedDataSourceInfo.doc_url"
              target="_blank"
              type="primary"
              style="margin-left: 8px"
            >
              查看文档
            </el-link>
          </div>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-input-number
            v-model="formData.priority"
            :min="1"
            :max="10"
            placeholder="数字越小优先级越高"
            style="width: 100%"
          />
          <div class="form-tip">
            <el-text type="info" size="small">
              数字越小优先级越高，系统将优先使用高优先级的数据源
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { MarketType, MarketTypeName } from '../types'
import userDataSourceApi from '../api/userDataSourceApi'

// 数据源配置信息
const DATA_SOURCE_INFO: Record<string, { name: string; description: string; doc_url: string }> = {
  tushare_pro: {
    name: 'TuShare Pro',
    description: 'TuShare Pro 是中国领先的金融数据接口',
    doc_url: 'https://tushare.pro/document/2'
  },
  alpha_vantage: {
    name: 'Alpha Vantage',
    description: '美股数据提供商，提供免费和付费 API',
    doc_url: 'https://www.alphavantage.co/documentation/'
  },
  tushare: {
    name: 'TuShare',
    description: 'TuShare 是中国领先的金融数据接口',
    doc_url: 'https://tushare.pro/document/2'
  },
  akshare: {
    name: 'AkShare',
    description: 'AkShare 是一个免费的开源财经数据接口库',
    doc_url: 'https://akshare.akfamily.xyz'
  },
  yahoo: {
    name: 'Yahoo Finance',
    description: 'Yahoo Finance 提供免费的股票市场数据',
    doc_url: 'https://finance.yahoo.com'
  }
}

// 允许配置的数据源（按市场）
const ALLOWED_SOURCES: Record<string, string[]> = {
  A_STOCK: ['tushare_pro'],
  US_STOCK: ['alpha_vantage'],
  HK_STOCK: []
}

// 状态
const loading = ref(false)
const testing = ref<string | null>(null)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const activeMarket = ref<MarketType>(MarketType.A_STOCK)
const userConfigs = ref<any[]>([])

// 对话框表单
const formRef = ref<FormInstance>()
const formData = ref({
  market: 'A_STOCK',
  source_id: '',
  api_key: '',
  priority: 1,
  enabled: true
})
const editingConfig = ref<any>(null)

// 表单验证规则
const formRules: FormRules = {
  market: [{ required: true, message: '请选择市场类型', trigger: 'change' }],
  source_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  api_key: [
    { required: true, message: '请输入 API Key', trigger: 'blur' },
    { min: 10, message: 'API Key 长度不能少于 10 个字符', trigger: 'blur' }
  ],
  priority: [{ required: true, message: '请输入优先级', trigger: 'blur' }]
}

// 计算属性
const filteredConfigs = computed(() => {
  return userConfigs.value.filter(c => c.market === activeMarket.value)
})

const aStockCount = computed(() => {
  return userConfigs.value.filter(c => c.market === 'A_STOCK').length
})

const usStockCount = computed(() => {
  return userConfigs.value.filter(c => c.market === 'US_STOCK').length
})

const hkStockCount = computed(() => {
  return userConfigs.value.filter(c => c.market === 'HK_STOCK').length
})

const availableDataSources = computed(() => {
  const sources = ALLOWED_SOURCES[formData.value.market] || []
  return sources.map(id => ({
    id,
    name: DATA_SOURCE_INFO[id]?.name || id
  }))
})

const selectedDataSourceInfo = computed(() => {
  return DATA_SOURCE_INFO[formData.value.source_id] || null
})

// 方法
const getDataSourceDisplayName = (sourceId: string) => {
  return DATA_SOURCE_INFO[sourceId]?.name || sourceId
}

const getDataSourceDescription = (sourceId: string) => {
  return DATA_SOURCE_INFO[sourceId]?.description || ''
}

const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleString('zh-CN')
}

const fetchConfigs = async () => {
  try {
    loading.value = true
    const configs = await userDataSourceApi.getConfigs(activeMarket.value, false)
    userConfigs.value = configs
  } catch (error: any) {
    ElMessage.error(`获取配置失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

const handleMarketChange = () => {
  fetchConfigs()
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingConfig.value = null
  formData.value = {
    market: activeMarket.value,
    source_id: '',
    api_key: '',
    priority: 1,
    enabled: true
  }
  dialogVisible.value = true
}

const handleEdit = (config: any) => {
  dialogMode.value = 'edit'
  editingConfig.value = config
  formData.value = {
    market: config.market,
    source_id: config.source_id,
    api_key: '', // 编辑时不回显 API Key
    priority: config.priority,
    enabled: config.enabled
  }
  dialogVisible.value = true
}

const handleDataSourceChange = () => {
  // 数据源变更时可以做一些处理，比如设置默认优先级等
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (dialogMode.value === 'create') {
      await userDataSourceApi.createConfig(formData.value)
      ElMessage.success('数据源配置创建成功')
    } else {
      await userDataSourceApi.updateConfig(
        editingConfig.value.source_id,
        editingConfig.value.market,
        formData.value
      )
      ElMessage.success('数据源配置更新成功')
    }

    dialogVisible.value = false
    await fetchConfigs()
  } catch (error: any) {
    if (error !== false) { // 表单验证失败时 error 为 false
      ElMessage.error(`操作失败: ${error.message || '未知错误'}`)
    }
  } finally {
    submitting.value = false
  }
}

const handleToggleEnabled = async (config: any) => {
  try {
    await userDataSourceApi.updateConfig(
      config.source_id,
      config.market,
      { enabled: !config.enabled }
    )
    ElMessage.success(config.enabled ? '已禁用' : '已启用')
    await fetchConfigs()
  } catch (error: any) {
    ElMessage.error(`操作失败: ${error.message || '未知错误'}`)
  }
}

const handleDelete = async (config: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据源 "${getDataSourceDisplayName(config.source_id)}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
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

const handleTest = async (config: any) => {
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

// 初始化
onMounted(async () => {
  await fetchConfigs()
})
</script>

<style scoped lang="scss">
.user-data-source-config-view {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
}

.market-tabs {
  margin-bottom: 16px;
}

// 卡片容器
.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

// 数据源卡片
.source-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s ease;

  &:hover {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    border-color: var(--el-color-primary);
  }

  // 卡片头部
  .card-header {
    margin-bottom: 12px;

    .card-title {
      margin: 0 0 8px 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .card-description {
      margin: 0;
      font-size: 13px;
      color: var(--el-text-color-secondary);
      line-height: 1.5;
    }
  }

  // 状态信息
  .card-status {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);

    .status-item {
      display: flex;
      align-items: center;
      font-size: 13px;

      .status-label {
        color: var(--el-text-color-secondary);
        margin-right: 8px;
        min-width: 70px;
      }

      .status-value {
        color: var(--el-text-color-regular);
      }
    }
  }

  // 配置信息
  .card-config {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;

    .config-item {
      display: flex;
      align-items: center;
      font-size: 13px;

      .config-label {
        color: var(--el-text-color-secondary);
        margin-right: 8px;
        min-width: 70px;
      }

      .config-value {
        color: var(--el-text-color-regular);

        &.masked {
          font-family: monospace;
          letter-spacing: 2px;
          color: var(--el-text-color-placeholder);
        }
      }
    }
  }

  // 操作按钮
  .card-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  // 添加卡片
  &.add-card {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    cursor: pointer;
    border: 2px dashed var(--el-border-color);
    background: transparent;

    &:hover {
      border-color: var(--el-color-primary);
      background: var(--el-fill-color-light);
    }

    .add-card-content {
      text-align: center;

      p {
        margin: 12px 0 0 0;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.form-tip {
  margin-top: 4px;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
