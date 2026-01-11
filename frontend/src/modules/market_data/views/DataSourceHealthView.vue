<template>
  <div class="data-source-health-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon class="header-icon" :size="28">
          <Connection />
        </el-icon>
        <div>
          <h2>数据源监控</h2>
          <p class="description">
            实时监控市场数据源的健康状态和响应时间
          </p>
        </div>
      </div>
      <el-button @click="handleRefresh" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 数据源状态卡片 -->
    <el-row :gutter="20" class="status-cards">
      <el-col
        v-for="source in healthData"
        :key="source.sourceName"
        :xs="24"
        :sm="12"
        :md="8"
      >
        <el-card class="status-card" :class="{ 'status-error': !source.isAvailable }">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-icon class="source-icon" :size="24">
                  <component :is="getSourceIcon(source.sourceName)" />
                </el-icon>
                <span class="source-name">{{ getSourceDisplayName(source.sourceName) }}</span>
              </div>
              <el-tag
                :type="source.isAvailable ? 'success' : 'danger'"
                size="large"
              >
                {{ source.isAvailable ? '正常' : '异常' }}
              </el-tag>
            </div>
          </template>

          <div class="status-content">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="响应时间">
                <span v-if="source.responseTimeMs">
                  {{ source.responseTimeMs }} ms
                  <el-tag
                    v-if="source.responseTimeMs < 200"
                    type="success"
                    size="small"
                    style="margin-left: 8px"
                  >
                    快速
                  </el-tag>
                  <el-tag
                    v-else-if="source.responseTimeMs < 1000"
                    type="warning"
                    size="small"
                    style="margin-left: 8px"
                  >
                    一般
                  </el-tag>
                  <el-tag
                    v-else
                    type="danger"
                    size="small"
                    style="margin-left: 8px"
                  >
                    慢
                  </el-tag>
                </span>
                <span v-else>-</span>
              </el-descriptions-item>

              <el-descriptions-item label="失败次数">
                <el-tag
                  :type="source.failureCount > 0 ? 'danger' : 'success'"
                  size="small"
                >
                  {{ source.failureCount }}
                </el-tag>
              </el-descriptions-item>

              <el-descriptions-item label="最后检查">
                {{ formatTime(source.lastCheckTime) }}
              </el-descriptions-item>

              <el-descriptions-item
                v-if="source.error"
                label="错误信息"
              >
                <el-text type="danger" class="error-text">
                  {{ source.error }}
                </el-text>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计图表 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>响应时间趋势</span>
          <el-radio-group v-model="timeRange" @change="handleTimeRangeChange">
            <el-radio-button label="1h">近1小时</el-radio-button>
            <el-radio-button label="24h">近24小时</el-radio-button>
            <el-radio-button label="7d">近7天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div class="chart-placeholder">
        <el-empty
          description="响应时间趋势图表开发中"
          :image-size="200"
        />
      </div>
    </el-card>

    <!-- 数据源说明 -->
    <el-card class="info-card">
      <template #header>
        <span>数据源说明</span>
      </template>

      <el-collapse>
        <el-collapse-item title="TuShare Pro" name="tushare">
          <div class="info-content">
            <p><strong>TuShare Pro</strong> 是专业的A股数据服务平台，提供全面、准确的金融数据。</p>
            <ul>
              <li><strong>优势</strong>: 数据质量高、响应速度快、覆盖全面</li>
              <li><strong>劣势</strong>: 需要付费、有API调用限制</li>
              <li><strong>适用场景</strong>: 生产环境、对数据质量要求高的场景</li>
              <li><strong>优先级</strong>: 1（最高）</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="AkShare" name="akshare">
          <div class="info-content">
            <p><strong>AkShare</strong> 是开源的财经数据接口库，提供免费的金融数据获取服务。</p>
            <ul>
              <li><strong>优势</strong>: 完全免费、开源、无需注册</li>
              <li><strong>劣势</strong>: 数据质量不稳定、响应较慢、可能中断</li>
              <li><strong>适用场景</strong>: 开发测试、个人学习、数据降级备用</li>
              <li><strong>优先级</strong>: 2（备用）</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="自动降级策略" name="fallback">
          <div class="info-content">
            <p>系统采用智能降级策略，确保数据获取的高可用性：</p>
            <ol>
              <li><strong>优先使用</strong>: 系统优先使用TuShare Pro获取数据</li>
              <li><strong>故障检测</strong>: 实时监控数据源健康状态</li>
              <li><strong>自动切换</strong>: TuShare失败时自动切换到AkShare</li>
              <li><strong>恢复机制</strong>: TuShare恢复后自动切回主数据源</li>
              <li><strong>熔断保护</strong>: 连续失败超过阈值时暂时禁用数据源</li>
            </ol>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection,
  Refresh,
  TrendCharts,
  DataLine
} from '@element-plus/icons-vue'
import marketDataApi from '../api/marketDataApi'
import type { DataSourceHealth } from '../types'

// 状态
const loading = ref(false)
const healthData = ref<DataSourceHealth[]>([])
const timeRange = ref('1h')
let refreshTimer: any = null

/**
 * 获取数据源图标
 */
const getSourceIcon = (sourceName: string) => {
  return TrendCharts
}

/**
 * 获取数据源显示名称
 */
const getSourceDisplayName = (sourceName: string) => {
  const nameMap: Record<string, string> = {
    'tushare': 'TuShare Pro',
    'akshare': 'AkShare'
  }
  return nameMap[sourceName] || sourceName
}

/**
 * 格式化时间
 */
const formatTime = (timeStr?: string) => {
  if (!timeStr) return '-'
  try {
    const date = new Date(timeStr)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diff < 60) return `${diff}秒前`
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    return date.toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

/**
 * 检查数据源健康状态
 */
const checkHealth = async () => {
  try {
    loading.value = true
    const data = await marketDataApi.checkDataSourcesHealth()
    healthData.value = data
  } catch (error: any) {
    ElMessage.error(`获取健康状态失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/**
 * 刷新
 */
const handleRefresh = () => {
  checkHealth()
}

/**
 * 时间范围变更
 */
const handleTimeRangeChange = () => {
  // TODO: 根据时间范围更新图表数据
  ElMessage.info('图表功能开发中...')
}

/**
 * 启动定时刷新
 */
const startRefreshTimer = () => {
  // 每30秒自动刷新一次
  refreshTimer = setInterval(() => {
    checkHealth()
  }, 30000)
}

/**
 * 停止定时刷新
 */
const stopRefreshTimer = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 初始化
onMounted(() => {
  checkHealth()
  startRefreshTimer()
})

onUnmounted(() => {
  stopRefreshTimer()
})
</script>

<style scoped lang="scss">
.data-source-health-view {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .header-content {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      color: var(--el-color-primary);
    }

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }

    .description {
      margin: 4px 0 0 0;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }
}

.status-cards {
  margin-bottom: 20px;

  .status-card {
    &.status-error {
      :deep(.el-card__header) {
        background-color: var(--el-color-danger-light-9);
        border-bottom: 2px solid var(--el-color-danger);
      }
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;

        .source-icon {
          color: var(--el-color-primary);
        }

        .source-name {
          font-size: 16px;
          font-weight: 600;
        }
      }
    }

    .status-content {
      .error-text {
        word-break: break-all;
      }
    }
  }
}

.chart-card {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chart-placeholder {
    height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.info-card {
  .info-content {
    p {
      margin: 0 0 12px 0;
      font-weight: 600;
    }

    ul, ol {
      margin: 0;
      padding-left: 20px;

      li {
        margin: 8px 0;
        line-height: 1.6;
      }
    }
  }
}
</style>
