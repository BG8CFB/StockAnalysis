<template>
  <div class="task-center-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>任务中心</h2>
    </div>

    <!-- 统计卡片 -->
    <el-row
      :gutter="20"
      class="stats-row"
    >
      <el-col :span="6">
        <el-card
          shadow="never"
          class="stat-card"
        >
          <div class="stat-content">
            <div class="stat-value">
              {{ summary.total_reports || 0 }}
            </div>
            <div class="stat-label">
              已完成任务
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card
          shadow="never"
          class="stat-card stat-buy"
        >
          <div class="stat-content">
            <div class="stat-value">
              {{ summary.buy_count || 0 }}
            </div>
            <div class="stat-label">
              买入建议
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card
          shadow="never"
          class="stat-card stat-sell"
        >
          <div class="stat-content">
            <div class="stat-value">
              {{ summary.sell_count || 0 }}
            </div>
            <div class="stat-label">
              卖出建议
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card
          shadow="never"
          class="stat-card stat-hold"
        >
          <div class="stat-content">
            <div class="stat-value">
              {{ summary.hold_count || 0 }}
            </div>
            <div class="stat-label">
              持有建议
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选器 -->
    <el-card
      shadow="never"
      class="filter-card"
    >
      <el-form
        :model="filters"
        inline
      >
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="待执行"
              :value="TaskStatusEnum.PENDING"
            />
            <el-option
              label="分析中"
              :value="TaskStatusEnum.RUNNING"
            />
            <el-option
              label="已完成"
              :value="TaskStatusEnum.COMPLETED"
            />
            <el-option
              label="失败"
              :value="TaskStatusEnum.FAILED"
            />
            <el-option
              label="已取消"
              :value="TaskStatusEnum.CANCELLED"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="股票代码">
          <el-input
            v-model="filters.stock_code"
            placeholder="输入股票代码"
            clearable
            style="width: 200px"
            @keyup.enter="handleFilterChange"
          />
        </el-form-item>

        <el-form-item label="推荐结果">
          <el-select
            v-model="filters.recommendation"
            placeholder="全部"
            clearable
            style="width: 150px"
            @change="handleFilterChange"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="买入"
              :value="RecommendationEnum.BUY"
            />
            <el-option
              label="卖出"
              :value="RecommendationEnum.SELL"
            />
            <el-option
              label="持有"
              :value="RecommendationEnum.HOLD"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="风险等级">
          <el-select
            v-model="filters.risk_level"
            placeholder="全部"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="高"
              :value="RiskLevelEnum.HIGH"
            />
            <el-option
              label="中"
              :value="RiskLevelEnum.MEDIUM"
            />
            <el-option
              label="低"
              :value="RiskLevelEnum.LOW"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleFilterChange"
          >
            查询
          </el-button>
          <el-button @click="handleReset">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card
      shadow="never"
      class="table-card"
    >
      <el-table
        v-loading="store.tasksLoading"
        :data="store.tasks"
        stripe
        @row-click="handleRowClick"
      >
        <el-table-column
          prop="stock_code"
          label="股票代码"
          width="100"
        />
        <el-table-column
          prop="trade_date"
          label="交易日期"
          width="120"
        />
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
          label="推荐结果"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.final_recommendation"
              :type="getRecommendationType(row.final_recommendation)"
              size="small"
            >
              {{ row.final_recommendation }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="风险等级"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="getRiskLevelType(row.risk_level)"
              size="small"
            >
              {{ row.risk_level }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="价格信息"
          width="180"
        >
          <template #default="{ row }">
            <div class="price-info">
              <span
                v-if="row.buy_price"
                class="price-tag"
              >
                买入: ¥{{ row.buy_price.toFixed(2) }}
              </span>
              <span
                v-if="row.sell_price"
                class="price-tag"
              >
                卖出: ¥{{ row.sell_price.toFixed(2) }}
              </span>
              <span v-if="!row.buy_price && !row.sell_price">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="进度"
          width="150"
        >
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="getProgressStatus(row.status)"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column
          label="创建时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
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
              @click.stop="goToDetail(row.id)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status === TaskStatusEnum.RUNNING"
              link
              type="danger"
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
              @click.stop="handleDelete(row.id)"
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTradingAgentsStore } from '../../store'
import {
  TaskStatusEnum,
  RecommendationEnum,
  RiskLevelEnum,
  type AnalysisTask,
  type ReportSummary,
} from '../../types'

const router = useRouter()
const store = useTradingAgentsStore()

// 筛选条件
const filters = reactive({
  status: '',
  stock_code: '',
  recommendation: '',
  risk_level: '',
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 报告统计
const summary = ref<ReportSummary>({
  total_reports: 0,
  buy_count: 0,
  sell_count: 0,
  hold_count: 0,
  avg_buy_price: null,
  avg_sell_price: null,
  total_token_usage: 0,
  recommendation_distribution: {
    buy: 0,
    sell: 0,
    hold: 0,
  },
})

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
function getRecommendationType(recommendation: RecommendationEnum): string {
  const typeMap: Record<string, string> = {
    [RecommendationEnum.BUY]: 'success',
    [RecommendationEnum.SELL]: 'danger',
    [RecommendationEnum.HOLD]: 'info',
  }
  return typeMap[recommendation] || 'info'
}

/**
 * 获取风险等级类型
 */
function getRiskLevelType(riskLevel: RiskLevelEnum): string {
  const typeMap: Record<string, string> = {
    [RiskLevelEnum.HIGH]: 'danger',
    [RiskLevelEnum.MEDIUM]: 'warning',
    [RiskLevelEnum.LOW]: 'success',
  }
  return typeMap[riskLevel] || 'info'
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
  return date.toLocaleString('zh-CN')
}

/**
 * 筛选变化
 */
function handleFilterChange() {
  currentPage.value = 1
  loadTasks()
}

/**
 * 重置筛选
 */
function handleReset() {
  filters.status = ''
  filters.stock_code = ''
  filters.recommendation = ''
  filters.risk_level = ''
  currentPage.value = 1
  loadTasks()
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
 * 行点击
 */
function handleRowClick(row: AnalysisTask) {
  goToDetail(row.id)
}

/**
 * 加载任务列表
 */
async function loadTasks() {
  try {
    await store.fetchTasks({
      status: filters.status || undefined,
      stock_code: filters.stock_code || undefined,
      recommendation: filters.recommendation || undefined,
      risk_level: filters.risk_level || undefined,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
  } catch (error) {
    console.error('加载任务列表失败:', error)
    ElMessage.error('加载任务列表失败')
  }
}

/**
 * 加载统计摘要
 */
async function loadSummary() {
  try {
    const result = await store.fetchReportSummary(30)
    summary.value = {
      total_reports: result.total_reports || 0,
      buy_count: result.recommendation_distribution?.buy || 0,
      sell_count: result.recommendation_distribution?.sell || 0,
      hold_count: result.recommendation_distribution?.hold || 0,
      avg_buy_price: result.avg_buy_price,
      avg_sell_price: result.avg_sell_price,
      total_token_usage: result.total_token_usage,
      recommendation_distribution: result.recommendation_distribution || {
        buy: 0,
        sell: 0,
        hold: 0,
      },
    }
  } catch (error) {
    console.error('加载统计摘要失败:', error)
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
    loadTasks()
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
    loadTasks()
  } catch (error) {
    console.error('重试任务失败:', error)
    ElMessage.error('重试任务失败')
  }
}

/**
 * 删除任务
 */
async function handleDelete(taskId: string) {
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

    await store.deleteTask(taskId)
    ElMessage.success('任务已删除')
    loadTasks()
  } catch (err) {
    // 用户取消
  }
}

// 初始化
onMounted(() => {
  loadTasks()
  loadSummary()
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

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  border: 1px solid var(--el-border-color);
}

.stat-content {
  padding: 8px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
}

.stat-buy .stat-value {
  color: var(--el-color-success);
}

.stat-sell .stat-value {
  color: var(--el-color-danger);
}

.stat-hold .stat-value {
  color: var(--el-color-info);
}

.filter-card,
.table-card {
  margin-bottom: 20px;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}

.price-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-tag {
  font-size: 13px;
}

.price-tag:first-child {
  color: var(--el-color-success);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>

