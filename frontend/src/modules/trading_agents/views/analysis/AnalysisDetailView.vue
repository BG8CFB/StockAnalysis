<template>
  <div class="analysis-detail-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-button
          :icon="ArrowLeft"
          circle
          @click="goBack"
        />
        <div>
          <h2>{{ task?.stock_code || '股票分析' }}</h2>
          <p class="subtitle">
            {{ task?.trade_date || '' }}
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          v-if="task"
          :type="getStatusType(task.status)"
          size="large"
        >
          {{ getStatusLabel(task.status) }}
        </el-tag>
        <el-button
          v-if="canStop"
          type="danger"
          :icon="VideoPause"
          @click="handleStop"
        >
          停止分析
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <el-skeleton
        :rows="5"
        animated
      />
    </div>

    <!-- 错误状态 -->
    <el-empty
      v-else-if="error"
      description="加载失败"
      :image-size="120"
    >
      <el-button
        type="primary"
        @click="loadTask"
      >
        重试
      </el-button>
    </el-empty>

    <!-- 分析内容 -->
    <div
      v-else-if="task && progressState"
      class="analysis-content"
    >
      <!-- 进度概览 -->
      <el-card
        shadow="never"
        class="overview-card"
      >
        <div class="overview-grid">
          <div class="overview-item">
            <div class="item-label">
              当前阶段
            </div>
            <div class="item-value">
              {{ currentPhaseInfo?.name || '-' }}
            </div>
          </div>
          <div class="overview-item">
            <div class="item-label">
              分析进度
            </div>
            <div class="item-value">
              <el-progress
                :percentage="progressState.progress"
                :status="progressStatus"
                :stroke-width="8"
              />
            </div>
          </div>
          <div class="overview-item">
            <div class="item-label">
              已耗时
            </div>
            <div class="item-value">
              {{ formatDuration(elapsedSeconds) }}
            </div>
          </div>
          <div class="overview-item">
            <div class="item-label">
              智能体
            </div>
            <div class="item-value">
              {{ completedAgentsCount }}/{{ totalAgentsCount }}
            </div>
          </div>
        </div>
      </el-card>

      <!-- 主要内容区域 -->
      <el-row :gutter="20">
        <!-- 左侧：进度和报告 -->
        <el-col :span="16">
          <!-- 阶段进度 -->
          <el-card
            shadow="never"
            class="phase-card"
          >
            <template #header>
              <span>分析阶段</span>
            </template>

            <el-steps
              :active="currentPhaseIndex"
              align-center
            >
              <el-step
                v-for="phase in PHASES"
                :key="phase.id"
                :title="phase.name"
                :description="phase.description"
              />
            </el-steps>
          </el-card>

          <!-- 当前运行的智能体 -->
          <el-card
            v-if="runningAgents.length > 0"
            shadow="never"
            class="agents-card"
          >
            <template #header>
              <span>运行中的智能体</span>
            </template>

            <div class="running-agents">
              <AgentStatusCard
                v-for="agent in runningAgents"
                :key="agent.slug"
                :agent="agent"
                :show-thinking="true"
                @show-thinking="handleShowThinking"
              />
            </div>
          </el-card>

          <!-- 已完成的智能体 -->
          <el-card
            v-if="completedAgents.length > 0"
            shadow="never"
            class="agents-card"
          >
            <template #header>
              <span>已完成的智能体 ({{ completedAgents.length }})</span>
            </template>

            <div class="completed-agents">
              <AgentStatusCard
                v-for="agent in completedAgents"
                :key="agent.slug"
                :agent="agent"
                :show-thinking="true"
                @show-thinking="handleShowThinking"
              />
            </div>
          </el-card>

          <!-- 已生成的报告 -->
          <el-card
            v-if="generatedReports.length > 0"
            shadow="never"
            class="reports-card"
          >
            <template #header>
              <span>分析报告 ({{ generatedReports.length }})</span>
            </template>

            <div class="reports-list">
              <ReportCard
                v-for="report in generatedReports"
                :key="report.agent"
                :agent-name="report.name"
                :report="report.report"
              />
            </div>
          </el-card>

          <!-- 最终报告 -->
          <el-card
            v-if="showFinalReport"
            shadow="never"
            class="final-report-card"
          >
            <StreamingReport
              :content="task.final_report || undefined"
              :recommendation="task.final_recommendation"
              :buy-price="task.buy_price"
              :sell-price="task.sell_price"
              :total-tokens="task.token_usage?.total_tokens || 0"
              :estimated-cost="estimatedCost.value"
              :is-complete="task.status === TaskStatusEnum.COMPLETED"
              :is-streaming="false"
            />
          </el-card>
        </el-col>

        <!-- 右侧：工具调用和状态 -->
        <el-col :span="8">
          <!-- 工具调用记录 -->
          <el-card
            shadow="never"
            class="tools-card"
          >
            <template #header>
              <span>工具调用</span>
              <el-badge
                :value="progress.recentToolCalls.value.length"
                :max="99"
              />
            </template>

            <ToolCallLog :tool-calls="progress.recentToolCalls.value" />
          </el-card>

          <!-- Token 使用 -->
          <el-card
            v-if="tokenStats.value.totalTokens > 0"
            shadow="never"
            class="token-card"
          >
            <template #header>
              <span>Token 使用</span>
            </template>

            <div class="token-stats">
              <div class="stat-row">
                <span class="stat-label">输入:</span>
                <span class="stat-value">{{ formatTokenCount(tokenStats.value.promptTokens) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">输出:</span>
                <span class="stat-value">{{ formatTokenCount(tokenStats.value.completionTokens) }}</span>
              </div>
              <el-divider />
              <div class="stat-row stat-total">
                <span class="stat-label">总计:</span>
                <span class="stat-value">{{ formatTokenCount(tokenStats.value.totalTokens) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">估算成本:</span>
                <span class="stat-value">¥{{ estimatedCost.value.toFixed(2) }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 智能体思考过程对话框 -->
    <AgentThinkingDialog
      v-model:visible="thinkingDialogVisible"
      :agent-name="selectedAgentName"
      :thinking-content="selectedAgentThinking"
      :loading="thinkingLoading"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, VideoPause } from '@element-plus/icons-vue'
import { useWebSocket, WebSocketStatus } from '../../composables/useWebSocket'
import { useAnalysisProgress, PHASES } from '../../composables/useAnalysisProgress'
import { useTokenUsage } from '../../composables/useTokenUsage'
import { taskApi } from '../../api'
import { TaskStatusEnum, type AnalysisTask } from '../../types'
import type { AgentStatus } from '../../composables/useAnalysisProgress'
import AgentStatusCard from '../../components/analysis/AgentStatusCard.vue'
import ToolCallLog from '../../components/analysis/ToolCallLog.vue'
import ReportCard from '../../components/analysis/ReportCard.vue'
import StreamingReport from '../../components/analysis/StreamingReport.vue'
import AgentThinkingDialog from '../../components/analysis/AgentThinkingDialog.vue'

const route = useRoute()
const router = useRouter()

// 任务 ID
const taskId = computed(() => route.params.taskId as string)

// 任务信息
const task = ref<AnalysisTask | null>(null)
const loading = ref(true)
const error = ref(false)

// 分析进度 - 初始化为空，在任务加载后更新
const progress = useAnalysisProgress()
const {
  state: progressStateRaw,
  currentPhaseInfo,
  completedAgentsCount,
  totalAgentsCount,
  runningAgents,
  completedAgents,
  generatedReports,
  elapsedSeconds,
  handleEvent: handleProgressEvent
} = progress

// Token 使用 - 初始化为空，在任务加载后更新
const tokenUsage = useTokenUsage()

// 思考过程对话框状态
const thinkingDialogVisible = ref(false)
const selectedAgentName = ref('')
const selectedAgentThinking = ref('')
const thinkingLoading = ref(false)

// WebSocket 连接
const ws = useWebSocket({
  taskId: taskId.value,
  onEvent: handleWebSocketEvent,
  onStatusChange: handleWsStatusChange,
  onError: handleWsError,
})

// 计算属性：当前阶段索引
const currentPhaseIndex = computed(() => {
  return Math.max(0, progressStateRaw.value.currentPhase - 1)
})

// 计算属性：进度状态
const progressStatus = computed(() => {
  if (task.value?.status === TaskStatusEnum.COMPLETED) return 'success'
  if (task.value?.status === TaskStatusEnum.FAILED) return 'exception'
  return undefined
})

// 计算属性：是否可以停止
const canStop = computed(() => {
  return task.value?.status === TaskStatusEnum.RUNNING
})

// 计算属性：是否显示最终报告
const showFinalReport = computed(() => {
  return task.value?.final_report || task.value?.final_recommendation
})

// 计算属性：Token 统计
const tokenStats = computed(() => tokenUsage.totalUsage)

// 计算属性：估算成本
const estimatedCost = computed(() => tokenUsage.estimatedCost)

// 计算属性：进度状态
const progressState = computed(() => progressStateRaw.value)

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
 * 格式化持续时间
 */
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}小时${minutes}分${secs}秒`
  }
  if (minutes > 0) {
    return `${minutes}分${secs}秒`
  }
  return `${secs}秒`
}

/**
 * 格式化 Token 数量
 */
function formatTokenCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`
  }
  return count.toString()
}

/**
 * WebSocket 事件处理
 */
function handleWebSocketEvent(event: any) {
  handleProgressEvent(event)

  // 更新 Token 使用
  if (event.data?.token_usage) {
    tokenUsage.updateTokenUsage(event.data.token_usage)
  }
}

/**
 * WebSocket 状态变化
 */
function handleWsStatusChange(status: WebSocketStatus) {
  console.log('[AnalysisDetail] WebSocket 状态:', status)
}

/**
 * WebSocket 错误
 */
function handleWsError(err: Error) {
  console.error('[AnalysisDetail] WebSocket 错误:', err)
  // WebSocket 连接失败不影响任务详情显示，仅记录错误
  // 实时更新功能会失效，但用户仍可查看静态数据
}

/**
 * 加载任务信息
 */
async function loadTask() {
  loading.value = true
  error.value = false

  try {
    const response = await taskApi.getTask(taskId.value)
    task.value = response

    // 更新进度状态
    if (response) {
      // 重置并初始化进度状态
      progress.reset()
      if (response.current_phase) {
        progress.state.value.currentPhase = response.current_phase
      }
      if (response.progress) {
        progress.state.value.progress = response.progress
      }
      if (response.reports) {
        progress.state.value.reports = new Map(Object.entries(response.reports))
      }
      if (response.created_at) {
        progress.state.value.startTime = new Date(response.created_at).getTime()
      }
      if (response.completed_at) {
        progress.state.value.endTime = new Date(response.completed_at).getTime()
      }
      if (response.current_agent) {
        progress.currentAgent.value = response.current_agent
      }
    }

    // 更新 Token 使用
    if (response.token_usage) {
      tokenUsage.updateTokenUsage(response.token_usage)
    }
  } catch (err) {
    console.error('加载任务失败:', err)
    error.value = true
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

/**
 * 停止分析
 */
async function handleStop() {
  try {
    await ElMessageBox.confirm(
      '确定要停止当前分析吗？已完成的报告将被保留。',
      '确认停止',
      {
        confirmButtonText: '停止',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await taskApi.cancelTask(taskId.value)
    ElMessage.success('已停止分析')

    // 刷新任务状态
    await loadTask()
  } catch (err) {
    // 用户取消或错误
    if (err !== 'cancel') {
      console.error('停止任务失败:', err)
    }
  }
}

/**
 * 返回
 */
function goBack() {
  router.back()
}

/**
 * 显示智能体思考过程
 */
async function handleShowThinking(agent: AgentStatus) {
  selectedAgentName.value = agent.name
  thinkingLoading.value = true
  thinkingDialogVisible.value = true

  try {
    // TODO: 从后端获取智能体的思考过程
    // 暂时使用模拟数据
    selectedAgentThinking.value = generateMockThinking(agent.name)
  } catch (error) {
    ElMessage.error('加载思考过程失败')
  } finally {
    thinkingLoading.value = false
  }
}

/**
 * 生成模拟思考过程
 */
function generateMockThinking(agentName: string): string {
  return `# ${agentName} 思考过程

## 分析目标
对当前股票进行深入分析，评估投资价值和风险。

## 关键发现

### 1. 基本面分析
- 财务状况良好，营收稳定增长
- 盈利能力持续提升
- 负债率处于合理水平

### 2. 技术面分析
- 股价处于上升趋势
- 成交量温和放大
- 技术指标显示买入信号

### 3. 市场情绪
- 市场对该股票关注度较高
- 投资者情绪整体偏正面
- 机构持仓比例稳定

## 结论
基于以上分析，该股票具有良好的投资价值，建议**买入**。

## 风险提示
- 市场波动风险
- 行业政策变化风险
- 公司经营风险
`
}

// 组件挂载
onMounted(async () => {
  await loadTask()

  // 连接 WebSocket
  if (task.value?.status === TaskStatusEnum.RUNNING) {
    ws.connect()
  }
})

// 组件卸载
onUnmounted(() => {
  ws.disconnect()
})

// 监听任务状态变化
watch(() => task.value?.status, (newStatus) => {
  if (newStatus === TaskStatusEnum.RUNNING && ws.status.value === WebSocketStatus.DISCONNECTED) {
    ws.connect()
  } else if (newStatus === TaskStatusEnum.COMPLETED || newStatus === TaskStatusEnum.FAILED) {
    ws.disconnect()
  }
})
</script>

<style scoped>
.analysis-detail-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.loading-container {
  padding: 40px;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card {
  margin-bottom: 20px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.overview-item .item-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.overview-item .item-value {
  font-size: 16px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.phase-card,
.agents-card,
.reports-card,
.final-report-card,
.tools-card,
.token-card {
  margin-bottom: 20px;
}

.running-agents,
.completed-agents {
  display: grid;
  gap: 12px;
}

.reports-list {
  display: grid;
  gap: 16px;
}

.token-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.stat-label {
  color: var(--el-text-color-secondary);
}

.stat-value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.stat-total {
  font-weight: 600;
}
</style>
