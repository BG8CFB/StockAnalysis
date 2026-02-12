<template>
  <div class="tool-call-log">
    <div class="log-header">
      <h4>工具调用记录</h4>
      <el-badge
        :value="toolCalls.length"
        :max="99"
        class="badge"
      />
    </div>

    <div class="log-list">
      <el-timeline>
        <el-timeline-item
          v-for="call in displayCalls"
          :key="call.startTime"
          :timestamp="formatTime(call.startTime)"
          placement="top"
          :type="getTimelineType(call.status)"
          :icon="getTimelineIcon(call.status)"
        >
          <div class="call-item">
            <div class="call-header">
              <span class="tool-name">{{ call.toolName }}</span>
              <el-tag
                :type="getStatusType(call.status)"
                size="small"
              >
                {{ getStatusLabel(call.status) }}
              </el-tag>
            </div>
            <div class="call-info">
              <span class="agent-name">来源: {{ call.agentName }}</span>
              <span
                v-if="call.duration"
                class="duration"
              >耗时: {{ call.duration }}ms</span>
            </div>

            <!-- 输入参数 -->
            <el-collapse
              v-if="call.input"
              class="call-detail"
            >
              <el-collapse-item
                title="输入参数"
                name="input"
              >
                <pre class="json-content">{{ formatJson(call.input) }}</pre>
              </el-collapse-item>

              <!-- 输出结果 -->
              <el-collapse-item
                v-if="call.output"
                title="输出结果"
                name="output"
              >
                <pre class="json-content">{{ formatJson(call.output) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-if="toolCalls.length === 0"
      description="暂无工具调用记录"
      :image-size="80"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Tools, Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import type { ToolCallRecord } from '../../composables/useAnalysisProgress'

interface Props {
  toolCalls: ToolCallRecord[]
  maxDisplay?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxDisplay: 20,
})

// 显示的调用记录
const displayCalls = computed(() => {
  return props.toolCalls.slice(-props.maxDisplay).reverse()
})

/**
 * 获取时间线类型
 */
function getTimelineType(status: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return typeMap[status] || 'info'
}

/**
 * 获取时间线图标
 */
function getTimelineIcon(status: string) {
  const iconMap: Record<string, any> = {
    running: Loading,
    completed: CircleCheck,
    failed: CircleClose,
  }
  return iconMap[status] || Tools
}

/**
 * 获取状态标签类型
 */
function getStatusType(status: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return typeMap[status] || 'info'
}

/**
 * 获取状态标签文本
 */
function getStatusLabel(status: string): string {
  const labelMap: Record<string, string> = {
    running: '运行中',
    completed: '完成',
    failed: '失败',
  }
  return labelMap[status] || '未知'
}

/**
 * 格式化时间
 */
function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

/**
 * 格式化 JSON
 */
function formatJson(json: string): string {
  try {
    const parsed = JSON.parse(json)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return json
  }
}

// 计算耗时
const displayCallsWithDuration = computed(() => {
  return displayCalls.value.map((call) => ({
    ...call,
    duration: call.endTime ? call.endTime - call.startTime : null,
  }))
})
</script>

<style scoped>
.tool-call-log {
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.log-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.log-list {
  max-height: 500px;
  overflow-y: auto;
}

.call-item {
  padding: 8px 0;
}

.call-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.tool-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.call-info {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.call-detail {
  margin-top: 8px;
}

.json-content {
  margin: 0;
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  color: var(--el-text-color-primary);
  max-height: 200px;
  overflow: auto;
}
</style>
