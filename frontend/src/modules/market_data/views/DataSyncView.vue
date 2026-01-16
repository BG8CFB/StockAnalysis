<template>
  <div class="data-sync-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>数据同步</h2>
    </div>

    <!-- 同步控制区 -->
    <el-card class="sync-card">
      <template #header>
        <div class="card-header">
          <span>全量同步</span>
          <el-tag :type="syncStatus === 'syncing' ? 'warning' : 'info'" size="small">
            {{ syncStatusText }}
          </el-tag>
        </div>
      </template>

      <div class="sync-content">
        <div class="sync-description">
          <p>触发全量数据同步，包括：</p>
          <ul>
            <li>股票列表</li>
            <li>日线行情（最近1个月，前100只股票）</li>
            <li>公司信息（仅A股）</li>
          </ul>
          <el-alert
            title="注意"
            type="warning"
            :closable="false"
            show-icon
          >
            此操作可能需要较长时间，建议在非高峰期执行。
          </el-alert>
        </div>

        <!-- 市场选择 -->
        <div class="market-selector">
          <span class="label">选择市场：</span>
          <el-radio-group v-model="selectedMarket" :disabled="syncStatus === 'syncing'">
            <el-radio-button label="A_STOCK">A股</el-radio-button>
            <el-radio-button label="US_STOCK">美股</el-radio-button>
            <el-radio-button label="HK_STOCK">港股</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 同步按钮 -->
        <div class="sync-button-wrapper">
          <el-button
            type="primary"
            size="large"
            :loading="syncStatus === 'syncing'"
            :disabled="syncStatus === 'syncing'"
            @click="handleSync"
          >
            <el-icon v-if="syncStatus !== 'syncing'"><Refresh /></el-icon>
            {{ syncButtonText }}
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 同步结果 -->
    <el-card v-if="syncResult" class="result-card">
      <template #header>
        <div class="card-header">
          <span>同步结果</span>
          <el-tag :type="syncResult.successful_tasks === syncResult.total_tasks ? 'success' : 'warning'" size="small">
            {{ syncResult.successful_tasks }}/{{ syncResult.total_tasks }} 成功
          </el-tag>
        </div>
      </template>

      <div class="result-content">
        <div class="result-info">
          <p><strong>市场：</strong>{{ syncResult.market }}</p>
          <p><strong>开始时间：</strong>{{ formatTime(syncResult.started_at) }}</p>
          <p><strong>结束时间：</strong>{{ formatTime(syncResult.finished_at) }}</p>
        </div>

        <el-divider />

        <div class="tasks-list">
          <h4>任务详情</h4>
          <div
            v-for="(task, index) in syncResult.tasks"
            :key="index"
            class="task-item"
          >
            <div class="task-header">
              <span class="task-name">{{ task.name }}</span>
              <el-tag
                :type="getTaskStatusType(task.status)"
                size="small"
              >
                {{ getTaskStatusLabel(task.status) }}
              </el-tag>
            </div>
            <div v-if="task.result" class="task-result">
              <span v-if="task.result.total !== undefined">
                总计：{{ task.result.total || 0 }} 条
              </span>
              <span v-if="task.result.total_quotes !== undefined">
                行情：{{ task.result.total_quotes || 0 }} 条
              </span>
              <span v-if="task.result.total_records !== undefined">
                记录：{{ task.result.total_records || 0 }} 条
              </span>
              <span v-if="task.result.source" class="source-tag">
                数据源：{{ task.result.source }}
              </span>
            </div>
            <div v-if="task.error" class="task-error">
              <el-text type="danger">{{ task.error }}</el-text>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import marketDataApi from '../api/marketDataApi'

// 状态
const syncStatus = ref<'idle' | 'syncing' | 'completed'>('idle')
const selectedMarket = ref('A_STOCK')
const syncResult = ref<any>(null)

// 计算属性
const syncStatusText = computed(() => {
  switch (syncStatus.value) {
    case 'syncing':
      return '同步中...'
    case 'completed':
      return '同步完成'
    default:
      return '待同步'
  }
})

const syncButtonText = computed(() => {
  return syncStatus.value === 'syncing' ? '同步中...' : '开始全量同步'
})

// 格式化时间
const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 获取任务状态标签类型
const getTaskStatusType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'completed_with_errors':
      return 'warning'
    case 'failed':
      return 'danger'
    case 'skipped':
      return 'info'
    default:
      return 'info'
  }
}

// 获取任务状态标签
const getTaskStatusLabel = (status: string) => {
  switch (status) {
    case 'completed':
      return '成功'
    case 'completed_with_errors':
      return '部分成功'
    case 'failed':
      return '失败'
    case 'skipped':
      return '跳过'
    default:
      return status
  }
}

// 处理同步
const handleSync = async () => {
  try {
    syncStatus.value = 'syncing'
    syncResult.value = null

    ElMessage.info(`开始同步 ${selectedMarket.value} 数据...`)

    const result = await marketDataApi.triggerFullSync(selectedMarket.value)

    syncResult.value = result
    syncStatus.value = 'completed'

    if (result.successful_tasks === result.total_tasks) {
      ElMessage.success('全量同步完成！')
    } else {
      ElMessage.warning(`同步完成，部分任务失败：${result.successful_tasks}/${result.total_tasks}`)
    }
  } catch (error: any) {
    syncStatus.value = 'idle'
    ElMessage.error(`同步失败: ${error.message || '未知错误'}`)
  }
}
</script>

<style scoped lang="scss">
.data-sync-view {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
}

.sync-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sync-content {
  .sync-description {
    margin-bottom: 20px;

    p {
      margin: 0 0 8px 0;
      font-weight: 500;
    }

    ul {
      margin: 8px 0 16px 20px;
      padding: 0;

      li {
        margin-bottom: 4px;
      }
    }

    .el-alert {
      margin-top: 12px;
    }
  }

  .market-selector {
    display: flex;
    align-items: center;
    margin-bottom: 20px;

    .label {
      margin-right: 12px;
      font-weight: 500;
    }
  }

  .sync-button-wrapper {
    display: flex;
    justify-content: center;
    padding: 20px 0;

    .el-button {
      min-width: 200px;
    }
  }
}

.result-card {
  .result-content {
    .result-info {
      margin-bottom: 16px;

      p {
        margin: 4px 0;
        font-size: 14px;
      }
    }

    .tasks-list {
      h4 {
        margin: 0 0 12px 0;
        font-size: 16px;
        font-weight: 600;
      }

      .task-item {
        padding: 12px;
        margin-bottom: 12px;
        background-color: var(--el-fill-color-light);
        border-radius: 4px;

        &:last-child {
          margin-bottom: 0;
        }

        .task-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;

          .task-name {
            font-weight: 500;
          }
        }

        .task-result {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          font-size: 13px;
          color: var(--el-text-color-regular);

          .source-tag {
            color: var(--el-color-primary);
            font-weight: 500;
          }
        }

        .task-error {
          margin-top: 8px;
          font-size: 13px;
        }
      }
    }
  }
}
</style>
