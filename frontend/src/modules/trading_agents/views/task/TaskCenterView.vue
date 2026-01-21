<template>
  <div class="task-center-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>任务中心</h2>
      <el-button
        :icon="RefreshRight"
        :loading="store.tasksLoading"
        @click="handleRefresh"
      >
        刷新
      </el-button>
    </div>

    <!-- 统计条 -->
    <div class="stats-bar">
      <div class="stats-label">
        统计概览：
      </div>
      <div class="stats-items">
        <div
          v-for="item in statsItems"
          :key="item.key"
          :class="['stats-item', item.type]"
        >
          <span class="stats-label-text">{{ item.label }}</span>
          <span class="stats-count">{{ statusCounts[item.key] || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- 筛选卡片：状态标签 + 搜索区域 -->
    <el-card
      v-if="shouldShowSearch"
      shadow="never"
      class="filter-card"
    >
      <!-- 状态标签行 -->
      <div class="filter-tabs">
        <el-radio-group
          v-model="activeStatusTab"
          size="default"
          @change="handleStatusChange"
        >
          <el-radio-button
            v-for="tab in statusTabs"
            :key="tab.key"
            :value="tab.key"
          >
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 分割线 -->
      <el-divider style="margin: 16px 0;" />

      <!-- 搜索区域 -->
      <el-form
        :model="searchParams"
        inline
        class="search-form-inline"
      >
        <div class="search-conditions">
          <el-form-item
            v-if="shouldShowStockSearch"
            label="股票"
          >
            <el-input
              v-model="searchParams.stockCode"
              placeholder="代码/名称"
              clearable
              style="width: 180px"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            />
          </el-form-item>

          <el-form-item
            v-if="shouldShowRecommendationFilter"
            label="建议"
          >
            <el-select
              v-model="searchParams.recommendation"
              placeholder="全部"
              clearable
              style="width: 120px"
              @change="handleSearch"
            >
              <el-option
                label="全部"
                value=""
              />
              <el-option
                label="买入"
                value="buy"
              />
              <el-option
                label="卖出"
                value="sell"
              />
              <el-option
                label="持有"
                value="hold"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="shouldShowRecommendationFilter"
            label="风险"
          >
            <el-select
              v-model="searchParams.riskLevel"
              placeholder="全部"
              clearable
              style="width: 110px"
              @change="handleSearch"
            >
              <el-option
                label="全部"
                value=""
              />
              <el-option
                label="高"
                value="high"
              />
              <el-option
                label="中"
                value="medium"
              />
              <el-option
                label="低"
                value="low"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="时间">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              format="YYYY年MM月DD日"
              style="width: 320px"
              @change="handleSearch"
            />
          </el-form-item>
        </div>

        <!-- 按钮区域（靠右） -->
        <div class="search-actions">
          <el-button
            type="primary"
            @click="handleSearch"
          >
            查询
          </el-button>
          <el-button @click="handleReset">
            重置
          </el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 失败/取消状态：仅显示标签，不显示搜索 -->
    <el-card
      v-if="!shouldShowSearch"
      shadow="never"
      class="filter-card"
    >
      <div class="filter-tabs">
        <el-radio-group
          v-model="activeStatusTab"
          size="default"
          @change="handleStatusChange"
        >
          <el-radio-button
            v-for="tab in statusTabs"
            :key="tab.key"
            :value="tab.key"
          >
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <!-- 批量操作栏（仅失败/取消状态显示） -->
    <div
      v-if="shouldShowBatchActions"
      class="batch-actions-bar"
    >
      <el-button
        type="danger"
        :icon="Delete"
        @click="handleClearAll"
      >
        批量清空{{ currentStatusLabel }}
      </el-button>
      <el-button
        type="danger"
        :icon="Delete"
        :disabled="selectedTaskIds.length === 0"
        @click="handleBatchDelete"
      >
        批量删除选中 ({{ selectedTaskIds.length }})
      </el-button>
    </div>

    <!-- 任务列表表格 -->
    <el-card
      shadow="never"
      class="table-card"
    >
      <el-table
        v-loading="store.tasksLoading"
        :data="store.tasks"
        stripe
        @row-click="handleRowClick"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          v-if="shouldEnableBatchSelection"
          type="selection"
          width="55"
        />
        <el-table-column
          prop="stock_code"
          label="股票代码"
          width="110"
        />
        <el-table-column
          prop="stock_name"
          label="股票名称"
          width="130"
        />
        <el-table-column
          v-if="shouldShowRecommendationColumn"
          label="买卖建议"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.final_recommendation"
              :type="getRecommendationType(row.final_recommendation)"
              size="small"
            >
              {{ getRecommendationLabel(row.final_recommendation) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="shouldShowRiskLevelColumn"
          label="风险等级"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="getRiskLevelType(row.risk_level)"
              size="small"
            >
              {{ getRiskLevelLabel(row.risk_level) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="shouldShowErrorColumn"
          label="错误信息"
          min-width="200"
        >
          <template #default="{ row }">
            <el-tooltip
              v-if="row.error_message"
              :content="row.error_message"
              placement="top"
            >
              <span class="error-message">{{ row.error_message }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="进度"
          width="150"
        >
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="getProgressStatus(row.status)"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column
          label="创建时间"
          width="170"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="180"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click.stop="goToDetail(row.id)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status === TaskStatusEnum.RUNNING"
              link
              type="warning"
              @click.stop="handleCancel(row.id)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.status === TaskStatusEnum.FAILED"
              link
              type="primary"
              @click.stop="handleRetry(row.id)"
            >
              重试
            </el-button>
            <el-button
              link
              type="danger"
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="store.tasksTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Delete } from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../../store'
import { taskApi } from '../../api'
import {
  TaskStatusEnum,
  RecommendationEnum,
  RiskLevelEnum,
  type AnalysisTask,
} from '../../types'

const router = useRouter()
const store = useTradingAgentsStore()

// 状态标签配置
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '进行中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '已失败' },
  { key: 'cancelled', label: '已取消' },
]

// 统计条配置
const statsItems = [
  { key: 'all', label: '全部', type: 'primary' },
  { key: 'running', label: '进行中', type: 'warning' },
  { key: 'completed', label: '完成', type: 'success' },
  { key: 'failed', label: '失败', type: 'orange' },
  { key: 'cancelled', label: '取消', type: 'gray' },
]

// 当前激活的状态标签
const activeStatusTab = ref<string>('all')

// 状态数量统计
const statusCounts = ref<Record<string, number>>({})

// 搜索参数
const searchParams = reactive({
  stockCode: '',
  recommendation: '',
  riskLevel: '',
})

// 日期范围
const dateRange = ref<[string, string] | null>(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 选中的任务 ID（用于批量删除）
const selectedTaskIds = ref<string[]>([])

// 计算属性：当前状态标签的中文标签
const currentStatusLabel = computed(() => {
  const tab = statusTabs.find(t => t.key === activeStatusTab.value)
  return tab ? tab.label : ''
})

// 计算属性：是否显示搜索框（全部、进行中、已完成显示）
const shouldShowSearch = computed(() =>
  ['all', 'running', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示股票搜索框
const shouldShowStockSearch = computed(() =>
  ['all', 'running', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示买卖建议和风险等级筛选（仅全部/已完成）
const shouldShowRecommendationFilter = computed(() =>
  ['all', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示批量操作栏（仅失败/取消状态）
const shouldShowBatchActions = computed(() =>
  ['failed', 'cancelled'].includes(activeStatusTab.value)
)

// 计算属性：是否启用批量选择（失败/取消状态，或其他状态有选中任务时）
const shouldEnableBatchSelection = computed(() =>
  ['failed', 'cancelled', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示买卖建议列
const shouldShowRecommendationColumn = computed(() =>
  ['all', 'running', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示风险等级列
const shouldShowRiskLevelColumn = computed(() =>
  ['all', 'running', 'completed'].includes(activeStatusTab.value)
)

// 计算属性：是否显示错误信息列（失败/取消/终止状态）
const shouldShowErrorColumn = computed(() =>
  ['failed', 'cancelled', 'stopped'].includes(activeStatusTab.value)
)

/**
 * 状态标签切换
 */
async function handleStatusChange() {
  currentPage.value = 1
  selectedTaskIds.value = []
  await loadTasks()
}

/**
 * 搜索
 */
async function handleSearch() {
  currentPage.value = 1
  await loadTasks()
}

/**
 * 重置筛选
 */
function handleReset() {
  searchParams.stockCode = ''
  searchParams.recommendation = ''
  searchParams.riskLevel = ''
  dateRange.value = null
  handleSearch()
}

/**
 * 页码变化
 */
function handlePageChange(page: number) {
  currentPage.value = page
  loadTasks()
}

/**
 * 每页数量变化
 */
function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadTasks()
}

/**
 * 刷新
 */
async function handleRefresh() {
  await Promise.all([
    loadStatusCounts(),
    loadTasks(),
  ])
  ElMessage.success('刷新成功')
}

/**
 * 表格行点击
 */
function handleRowClick(row: AnalysisTask) {
  goToDetail(row.id)
}

/**
 * 表格选择变化
 */
function handleSelectionChange(selection: AnalysisTask[]) {
  selectedTaskIds.value = selection.map(task => task.id)
}

/**
 * 加载状态数量统计
 */
async function loadStatusCounts() {
  try {
    const result = await taskApi.getStatusCounts()
    statusCounts.value = result
  } catch (error) {
    console.error('加载状态统计失败:', error)
  }
}

/**
 * 加载任务列表
 */
async function loadTasks() {
  try {
    // 根据当前状态标签确定要查询的状态
    let statusFilter: string | undefined
    switch (activeStatusTab.value) {
      case 'running':
        // 进行中 = 待执行 + 分析中
        statusFilter = undefined // 由前端聚合，不传 status
        break
      case 'cancelled':
        // 已取消 = 已取消 + 已停止
        statusFilter = undefined
        break
      default:
        statusFilter = activeStatusTab.value === 'all' ? undefined : activeStatusTab.value
    }

    await store.fetchTasks({
      status: statusFilter,
      stock_code: searchParams.stockCode || undefined,
      recommendation: searchParams.recommendation || undefined,
      risk_level: searchParams.riskLevel || undefined,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1],
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
  } catch (error) {
    console.error('加载任务列表失败:', error)
    ElMessage.error('加载任务列表失败')
  }
}

/**
 * 跳转到详情页面
 */
function goToDetail(taskId: string) {
  router.push({
    name: 'AnalysisDetail',
    params: { taskId },
  })
}

/**
 * 取消任务
 */
async function handleCancel(taskId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await store.cancelTask(taskId)
    ElMessage.success('任务已取消')
    await Promise.all([
      loadStatusCounts(),
      loadTasks(),
    ])
  } catch (err) {
    // 用户取消
  }
}

/**
 * 重试任务
 */
async function handleRetry(taskId: string) {
  try {
    await store.retryTask(taskId)
    ElMessage.success('任务已重新提交')
    await Promise.all([
      loadStatusCounts(),
      loadTasks(),
    ])
  } catch (error) {
    console.error('重试任务失败:', error)
    ElMessage.error('重试任务失败')
  }
}

/**
 * 删除单个任务
 */
async function handleDelete(task: AnalysisTask) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个任务吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await taskApi.deleteTask(task.id)
    ElMessage.success('任务已删除')
    await Promise.all([
      loadStatusCounts(),
      loadTasks(),
    ])
  } catch (err: any) {
    // 区分用户取消和 API 错误
    if (err === 'cancel' || err?.message === 'cancel') {
      // 用户取消操作，不显示错误
      return
    }
    // API 调用失败，显示错误消息
    const errorMsg = err?.response?.data?.detail || err?.message || '删除任务失败'
    ElMessage.error(errorMsg)
  }
}

/**
 * 批量清空当前状态的所有任务
 */
async function handleClearAll() {
  try {
    // 根据当前标签确定要清空的状态
    let statusList: string[] = []
    let statusLabel = ''

    if (activeStatusTab.value === 'failed') {
      statusList = ['failed']
      statusLabel = '失败'
    } else if (activeStatusTab.value === 'cancelled') {
      statusList = ['cancelled', 'stopped']
      statusLabel = '取消'
    } else {
      return
    }

    // 先查询当前状态的任务数量
    const count = statusCounts.value[activeStatusTab.value] || 0

    if (count === 0) {
      ElMessage.info('没有需要清空的任务')
      return
    }

    await ElMessageBox.confirm(
      `确定要清空所有${statusLabel}任务吗？共 ${count} 个任务，此操作不可恢复。`,
      '批量清空确认',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true,
      }
    )

    await taskApi.clearTasksByStatus({
      statuses: statusList.join(','),
      delete_reports: false,
    })

    ElMessage.success(`已清空 ${count} 个${statusLabel}任务`)
    await Promise.all([
      loadStatusCounts(),
      loadTasks(),
    ])
  } catch (err) {
    // 用户取消
  }
}

/**
 * 批量删除选中的任务
 */
async function handleBatchDelete() {
  try {
    if (selectedTaskIds.value.length === 0) {
      ElMessage.warning('请先选择要删除的任务')
      return
    }

    // 获取选中任务的详情
    const selectedTasks = store.tasks.filter(task =>
      selectedTaskIds.value.includes(task.id)
    )

    const taskSummary = selectedTasks
      .map(t => `• ${t.stock_code} ${t.stock_name || ''} (${getStatusLabel(t.status)})`)
      .join('\n')

    await ElMessageBox.confirm(
      `即将删除以下 ${selectedTaskIds.value.length} 个任务：\n${taskSummary}\n\n此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true,
      }
    )

    const result = await taskApi.batchDeleteTasks({
      task_ids: selectedTaskIds.value,
      delete_reports: false,
    })

    if (result.failed_count > 0) {
      ElMessage.warning(
        `成功删除 ${result.success_count} 个任务，失败 ${result.failed_count} 个`
      )
    } else {
      ElMessage.success(`成功删除 ${result.success_count} 个任务`)
    }

    selectedTaskIds.value = []
    await Promise.all([
      loadStatusCounts(),
      loadTasks(),
    ])
  } catch (err) {
    // 用户取消
  }
}

/**
 * 获取状态类型
 */
function getStatusType(status: TaskStatusEnum): string {
  const typeMap: Record<string, string> = {
    [TaskStatusEnum.PENDING]: 'info',
    [TaskStatusEnum.RUNNING]: 'warning',
    [TaskStatusEnum.COMPLETED]: 'success',
    [TaskStatusEnum.FAILED]: 'danger',
    [TaskStatusEnum.CANCELLED]: 'info',
    [TaskStatusEnum.STOPPED]: 'info',
    [TaskStatusEnum.EXPIRED]: 'danger',
  }
  return typeMap[status] || 'info'
}

/**
 * 获取状态标签
 */
function getStatusLabel(status: TaskStatusEnum): string {
  const labelMap: Record<string, string> = {
    [TaskStatusEnum.PENDING]: '待执行',
    [TaskStatusEnum.RUNNING]: '分析中',
    [TaskStatusEnum.COMPLETED]: '已完成',
    [TaskStatusEnum.FAILED]: '失败',
    [TaskStatusEnum.CANCELLED]: '已取消',
    [TaskStatusEnum.STOPPED]: '已停止',
    [TaskStatusEnum.EXPIRED]: '已过期',
  }
  return labelMap[status] || '未知'
}

/**
 * 获取推荐结果类型
 */
function getRecommendationType(recommendation: string): string {
  const typeMap: Record<string, string> = {
    'buy': 'success',
    'sell': 'danger',
    'hold': 'info',
  }
  return typeMap[recommendation] || 'info'
}

/**
 * 获取推荐结果标签
 */
function getRecommendationLabel(recommendation: string): string {
  const labelMap: Record<string, string> = {
    'buy': '买入',
    'sell': '卖出',
    'hold': '持有',
  }
  return labelMap[recommendation] || '-'
}

/**
 * 获取风险等级类型
 */
function getRiskLevelType(riskLevel: string): string {
  const typeMap: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'success',
  }
  return typeMap[riskLevel] || 'info'
}

/**
 * 获取风险等级标签
 */
function getRiskLevelLabel(riskLevel: string): string {
  const labelMap: Record<string, string> = {
    'high': '高',
    'medium': '中',
    'low': '低',
  }
  return labelMap[riskLevel] || '-'
}

/**
 * 获取进度条状态
 */
function getProgressStatus(status: TaskStatusEnum): '' | 'success' | 'exception' | undefined {
  if (status === TaskStatusEnum.COMPLETED) return 'success'
  if (status === TaskStatusEnum.FAILED || status === TaskStatusEnum.CANCELLED) return 'exception'
  return undefined
}

/**
 * 格式化日期时间
 */
function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 初始化
onMounted(() => {
  loadStatusCounts()
  loadTasks()
})
</script>

<style scoped>
.task-center-view {
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
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* 统计条 */
.stats-bar {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  margin-bottom: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.stats-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-right: 16px;
  white-space: nowrap;
}

.stats-items {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.stats-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.stats-item.primary {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.stats-item.warning {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.stats-item.success {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.stats-item.orange {
  background: #FDF6EC;
  color: #E6A23C;
}

.stats-item.gray {
  background: #F4F4F5;
  color: #909399;
}

.stats-label-text {
  opacity: 0.8;
}

.stats-count {
  font-size: 16px;
  font-weight: 600;
}

/* 筛选标签栏 */
.filter-tabs {
  display: flex;
  justify-content: flex-start;
}

/* 筛选卡片 */
.filter-card {
  margin-bottom: 20px;
}

/* 搜索表单单行布局 */
.search-form-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

/* 搜索条件区域（靠左） */
.search-conditions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-conditions :deep(.el-form-item) {
  margin-bottom: 0;
}

/* 按钮区域（靠右） */
.search-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.search-actions :deep(.el-form-item) {
  margin-bottom: 0;
}

/* 批量操作栏 */
.batch-actions-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff5f5;
  border: 1px solid #ffcccc;
  border-radius: 4px;
}

/* 表格卡片 */
.table-card {
  margin-bottom: 20px;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}

.error-message {
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-color-danger);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
