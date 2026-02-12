<template>
  <div class="all-tasks-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>所有任务管理</h2>
      <el-button
        type="primary"
        :icon="Refresh"
        @click="fetchData"
      >
        刷新
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
            title="总任务数"
            :value="stats.total"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="今日任务"
            :value="stats.today"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="运行中"
            :value="stats.running"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="公共模型运行中"
            :value="stats.public_model_running"
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
              label="待执行"
              value="pending"
            />
            <el-option
              label="运行中"
              value="running"
            />
            <el-option
              label="已完成"
              value="completed"
            />
            <el-option
              label="失败"
              value="failed"
            />
            <el-option
              label="已取消"
              value="cancelled"
            />
            <el-option
              label="已过期"
              value="expired"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用户ID">
          <el-input
            v-model="filters.user_id"
            placeholder="用户ID"
            clearable
            style="width: 200px"
            @change="fetchData"
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
      >
        <el-table-column
          prop="id"
          label="任务ID"
          width="240"
          show-overflow-tooltip
        />
        <el-table-column
          prop="user_id"
          label="用户ID"
          width="240"
        />
        <el-table-column
          prop="stock_code"
          label="股票代码"
          width="120"
        />
        <el-table-column
          prop="trade_date"
          label="交易日期"
          width="120"
        />
        <el-table-column
          prop="status"
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
          prop="final_recommendation"
          label="推荐"
          width="80"
        >
          <template #default="{ row }">
            <span v-if="row.final_recommendation">{{ getRecommendationLabel(row.final_recommendation) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          label="创建时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="started_at"
          label="开始时间"
          width="180"
        >
          <template #default="{ row }">
            {{ row.started_at ? formatDateTime(row.started_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="completed_at"
          label="完成时间"
          width="180"
        >
          <template #default="{ row }">
            {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="token_usage"
          label="Token"
          width="100"
        >
          <template #default="{ row }">
            <span v-if="row.token_usage">{{ row.token_usage.total_tokens || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="100"
          fixed="right"
        >
          <template #default="{ row }">
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

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete } from '@element-plus/icons-vue'
import { httpGet, httpDelete } from '@/core/api/http'

// 状态
const loading = ref(false)
const tasks = ref<any[]>([])

// 统计
const stats = ref({
  total: 0,
  today: 0,
  running: 0,
  public_model_running: 0,
})

// 筛选
const filters = reactive({
  status: '',
  user_id: '',
})

// 分页
const pagination = reactive({
  page: 1,
  size: 50,
  total: 0,
})

// 获取数据
async function fetchData() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(pagination.size),
      offset: String((pagination.page - 1) * pagination.size),
    })

    if (filters.status) {
      params.append('status_filter', filters.status)
    }
    if (filters.user_id) {
      params.append('user_filter', filters.user_id)
    }

    const response = await httpGet<any>(`/api/admin/trading-agents/tasks?${params}`)
    tasks.value = response.tasks

    // 更新统计
    stats.value = {
      total: response.total,
      today: 0, // 从 stats 接口获取
      running: response.public_model_running,
      public_model_running: response.public_model_running,
    }

    pagination.total = response.total
  } finally {
    loading.value = false
  }

  // 获取详细统计
  try {
    const statsData = await httpGet<any>('/api/admin/trading-agents/tasks/stats')
    stats.value.today = statsData.today
    stats.value.running = statsData.running
  } catch (e) {
    // 忽略统计错误
  }
}

// 删除任务
async function handleDelete(task: any) {
  try {
    await ElMessageBox.confirm(`确定要删除任务 "${task.id}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await httpDelete(`/api/admin/trading-agents/tasks/${task.id}`)
    ElMessage.success('删除成功')
    fetchData()
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

// 获取状态类型
function getStatusType(status: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
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

// 初始化
onMounted(fetchData)
</script>

<style scoped>
.all-tasks-view {
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
</style>
