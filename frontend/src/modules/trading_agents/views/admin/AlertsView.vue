<template>
  <div class="alerts-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>系统告警事件</h2>
      <div class="header-actions">
        <el-button
          :icon="Refresh"
          @click="fetchAlerts"
        >
          刷新
        </el-button>
        <el-button
          v-if="hasUnresolved"
          type="primary"
          @click="resolveAllVisible"
        >
          全部标记已解决
        </el-button>
      </div>
    </div>

    <!-- 统计信息 -->
    <el-row
      :gutter="16"
      class="stats-row"
    >
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="总告警数"
            :value="stats.total"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="未解决"
            :value="stats.unresolved"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="严重告警"
            :value="stats.critical"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic
            title="今日告警"
            :value="stats.today"
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
        <el-form-item label="级别">
          <el-select
            v-model="filters.severity"
            placeholder="全部"
            clearable
            style="width: 140px"
            @change="fetchAlerts"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="信息"
              value="info"
            />
            <el-option
              label="警告"
              value="warning"
            />
            <el-option
              label="错误"
              value="error"
            />
            <el-option
              label="严重"
              value="critical"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="filters.event_type"
            placeholder="全部"
            clearable
            style="width: 160px"
            @change="fetchAlerts"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="工具循环"
              value="tool_loop"
            />
            <el-option
              label="配额耗尽"
              value="quota_exhausted"
            />
            <el-option
              label="MCP 不可用"
              value="mcp_unavailable"
            />
            <el-option
              label="任务超时"
              value="task_timeout"
            />
            <el-option
              label="批量失败"
              value="batch_failure"
            />
            <el-option
              label="Token 异常"
              value="token_anomaly"
            />
            <el-option
              label="模型错误"
              value="model_error"
            />
            <el-option
              label="任务失败"
              value="task_failed"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.resolved"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="fetchAlerts"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="未解决"
              value="false"
            />
            <el-option
              label="已解决"
              value="true"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="fetchAlerts"
          >
            查询
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card
      shadow="never"
      class="alerts-card"
    >
      <template #header>
        <div class="card-header">
          <span>告警列表 ({{ alerts.length }})</span>
          <el-radio-group
            v-model="viewMode"
            size="small"
          >
            <el-radio-button label="list">
              列表
            </el-radio-button>
            <el-radio-button label="timeline">
              时间线
            </el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'">
        <el-table
          v-loading="loading"
          :data="alerts"
          stripe
          @row-click="handleRowClick"
        >
          <el-table-column
            prop="id"
            label="ID"
            width="200"
            show-overflow-tooltip
          />
          <el-table-column
            label="级别"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                :type="getSeverityType(row.severity)"
                size="small"
              >
                {{ getSeverityLabel(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="event_type"
            label="类型"
            width="150"
          >
            <template #default="{ row }">
              {{ getEventTypeLabel(row.event_type) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="title"
            label="标题"
            show-overflow-tooltip
          />
          <el-table-column
            prop="description"
            label="描述"
            show-overflow-tooltip
          />
          <el-table-column
            label="用户"
            width="150"
          >
            <template #default="{ row }">
              {{ row.user_id || '-' }}
            </template>
          </el-table-column>
          <el-table-column
            label="任务"
            width="150"
          >
            <template #default="{ row }">
              {{ row.task_id || '-' }}
            </template>
          </el-table-column>
          <el-table-column
            prop="timestamp"
            label="时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.resolved ? 'info' : 'warning'"
                size="small"
              >
                {{ row.resolved ? '已解决' : '未解决' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="120"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                v-if="!row.resolved"
                link
                type="primary"
                size="small"
                @click.stop="handleResolve(row.id)"
              >
                标记解决
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 时间线视图 -->
      <el-timeline v-else-if="viewMode === 'timeline'">
        <el-timeline-item
          v-for="alert in alerts"
          :key="alert.id"
          :timestamp="alert.timestamp"
          placement="top"
          :type="getSeverityType(alert.severity)"
          :icon="getSeverityIcon(alert.severity)"
        >
          <template #dot>
            <span />
          </template>
          <el-card>
            <div class="alert-header">
              <div class="alert-title">
                {{ alert.title }}
              </div>
              <div class="alert-meta">
                <el-tag
                  :type="getSeverityType(alert.severity)"
                  size="small"
                >
                  {{ getSeverityLabel(alert.severity) }}
                </el-tag>
                <span class="alert-time">{{ formatDateTime(alert.timestamp) }}</span>
              </div>
            </div>
            <div class="alert-body">
              <p class="alert-desc">
                {{ alert.description }}
              </p>
              
              <div
                v-if="alert.metadata && Object.keys(alert.metadata).length > 0"
                class="alert-metadata"
              >
                <h4>详细信息：</h4>
                <pre>{{ JSON.stringify(alert.metadata, null, 2) }}</pre>
              </div>
              
              <div class="alert-footer">
                <div class="alert-info">
                  <span v-if="alert.user_id">用户: {{ alert.user_id }}</span>
                  <span v-if="alert.task_id">任务: {{ alert.task_id }}</span>
                </div>
                <el-button
                  v-if="!alert.resolved"
                  type="primary"
                  size="small"
                  @click="handleResolve(alert.id)"
                >
                  标记解决
                </el-button>
              </div>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <!-- 空状态 -->
      <el-empty
        v-if="!loading && alerts.length === 0"
        description="暂无告警"
        :image-size="120"
      />
    </el-card>

    <!-- 告警详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="告警详情"
      width="600px"
    >
      <div v-if="currentAlert">
        <el-descriptions
          :column="1"
          border
        >
          <el-descriptions-item label="ID">
            {{ currentAlert.id }}
          </el-descriptions-item>
          <el-descriptions-item label="级别">
            <el-tag :type="getSeverityType(currentAlert.severity)">
              {{ getSeverityLabel(currentAlert.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            {{ getEventTypeLabel(currentAlert.event_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="标题">
            {{ currentAlert.title }}
          </el-descriptions-item>
          <el-descriptions-item label="描述">
            {{ currentAlert.description }}
          </el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ currentAlert.user_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="任务">
            {{ currentAlert.task_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="时间">
            {{ formatDateTime(currentAlert.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ currentAlert.resolved ? '已解决' : '未解决' }}
          </el-descriptions-item>
          <el-descriptions-item label="解决时间">
            {{ currentAlert.resolved_at ? formatDateTime(currentAlert.resolved_at) : '-' }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div
          v-if="currentAlert.metadata"
          class="metadata-section"
        >
          <h4>元数据：</h4>
          <pre>{{ JSON.stringify(currentAlert.metadata, null, 2) }}</pre>
        </div>
        
        <div
          v-if="!currentAlert.resolved"
          class="dialog-footer"
        >
          <el-button
            type="primary"
            @click="handleResolve(currentAlert.id)"
          >
            标记解决
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, SuccessFilled, WarningFilled, InfoFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { httpGet, httpPost } from '@/core/api/http'

// 状态
const loading = ref(false)
const alerts = ref<any[]>([])
const detailVisible = ref(false)
const currentAlert = ref<any>(null)
const viewMode = ref<'list' | 'timeline'>('list')

// 筛选
const filters = reactive({
  severity: '',
  event_type: '',
  resolved: '',
})

// 统计
const stats = ref({
  total: 0,
  unresolved: 0,
  critical: 0,
  today: 0,
})

// 分页
const pagination = reactive({
  page: 1,
  size: 50,
  total: 0,
})

// 是否有未解决的告警
const hasUnresolved = computed(() => {
  return stats.value.unresolved > 0
})

// 获取告警列表
async function fetchAlerts() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(pagination.size),
      offset: String((pagination.page - 1) * pagination.size),
    })

    if (filters.severity) {
      params.append('severity', filters.severity)
    }
    if (filters.event_type) {
      params.append('event_type', filters.event_type)
    }
    if (filters.resolved !== '') {
      params.append('resolved', filters.resolved)
    }

    const response = await httpGet<any>(`/api/trading-agents/alerts?${params}`)
    alerts.value = response.alerts || []
    pagination.total = response.total || 0

    // 更新统计
    await fetchStats()
  } catch (error) {
    console.error('获取告警列表失败:', error)
    ElMessage.error('获取告警列表失败')
  } finally {
    loading.value = false
  }
}

// 获取统计
async function fetchStats() {
  try {
    const response = await httpGet<any>('/api/trading-agents/alerts/stats')
    stats.value = response || {
      total: 0,
      unresolved: 0,
      critical: 0,
      today: 0,
    }
  } catch (error) {
    console.error('获取告警统计失败:', error)
  }
}

// 行点击
function handleRowClick(row: any) {
  currentAlert.value = row
  detailVisible.value = true
}

// 标记解决
async function handleResolve(alertId: string) {
  try {
    await httpPost(`/api/trading-agents/alerts/${alertId}/resolve`)
    ElMessage.success('已标记为已解决')
    
    // 刷新列表
    await fetchAlerts()
    
    // 如果详情页打开，关闭
    if (detailVisible.value) {
      detailVisible.value = false
    }
  } catch (error) {
    console.error('标记解决失败:', error)
    ElMessage.error('标记解决失败')
  }
}

// 标记所有可见为已解决
async function resolveAllVisible() {
  const unresolved = alerts.value.filter(a => !a.resolved)
  if (unresolved.length === 0) {
    ElMessage.info('没有未解决的告警')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要标记这 ${unresolved.length} 个告警为已解决吗？`,
      '确认标记',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 批量标记
    for (const alert of unresolved) {
      await httpPost(`/api/trading-agents/alerts/${alert.id}/resolve`)
    }

    ElMessage.success(`已标记 ${unresolved.length} 个告警为已解决`)
    await fetchAlerts()
  } catch (err) {
    // 用户取消
  }
}

// 分页变化
function handlePageChange(page: number) {
  pagination.page = page
  fetchAlerts()
}

function handleSizeChange(size: number) {
  pagination.size = size
  pagination.page = 1
  fetchAlerts()
}

// 获取级别类型
function getSeverityType(severity: string): 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    'info': 'info',
    'warning': 'warning',
    'error': 'danger',
    'critical': 'danger',
  }
  return typeMap[severity] || 'info'
}

// 获取级别标签
function getSeverityLabel(severity: string): string {
  const labelMap: Record<string, string> = {
    'info': '信息',
    'warning': '警告',
    'error': '错误',
    'critical': '严重',
  }
  return labelMap[severity] || '未知'
}

// 获取级别图标
function getSeverityIcon(severity: string) {
  const iconMap: Record<string, any> = {
    'info': InfoFilled,
    'warning': WarningFilled,
    'error': CircleCloseFilled,
    'critical': CircleCloseFilled,
  }
  return iconMap[severity] || InfoFilled
}

// 获取事件类型标签
function getEventTypeLabel(eventType: string): string {
  const labelMap: Record<string, string> = {
    'tool_loop': '工具循环检测',
    'quota_exhausted': '配额耗尽',
    'mcp_unavailable': 'MCP 不可用',
    'task_timeout': '任务超时',
    'batch_failure': '批量任务失败',
    'token_anomaly': 'Token 异常消耗',
    'model_error': '模型调用错误',
    'task_failed': '任务失败',
  }
  return labelMap[eventType] || '未知'
}

// 格式化日期时间
function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 组件挂载
onMounted(() => {
  fetchAlerts()
})
</script>

<style scoped>
.alerts-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-row {
  margin-bottom: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.alerts-card {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.alert-title {
  font-weight: 600;
  font-size: 16px;
}

.alert-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-time {
  font-size: 12px;
  color: #909399;
}

.alert-body {
  padding: 10px 0;
}

.alert-desc {
  margin: 0 0 10px 0;
  line-height: 1.6;
}

.alert-metadata {
  margin: 10px 0;
}

.alert-metadata h4 {
  margin: 0 0 5px 0;
  font-size: 14px;
}

.alert-metadata pre {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.alert-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.alert-info {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #606266;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>

