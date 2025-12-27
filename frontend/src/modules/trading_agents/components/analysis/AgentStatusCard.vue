<template>
  <div
    class="agent-status-card"
    :class="statusClass"
  >
    <!-- 智能体名称和状态 -->
    <div class="card-header">
      <div class="agent-info">
        <el-icon
          class="agent-icon"
          :size="20"
        >
          <User />
        </el-icon>
        <span class="agent-name">{{ agent.name }}</span>
      </div>
      <el-tag
        :type="statusType"
        size="small"
      >
        {{ statusLabel }}
      </el-tag>
    </div>

    <!-- 进度信息 -->
    <div
      v-if="agent.status === 'running'"
      class="card-body"
    >
      <el-progress
        :percentage="progress"
        :indeterminate="true"
        :show-text="false"
        :stroke-width="2"
      />
      <span class="time-info">运行中: {{ elapsedText }}</span>
    </div>

    <!-- 完成信息 -->
    <div
      v-else-if="agent.status === 'completed'"
      class="card-body"
    >
      <div class="completion-info">
        <el-icon
          class="success-icon"
          :size="16"
        >
          <CircleCheck />
        </el-icon>
        <span>完成于: {{ formatTime(agent.endTime) }}</span>
      </div>
      <div
        v-if="duration"
        class="duration-info"
      >
        耗时: {{ durationText }}
      </div>
    </div>

    <!-- 失败信息 -->
    <div
      v-else-if="agent.status === 'failed'"
      class="card-body"
    >
      <div class="error-info">
        <el-icon
          class="error-icon"
          :size="16"
        >
          <CircleClose />
        </el-icon>
        <span>执行失败</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import type { AgentStatus } from '../../composables/useAnalysisProgress'

interface Props {
  agent: AgentStatus
}

const props = defineProps<Props>()

// 状态对应的类名
const statusClass = computed(() => {
  return `status-${props.agent.status}`
})

// 状态对应的标签类型
const statusType = computed(() => {
  const typeMap: Record<string, any> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return typeMap[props.agent.status] || 'info'
})

// 状态标签文本
const statusLabel = computed(() => {
  const labelMap: Record<string, string> = {
    pending: '待执行',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return labelMap[props.agent.status] || '未知'
})

// 进度百分比
const progress = computed(() => {
  if (props.agent.status === 'completed') return 100
  if (props.agent.status === 'running') {
    // 根据运行时间估算进度
    const elapsed = Date.now() - (props.agent.startTime || 0)
    return Math.min(Math.floor(elapsed / 100), 90)
  }
  return 0
})

// 运行耗时文本
const elapsedText = computed(() => {
  if (!props.agent.startTime) return '-'
  const elapsed = Date.now() - props.agent.startTime
  return formatDuration(elapsed)
})

// 总耗时（毫秒）
const duration = computed(() => {
  if (props.agent.startTime && props.agent.endTime) {
    return props.agent.endTime - props.agent.startTime
  }
  return null
})

// 耗时文本
const durationText = computed(() => {
  return duration.value ? formatDuration(duration.value) : '-'
})

/**
 * 格式化时间
 */
function formatTime(timestamp: number | null): string {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN')
}

/**
 * 格式化持续时间
 */
function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) {
    return `${seconds}秒`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}
</script>

<style scoped>
.agent-status-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-bg-color);
  transition: all 0.3s;
}

.agent-status-card.status-running {
  border-color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

.agent-status-card.status-completed {
  border-color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}

.agent-status-card.status-failed {
  border-color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-icon {
  color: var(--el-text-color-secondary);
}

.agent-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.card-body {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.time-info {
  display: block;
  margin-top: 8px;
}

.completion-info,
.error-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.success-icon {
  color: var(--el-color-success);
}

.error-icon {
  color: var(--el-color-danger);
}

.duration-info {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
}
</style>
