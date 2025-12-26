<template>
  <div class="task-center-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>任务中心</h2>
      <el-button
        type="primary"
        :icon="Refresh"
        @click="fetchTasks"
      >
        刷新
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="总任务" :value="stats.total" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="运行中" :value="stats.running" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="已完成" :value="stats.completed" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="失败" :value="stats.failed" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="Token 消耗" :value="stats.total_tokens" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="已过期" :value="stats.expired" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选和排序 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable @change="fetchTasks">
            <el-option label="全部" value="" />
            <el-option label="待执行" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="filters.sortBy" placeholder="创建时间" @change="fetchTasks">
            <el-option label="创建时间" value="created_at" />
            <el-option label="开始时间" value="started_at" />
            <el-option label="完成时间" value="completed_at" />
            <el-option label="Token 消耗" value="tokens" />
          </el-select>
          <el-select v-model="filters.sortOrder" @change="fetchTasks">
            <el-option label="降序" value="-1" />
            <el-option label="升序" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="filters.search"
            placeholder="股票代码"
            clearable
            @change="fetchTasks"
            style="width: 200px"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="tasks"
        stripe
        @row-click="handleRowClick"
      >
        <el-table-column prop="stock_code" label="股票代码" width="120" />
        <el-table-column prop="trade_date" label="交易日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="final_recommendation" label="推荐" width="80">
          <template #default="{ row }">
            <span v-if="row.final_recommendation">{{ getRecommendationLabel(row.final_recommendation) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="token_usage" label="Token" width="100">
          <template #default="{ row }">
            <span v-if="row.token_usage">{{ formatNumber(row.token_usage.total_tokens || 0) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_message" class="error-text">{{ row.error_message }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click.stop="handleViewDetail(row)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              link
              type="warning"
              @click.stop="handleCancel(row)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.status === 'failed' || row.status === 'expired'"
              link
              type="primary"
              @click.stop="handleRetry(row)"
            >
              重试
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
          @size-change="fetchTasks"
          @current-change="fetchTasks"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="`任务详情 - ${selectedTask?.stock_code || ''}`"
      width="800px"
    >
      <div v-if="selectedTask" class="task-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ selectedTask.id }}</el-descriptions-item>
          <el-descriptions-item label="股票代码">{{ selectedTask.stock_code }}</el-descriptions-item>
          <el-descriptions-item label="交易日期">{{ selectedTask.trade_date }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedTask.status)" size="small">
              {{ getStatusLabel(selectedTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="推荐">
            {{ selectedTask.final_recommendation ? getRecommendationLabel(selectedTask.final_recommendation) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(selectedTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ selectedTask.started_at ? formatDateTime(selectedTask.started_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ selectedTask.completed_at ? formatDateTime(selectedTask.completed_at) : '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- Token 使用 -->
        <div v-if="selectedTask.token_usage" class="token-usage">
          <h4>Token 使用量</h4>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-statistic title="Prompt Tokens" :value="selectedTask.token_usage.prompt_tokens || 0" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="Completion Tokens" :value="selectedTask.token_usage.completion_tokens || 0" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="Total Tokens" :value="selectedTask.token_usage.total_tokens || 0" />
            </el-col>
          </el-row>
        </div>

        <!-- 错误信息 -->
        <div v-if="selectedTask.error_message" class="error-section">
          <h4>错误信息</h4>
          <el-alert :title="selectedTask.error_message" type="error" :closable="false" />
        </div>

        <!-- 价格建议 -->
        <div v-if="selectedTask.buy_price || selectedTask.sell_price" class="price-section">
          <h4>价格建议</h4>
          <p>买入价: <strong>{{ selectedTask.buy_price || '-' }}</strong></p>
          <p>卖出价: <strong>{{ selectedTask.sell_price || '-' }}</strong></p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { httpGet, httpPut, httpDelete } from '@/core/api/http'

// 状态
const loading = ref(false)
const tasks = ref<any[]>([])
const selectedTask = ref<any>(null)
const showDetailDialog = ref(false)

// 统计
const stats = ref({
  total: 0,
  running: 0,
  completed: 0,
  failed: 0,
  expired: 0,
  total_tokens: 0,
})

// 筛选
const filters = reactive({
  status: '',
  sortBy: 'created_at',
  sortOrder: '-1',
  search: '',
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0,
})

// 获取任务列表
async function fetchTasks() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(pagination.size),
      offset: String((pagination.page - 1) * pagination.size),
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
    })

    if (filters.status) {
      params.append('status', filters.status)
    }
    if (filters.search) {
      params.append('search', filters.search)
    }

    const response = await httpGet<any>(`/api/trading-agents/tasks?${params}`)
    tasks.value = response.tasks
    pagination.total = response.total

    // 计算统计
    updateStats()
  } finally {
    loading.value = false
  }
}

// 更新统计
function updateStats() {
  stats.value = {
    total: tasks.value.length,
    running: tasks.value.filter(t => t.status === 'running').length,
    completed: tasks.value.filter(t => t.status === 'completed').length,
    failed: tasks.value.filter(t => t.status === 'failed').length,
    expired: tasks.value.filter(t => t.status === 'expired').length,
    total_tokens: tasks.value.reduce((sum, t) => sum + (t.token_usage?.total_tokens || 0), 0),
  }
}

// 查看详情
function handleViewDetail(task: any) {
  selectedTask.value = task
  showDetailDialog.value = true
}

// 取消任务
async function handleCancel(task: any) {
  try {
    await ElMessageBox.confirm(`确定要取消任务 "${task.stock_code}" 吗？`, '确认取消', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await httpPut(`/api/trading-agents/tasks/${task.id}/cancel`, {})
    ElMessage.success('任务已取消')
    fetchTasks()
  } catch {
    // 用户取消
  }
}

// 重试任务
async function handleRetry(task: any) {
  try {
    await ElMessageBox.confirm(`确定要重试任务 "${task.stock_code}" 吗？`, '确认重试', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    })
    // 创建新任务（使用相同参数）
    await httpPost('/api/trading-agents/tasks', {
      stock_code: task.stock_code,
      trade_date: task.trade_date,
    })
    ElMessage.success('任务已创建')
    fetchTasks()
  } catch {
    // 用户取消
  }
}

// 行点击
function handleRowClick(row: any) {
  handleViewDetail(row)
}

// 获取状态类型
function getStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
    expired: 'danger',
  }
  return typeMap[status] || 'info'
}

// 获取状态标签
function getStatusLabel(status: string): string {
  const labelMap: Record<string, string> = {
    pending: '待执行',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    expired: '已过期',
  }
  return labelMap[status] || status
}

// 获取推荐标签
function getRecommendationLabel(rec: string): string {
  const labelMap: Record<string, string> = {
    BUY: '买入',
    SELL: '卖出',
    HOLD: '持有',
  }
  return labelMap[rec] || rec
}

// 格式化日期时间
function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 格式化数字
function formatNumber(num: number): string {
  return num.toLocaleString()
}

// 初始化
onMounted(fetchTasks)
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

.task-detail h4 {
  margin-top: 20px;
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: 600;
}

.token-usage,
.price-section {
  margin-top: 20px;
}

.error-section {
  margin-top: 20px;
}

.error-text {
  color: #f56c6c;
}

.el-table {
  cursor: pointer;
}

.el-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
