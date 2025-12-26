<template>
  <div class="single-analysis-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>单个股票分析</span>
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
            prop="stock_code"
          >
            <el-input
              v-model="form.stock_code"
              placeholder="请输入股票代码，如：600000"
            />
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
              :loading="isAnalyzing"
              @click="handleStartAnalysis"
            >
              开始分析
            </el-button>
            <el-button
              :disabled="!currentTask || currentTask.status !== 'running'"
              @click="handleStopAnalysis"
            >
              停止分析
            </el-button>
          </el-form-item>
        </el-form>

        <el-divider />

        <div
          v-if="currentTask"
          class="task-status"
        >
          <h3>分析进度</h3>

          <el-steps
            :active="currentTask.current_phase"
            finish-status="success"
            align-center
          >
            <el-step
              title="分析师研究"
              description="多角度市场分析"
            />
            <el-step
              title="辩论阶段"
              description="多空观点交锋"
            />
            <el-step
              title="风险评估"
              description="首席风控官分析"
            />
            <el-step
              title="总结生成"
              description="综合分析报告"
            />
          </el-steps>

          <el-progress
            :percentage="currentTask.progress || 0"
            :status="currentTask.status === 'completed' ? 'success' : (currentTask.status === 'failed' ? 'exception' : '')"
          />

          <div
            v-if="currentTask.current_agent"
            class="current-agent"
          >
            当前执行智能体：{{ currentTask.current_agent }}
          </div>
        </div>

        <el-divider />

        <div
          v-if="events.length > 0"
          class="events-log"
        >
          <h3>执行日志</h3>
          <el-timeline>
            <el-timeline-item
              v-for="(event, index) in events"
              :key="index"
              :timestamp="formatTimestamp(event.timestamp)"
              placement="top"
              :type="getEventTypeColor(event.event_type)"
            >
              <div class="event-content">
                <div class="event-type">
                  {{ formatEventType(event.event_type) }}
                </div>
                <div
                  v-if="event.data"
                  class="event-data"
                >
                  <pre>{{ formatEventData(event.data) }}</pre>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>

        <el-divider />

        <div
          v-if="currentTask && currentTask.reports"
          class="reports-section"
        >
          <h3>分析报告</h3>
          <div
            v-for="(report, slug) in currentTask.reports"
            :key="slug"
            class="report-card"
          >
            <el-card>
              <template #header>
                <span>{{ getAgentName(slug) }}</span>
              </template>
              <div class="report-content">
                {{ report }}
              </div>
            </el-card>
          </div>
        </div>

        <el-divider />

        <div
          v-if="currentTask && currentTask.status === 'completed'"
          class="final-result"
        >
          <h3>最终分析结果</h3>
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="推荐操作">
              <el-tag :type="getRecommendationType(currentTask.final_recommendation)">
                {{ currentTask.final_recommendation }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item
              v-if="currentTask.buy_price"
              label="买入价格"
            >
              {{ currentTask.buy_price }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="currentTask.sell_price"
              label="卖出价格"
            >
              {{ currentTask.sell_price }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="currentTask.token_usage"
              label="Token 使用"
            >
              <span
                v-for="(count, model) in currentTask.token_usage"
                :key="model"
              >
                {{ model }}: {{ count }}
              </span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '@modules/trading_agents/api'
import type { AnalysisTask, TaskEvent } from '@modules/trading_agents/types'

const formRef = ref()
const isAnalyzing = ref(false)
const currentTask = ref<AnalysisTask | null>(null)
const events = ref<TaskEvent[]>([])
let websocket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_DELAY_BASE = 1000

const form = reactive({
  stock_code: '',
  trade_date: new Date().toISOString().split('T')[0],
  phase2_enabled: true,
  phase3_enabled: true,
  phase4_enabled: true,
})

const rules = {
  stock_code: [{ required: true, message: '请输入股票代码', trigger: 'blur' }],
  trade_date: [{ required: true, message: '请选择交易日期', trigger: 'change' }],
}

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

async function handleStartAnalysis() {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    isAnalyzing.value = true
    events.value = []

    const result = await taskApi.createTask({
      stock_code: form.stock_code,
      trade_date: form.trade_date,
      phase2_enabled: form.phase2_enabled,
      phase3_enabled: form.phase3_enabled,
      phase4_enabled: form.phase4_enabled,
    })

    const taskId = result.task_id
    connectWebSocket(taskId)

    ElMessage.success('分析任务已创建')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '创建任务失败')
    isAnalyzing.value = false
  }
}

async function handleStopAnalysis() {
  if (!currentTask.value) return

  try {
    await taskApi.cancelTask(currentTask.value.id)
    ElMessage.success('任务已停止')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '停止任务失败')
  }
}

function connectWebSocket(taskId: string) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/trading-agents/ws/${taskId}`

  websocket = new WebSocket(wsUrl)

  websocket.onopen = () => {
    console.log('WebSocket connected')
    reconnectAttempts = 0
  }

  websocket.onmessage = (event) => {
    try {
      const taskEvent: TaskEvent = JSON.parse(event.data)
      handleTaskEvent(taskEvent)
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
    if (currentTask.value) {
      connectWebSocket(currentTask.value.id)
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

function handleTaskEvent(event: TaskEvent) {
  events.value.push(event)

  switch (event.event_type) {
    case 'task_started':
      currentTask.value = {
        id: event.task_id,
        user_id: '',
        stock_code: form.stock_code,
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
        batch_id: null,
      }
      isAnalyzing.value = false
      break

    case 'phase_started':
      if (currentTask.value) {
        currentTask.value.current_phase = event.data.phase as number
      }
      break

    case 'agent_started':
      if (currentTask.value) {
        currentTask.value.current_agent = event.data.agent_name as string
      }
      break

    case 'agent_completed':
      if (currentTask.value && event.data.token_usage) {
        Object.assign(currentTask.value.token_usage, event.data.token_usage)
      }
      break

    case 'task_completed':
      if (currentTask.value) {
        currentTask.value.status = 'completed'
        currentTask.value.current_phase = 4
        currentTask.value.progress = 100
        currentTask.value.current_agent = null
        currentTask.value.completed_at = new Date().toISOString()
        if (event.data.final_recommendation) {
          currentTask.value.final_recommendation = event.data.final_recommendation
        }
        if (event.data.buy_price) {
          currentTask.value.buy_price = event.data.buy_price
        }
        if (event.data.sell_price) {
          currentTask.value.sell_price = event.data.sell_price
        }
        if (event.data.total_token_usage) {
          currentTask.value.token_usage = event.data.total_token_usage
        }
      }
      disconnectWebSocket()
      break

    case 'task_failed':
      if (currentTask.value) {
        currentTask.value.status = 'failed'
        currentTask.value.error_message = event.data.error_message as string
      }
      disconnectWebSocket()
      break

    case 'progress_update':
      if (currentTask.value) {
        currentTask.value.progress = event.data.progress as number
      }
      break

    case 'report_generated':
      if (currentTask.value) {
        const slug = event.data.agent_slug as string
        if (!currentTask.value.reports) {
          currentTask.value.reports = {}
        }
        currentTask.value.reports[slug] = event.data.content as string
      }
      break
  }
}

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

function formatEventType(eventType: string): string {
  const typeMap: Record<string, string> = {
    task_created: '任务创建',
    task_started: '任务开始',
    task_completed: '任务完成',
    task_failed: '任务失败',
    task_cancelled: '任务取消',
    task_stopped: '任务停止',
    phase_started: '阶段开始',
    phase_completed: '阶段完成',
    agent_started: '智能体开始',
    agent_completed: '智能体完成',
    agent_failed: '智能体失败',
    tool_called: '工具调用',
    tool_result: '工具结果',
    tool_disabled: '工具禁用',
    report_generated: '报告生成',
    report_stream_chunk: '报告流式片段',
    progress_update: '进度更新',
  }
  return typeMap[eventType] || eventType
}

function formatEventData(data: Record<string, unknown>): string {
  return JSON.stringify(data, null, 2)
}

function getEventTypeColor(eventType: string): string {
  const colorMap: Record<string, string> = {
    task_created: 'primary',
    task_started: 'primary',
    task_completed: 'success',
    task_failed: 'danger',
    phase_started: 'primary',
    phase_completed: 'success',
    agent_started: 'primary',
    agent_completed: 'success',
    agent_failed: 'danger',
    tool_called: 'info',
    tool_result: 'info',
    tool_disabled: 'warning',
    report_generated: 'success',
    progress_update: 'info',
  }
  return colorMap[eventType] || 'primary'
}

function getAgentName(slug: string): string {
  return AGENT_NAMES[slug] || slug
}

function getRecommendationType(recommendation: string | null): string {
  const typeMap: Record<string, string> = {
    '买入': 'success',
    '卖出': 'danger',
    '持有': 'warning',
  }
  return typeMap[recommendation || ''] || 'info'
}
</script>

<style scoped>
.single-analysis-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
}

.task-status {
  margin: 20px 0;
}

.current-agent {
  margin-top: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: center;
  font-weight: bold;
  color: #409eff;
}

.events-log {
  margin: 20px 0;
}

.event-content {
  padding: 10px;
}

.event-type {
  font-weight: bold;
  margin-bottom: 5px;
}

.event-data {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  margin-top: 5px;
  overflow-x: auto;
}

.event-data pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.reports-section {
  margin: 20px 0;
}

.report-card {
  margin-bottom: 20px;
}

.report-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
}

.final-result {
  margin: 20px 0;
}

.final-result h3 {
  margin-bottom: 15px;
}
</style>
