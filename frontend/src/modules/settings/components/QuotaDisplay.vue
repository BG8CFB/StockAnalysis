<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getQuotaInfo } from '@/core/settings'

interface QuotaInfo {
  tasks_used: number
  tasks_limit: number
  tasks_remaining: number
  tasks_usage_percent: number
  storage_used_mb: number
  storage_limit_mb: number
  storage_usage_percent: number
  concurrent_tasks: number
  concurrent_limit: number
  is_near_quota_limit: boolean
}

const quota = ref<QuotaInfo>({
  tasks_used: 0,
  tasks_limit: 100,
  tasks_remaining: 100,
  tasks_usage_percent: 0,
  storage_used_mb: 0,
  storage_limit_mb: 500,
  storage_usage_percent: 0,
  concurrent_tasks: 0,
  concurrent_limit: 5,
  is_near_quota_limit: false,
})

const loading = ref(false)

// 计算进度条类型
const getTaskProgressType = computed(() => {
  const percent = quota.value.tasks_usage_percent
  if (percent >= 90) return 'exception'
  if (percent >= 80) return 'warning'
  return 'success'
})

const getStorageProgressType = computed(() => {
  const percent = quota.value.storage_usage_percent
  if (percent >= 90) return 'exception'
  if (percent >= 80) return 'warning'
  return 'success'
})

// 加载配额信息
const loadQuota = async () => {
  loading.value = true
  try {
    quota.value = await getQuotaInfo()
  } catch (error) {
    console.error('加载配额信息失败', error)
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载
onMounted(() => {
  loadQuota()
})

// 暴露刷新方法
defineExpose({
  loadQuota,
})
</script>

<template>
  <el-card
    v-loading="loading"
    class="quota-display"
  >
    <template #header>
      <div class="card-header">
        <span>配额信息</span>
        <el-button
          text
          @click="loadQuota"
        >
          刷新
        </el-button>
      </div>
    </template>

    <div class="quota-info">
      <!-- 任务配额 -->
      <div class="quota-item">
        <div class="quota-label">
          <span>月度任务</span>
          <span class="quota-count">{{ quota.tasks_used }} / {{ quota.tasks_limit }}</span>
        </div>
        <el-progress
          :percentage="quota.tasks_usage_percent"
          :status="getTaskProgressType"
        />
        <div class="quota-remaining">
          剩余: {{ quota.tasks_remaining }}
        </div>
      </div>

      <!-- 存储备额 -->
      <div class="quota-item">
        <div class="quota-label">
          <span>存储空间</span>
          <span class="quota-count">{{ quota.storage_used_mb.toFixed(2) }} MB / {{ quota.storage_limit_mb }} MB</span>
        </div>
        <el-progress
          :percentage="quota.storage_usage_percent"
          :status="getStorageProgressType"
        />
        <div class="quota-remaining">
          已使用: {{ quota.storage_usage_percent.toFixed(1) }}%
        </div>
      </div>

      <!-- 并发任务 -->
      <div class="quota-item">
        <div class="quota-label">
          <span>并发任务</span>
          <span class="quota-count">{{ quota.concurrent_tasks }} / {{ quota.concurrent_limit }}</span>
        </div>
      </div>

      <!-- 警告提示 -->
      <el-alert
        v-if="quota.is_near_quota_limit"
        title="配额即将用尽"
        type="warning"
        :closable="false"
        show-icon
      >
        您的配额即将用尽，请升级套餐或清理数据
      </el-alert>
    </div>
  </el-card>
</template>

<style scoped>
.quota-display {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.quota-info {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quota-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quota-label {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.quota-count {
  font-weight: bold;
  color: var(--el-text-color-primary);
}

.quota-remaining {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
