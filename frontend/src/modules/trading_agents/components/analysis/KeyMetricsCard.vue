<template>
  <el-card shadow="never" class="key-metrics-card">
    <!-- 投资建议头部 -->
    <div class="recommendation-header">
      <div class="recommendation-label">投资建议</div>
      <el-tag
        :type="getRecommendationType()"
        size="large"
        class="recommendation-tag"
      >
        {{ recommendation || '分析中...' }}
      </el-tag>
    </div>

    <!-- 关键指标网格 -->
    <div class="metrics-grid">
      <!-- 买入价格 -->
      <div class="metric-item">
        <div class="metric-label">买入价格</div>
        <div class="metric-value primary">
          {{ buyPrice ? `¥${buyPrice.toFixed(2)}` : '-' }}
        </div>
      </div>

      <!-- 卖出价格 -->
      <div class="metric-item">
        <div class="metric-label">卖出价格</div>
        <div class="metric-value primary">
          {{ sellPrice ? `¥${sellPrice.toFixed(2)}` : '-' }}
        </div>
      </div>

      <!-- 风险等级 -->
      <div class="metric-item">
        <div class="metric-label">风险等级</div>
        <div class="metric-value" :class="getRiskClass()">
          {{ riskLevel || '-' }}
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  recommendation?: string | null
  buyPrice?: number | null
  sellPrice?: number | null
  riskLevel?: string | null
}

const props = defineProps<Props>()

function getRecommendationType(): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  if (!props.recommendation) return 'info'

  const rec = props.recommendation.toUpperCase()
  if (rec.includes('BUY') || rec === 'STRONG_BUY') return 'success'
  if (rec.includes('SELL') || rec === 'STRONG_SELL') return 'danger'
  if (rec === 'HOLD') return 'warning'
  return 'info'
}

function getRiskClass(): string {
  if (!props.riskLevel) return ''

  const risk = props.riskLevel.toUpperCase()
  if (risk === 'LOW') return 'risk-low'
  if (risk === 'MEDIUM') return 'risk-medium'
  if (risk === 'HIGH') return 'risk-high'
  return ''
}
</script>

<style scoped>
.key-metrics-card {
  margin-bottom: 20px;
}

.recommendation-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color);
  margin-bottom: 16px;
}

.recommendation-label {
  font-size: 16px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

.recommendation-tag {
  font-size: 16px;
  padding: 8px 16px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.metric-item {
  padding: 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.metric-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.metric-value.primary {
  color: var(--el-color-primary);
}

.metric-value.risk-low {
  color: var(--el-color-success);
}

.metric-value.risk-medium {
  color: var(--el-color-warning);
}

.metric-value.risk-high {
  color: var(--el-color-danger);
}
</style>
