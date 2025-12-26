<template>
  <div class="batch-analysis-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>批量股票分析</span>
        </div>
      </template>

      <div class="content">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
        >
          <el-form-item
            label="股票代码"
            prop="stock_codes"
          >
            <el-input
              v-model="form.stock_codes_text"
              type="textarea"
              :rows="10"
              placeholder="请输入股票代码，每行一个，如：&#10;600000&#10;600001&#10;600002&#10;..."
            />
            <div class="stock-count">
              已输入 {{ stockCodes.length }} 只股票
            </div>
          </el-form-item>

          <el-form-item label="上传文件">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              accept=".txt,.csv"
              :show-file-list="false"
            >
              <el-button type="primary">
                选择文件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .txt 或 .csv 格式文件，每行一个股票代码
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <el-form-item
            label="交易日期"
            prop="trade_date"
          >
            <el-date-picker
              v-model="form.trade_date"
              type="date"
              placeholder="选择交易日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item label="分析选项">
            <el-checkbox v-model="form.phase2_enabled">
              启用辩论阶段
            </el-checkbox>
            <el-checkbox v-model="form.phase3_enabled">
              启用风险分析
            </el-checkbox>
            <el-checkbox v-model="form.phase4_enabled">
              启用总结生成
            </el-checkbox>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="isSubmitting"
              @click="handleStartBatch"
            >
              开始批量分析
            </el-button>
            <el-button @click="handleClear">
              清空
            </el-button>
          </el-form-item>
        </el-form>

        <el-divider />

        <div
          v-if="batchTask"
          class="batch-progress"
        >
          <h3>批量任务进度</h3>

          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="总任务数">
              {{ batchTask.total_count }}
            </el-descriptions-item>
            <el-descriptions-item label="已完成">
              {{ batchTask.completed_count }}
            </el-descriptions-item>
            <el-descriptions-item label="失败">
              <el-tag type="danger">
                {{ batchTask.failed_count }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(batchTask.status)">
                {{ getStatusText(batchTask.status) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-progress
            :percentage="batchProgress"
            :status="batchTask.status === 'completed' ? 'success' : (batchTask.status === 'failed' ? 'exception' : '')"
          />

          <div class="batch-actions">
            <el-button
              v-if="batchTask.status === 'running'"
              type="danger"
              @click="handleStopBatch"
            >
              取消批量任务
            </el-button>
          </div>
        </div>

        <el-divider />

        <div
          v-if="tasks.length > 0"
          class="tasks-list"
        >
          <h3>任务列表</h3>

          <el-table
            :data="tasks"
            style="width: 100%"
          >
            <el-table-column
              prop="stock_code"
              label="股票代码"
              width="120"
            />
            <el-table-column
              prop="status"
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="current_phase"
              label="当前阶段"
              width="100"
            />
            <el-table-column
              prop="progress"
              label="进度"
              width="120"
            >
              <template #default="{ row }">
                <el-progress
                  :percentage="row.progress || 0"
                  :status="row.status === 'completed' ? 'success' : (row.status === 'failed' ? 'exception' : '')"
                />
              </template>
            </el-table-column>
            <el-table-column
              prop="current_agent"
              label="当前智能体"
              width="150"
            />
            <el-table-column
              prop="final_recommendation"
              label="推荐操作"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  v-if="row.final_recommendation"
                  :type="getRecommendationType(row.final_recommendation)"
                >
                  {{ row.final_recommendation }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="150"
            >
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'running'"
                  type="danger"
                  size="small"
                  @click="handleStopTask(row)"
                >
                  停止
                </el-button>
                <el-button
                  v-if="row.status === 'completed' || row.status === 'failed'"
                  type="primary"
                  size="small"
                  @click="handleViewReport(row)"
                >
                  查看报告
                </el-button>
                <el-button
                  v-if="row.status === 'failed'"
                  type="warning"
                  size="small"
                  @click="handleRetryTask(row)"
                >
                  重试
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-divider />

        <div
          v-if="currentReport"
          class="report-detail"
        >
          <h3>分析报告 - {{ currentReport.stock_code }}</h3>
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="推荐操作">
              <el-tag :type="getRecommendationType(currentReport.final_recommendation)">
                {{ currentReport.final_recommendation }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item
              v-if="currentReport.buy_price"
              label="买入价格"
            >
              {{ currentReport.buy_price }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="currentReport.sell_price"
              label="卖出价格"
            >
              {{ currentReport.sell_price }}
            </el-descriptions-item>
            <el-descriptions-item label="Token 使用">
              <span
                v-for="(count, model) in currentReport.token_usage"
                :key="model"
              >
                {{ model }}: {{ count }}
              </span>
            </el-descriptions-item>
          </el-descriptions>

          <div
            v-if="currentReport.reports"
            class="reports-section"
          >
            <h4>各智能体报告</h4>
            <el-tabs v-model="activeReportTab">
              <el-tab-pane
                v-for="(report, slug) in currentReport.reports"
                :key="slug"
                :label="getAgentName(slug)"
                :name="slug"
              >
                <div class="report-content">
                  {{ report }}
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>

          <div class="report-actions">
            <el-button @click="currentReport = null">
              关闭
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '@modules/trading_agents/api'
import type { AnalysisTask, BatchTask } from '@modules/trading_agents/types'

const formRef = ref()
const uploadRef = ref()
const isSubmitting = ref(false)
const batchTask = ref<BatchTask | null>(null)
const tasks = ref<AnalysisTask[]>([])
const currentReport = ref<AnalysisTask | null>(null)
const activeReportTab = ref('')
let websocket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_DELAY_BASE = 1000

const form = reactive({
  stock_codes_text: '',
  trade_date: new Date().toISOString().split('T')[0],
  phase2_enabled: true,
  phase3_enabled: true,
  phase4_enabled: true,
})

const rules = {
  stock_codes_text: [{ required: true, message: '请输入股票代码', trigger: 'blur' }],
  trade_date: [{ required: true, message: '请选择交易日期', trigger: 'change' }],
}

const stockCodes = computed(() => {
  return form.stock_codes_text
    .split('\n')
    .map(code => code.trim())
    .filter(code => code.length > 0)
})

const batchProgress = computed(() => {
  if (!batchTask.value || batchTask.value.total_count === 0) return 0
  return Math.round((batchTask.value.completed_count / batchTask.value.total_count) * 100)
})

const AGENT_NAMES: Record<string, string> = {
  market_technical: '市场技术分析师',
  market_fundamental: '市场基本面分析师',
  news_sentiment: '新闻情绪分析师',
  bull_debater: '看涨研究员',
  bear_debater: '看跌研究员',
  risk_assessor: '首席风控官',
  final_summarizer: '总结智能体',
}

onUnmounted(() => {
  disconnectWebSocket()
})

function handleFileChange(file: any) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    form.stock_codes_text = text
    ElMessage.success('文件上传成功')
  }
  reader.readAsText(file.raw)
}

async function handleStartBatch() {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    if (stockCodes.value.length === 0) {
      ElMessage.error('请输入至少一个股票代码')
      return
    }

    isSubmitting.value = true
    tasks.value = []
    batchTask.value = null

    const result = await taskApi.createBatchTask({
      stock_codes: stockCodes.value,
      trade_date: form.trade_date,
      phase2_enabled: form.phase2_enabled,
      phase3_enabled: form.phase3_enabled,
      phase4_enabled: form.phase4_enabled,
    })

    const batchId = result.batch_id
    batchTask.value = {
      id: batchId,
      user_id: '',
      stock_codes: stockCodes.value,
      total_count: stockCodes.value.length,
      completed_count: 0,
      failed_count: 0,
      status: 'pending',
      created_at: new Date().toISOString(),
      completed_at: null,
    }

    connectWebSocket(batchId)

    ElMessage.success('批量分析任务已创建')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '创建批量任务失败')
  } finally {
    isSubmitting.value = false
  }
}

function handleClear() {
  form.stock_codes_text = ''
  tasks.value = []
  batchTask.value = null
  currentReport.value = null
}

async function handleStopBatch() {
  if (!batchTask.value) return

  try {
    await taskApi.cancelTask(batchTask.value.id)
    ElMessage.success('批量任务已取消')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '取消任务失败')
  }
}

async function handleStopTask(task: AnalysisTask) {
  try {
    await taskApi.cancelTask(task.id)
    ElMessage.success('任务已停止')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '停止任务失败')
  }
}

async function handleRetryTask(task: AnalysisTask) {
  try {
    await taskApi.retryTask(task.id)
    ElMessage.success('任务已重新提交')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '重试任务失败')
  }
}

function handleViewReport(task: AnalysisTask) {
  currentReport.value = task
  if (task.reports && Object.keys(task.reports).length > 0) {
    activeReportTab.value = Object.keys(task.reports)[0]
  }
}

function connectWebSocket(batchId: string) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/trading-agents/batch-ws/${batchId}`

  websocket = new WebSocket(wsUrl)

  websocket.onopen = () => {
    console.log('WebSocket connected')
    reconnectAttempts = 0
  }

  websocket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      handleBatchMessage(message)
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  websocket.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  websocket.onclose = () => {
    console.log('WebSocket closed')
    scheduleReconnect()
  }
}

function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.log('Max reconnect attempts reached')
    return
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
  }

  const delay = RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttempts)
  console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`)

  reconnectTimer = setTimeout(() => {
    if (batchTask.value) {
      connectWebSocket(batchTask.value.id)
    }
    reconnectAttempts++
  }, delay)
}

function disconnectWebSocket() {
  if (websocket) {
    websocket.close()
    websocket = null
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

function handleBatchMessage(message: any) {
  switch (message.type) {
    case 'task_started':
      handleTaskStarted(message.data)
      break
    case 'task_progress':
      handleTaskProgress(message.data)
      break
    case 'task_completed':
      handleTaskCompleted(message.data)
      break
    case 'task_failed':
      handleTaskFailed(message.data)
      break
    case 'batch_completed':
      handleBatchCompleted(message.data)
      break
  }
}

function handleTaskStarted(data: any) {
  const existingTask = tasks.value.find(t => t.id === data.task_id)
  if (!existingTask) {
    tasks.value.push({
      id: data.task_id,
      user_id: '',
      stock_code: data.stock_code,
      trade_date: form.trade_date,
      status: 'running',
      current_phase: 1,
      current_agent: null,
      progress: 0,
      reports: {},
      final_recommendation: null,
      buy_price: null,
      sell_price: null,
      token_usage: {},
      error_message: null,
      error_details: null,
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: null,
      expired_at: null,
      batch_id: batchTask.value?.id || null,
    })
  }
}

function handleTaskProgress(data: any) {
  const task = tasks.value.find(t => t.id === data.task_id)
  if (task) {
    task.progress = data.progress
    task.current_phase = data.current_phase
    task.current_agent = data.current_agent
  }
}

function handleTaskCompleted(data: any) {
  const task = tasks.value.find(t => t.id === data.task_id)
  if (task) {
    task.status = 'completed'
    task.progress = 100
    task.current_phase = 4
    task.current_agent = null
    task.completed_at = new Date().toISOString()
    if (data.final_recommendation) {
      task.final_recommendation = data.final_recommendation
    }
    if (data.buy_price) {
      task.buy_price = data.buy_price
    }
    if (data.sell_price) {
      task.sell_price = data.sell_price
    }
    if (data.token_usage) {
      task.token_usage = data.token_usage
    }
    if (data.reports) {
      task.reports = data.reports
    }
  }

  if (batchTask.value) {
    batchTask.value.completed_count++
  }
}

function handleTaskFailed(data: any) {
  const task = tasks.value.find(t => t.id === data.task_id)
  if (task) {
    task.status = 'failed'
    task.error_message = data.error_message
  }

  if (batchTask.value) {
    batchTask.value.failed_count++
  }
}

function handleBatchCompleted(_data: any) {
  if (batchTask.value) {
    batchTask.value.status = 'completed'
    batchTask.value.completed_at = new Date().toISOString()
  }
  disconnectWebSocket()
  ElMessage.success('批量分析完成')
}

function getStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning',
    stopped: 'warning',
    expired: 'danger',
  }
  return typeMap[status] || 'info'
}

function getStatusText(status: string): string {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    stopped: '已停止',
    expired: '已过期',
  }
  return textMap[status] || status
}

function getRecommendationType(recommendation: string | null): string {
  const typeMap: Record<string, string> = {
    '买入': 'success',
    '卖出': 'danger',
    '持有': 'warning',
  }
  return typeMap[recommendation || ''] || 'info'
}

function getAgentName(slug: string): string {
  return AGENT_NAMES[slug] || slug
}
</script>

<style scoped>
.batch-analysis-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content {
  max-width: 1400px;
  margin: 0 auto;
}

.stock-count {
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
}

.batch-progress {
  margin: 20px 0;
}

.batch-actions {
  margin-top: 15px;
  text-align: center;
}

.tasks-list {
  margin: 20px 0;
}

.report-detail {
  margin: 20px 0;
}

.report-detail h3 {
  margin-bottom: 15px;
}

.reports-section {
  margin-top: 20px;
}

.reports-section h4 {
  margin-bottom: 10px;
}

.report-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.report-actions {
  margin-top: 20px;
  text-align: center;
}
</style>
