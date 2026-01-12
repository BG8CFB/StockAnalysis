<template>
  <div class="data-source-health-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon class="header-icon" :size="28">
          <Connection />
        </el-icon>
        <div>
          <h2>数据源状态监控</h2>
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

    <!-- 市场标签页 -->
    <el-tabs v-model="activeMarket" @tab-change="handleMarketChange" class="market-tabs">
      <el-tab-pane label="A股" :name="MarketType.A_STOCK" />
      <el-tab-pane label="美股" :name="MarketType.US_STOCK" />
      <el-tab-pane label="港股" :name="MarketType.HK_STOCK" />
    </el-tabs>

    <!-- 数据类型状态列表 -->
    <div class="data-types-container">
      <el-card
        v-for="dataType in currentMarketDataTypes"
        :key="dataType.dataType"
        class="data-type-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <el-tag :type="getDataSourceStatusTagType(dataType.currentSource.status)" size="large">
                {{ getDataSourceStatusLabel(dataType.currentSource.status) }}
              </el-tag>
              <span class="data-type-name">{{ dataType.dataTypeName }}</span>
              <el-tag v-if="dataType.isFallback" type="warning" size="small" style="margin-left: 8px">
                已降级
              </el-tag>
            </div>
            <el-button type="primary" link @click="handleViewDetail(dataType)">
              查看详情
            </el-button>
          </div>
        </template>

        <div class="card-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="当前使用">
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag type="success" size="small">
                  {{ dataSourceDisplayName(dataType.currentSource.sourceName) }}
                </el-tag>
                <span>{{ getDataSourceStatusLabel(dataType.currentSource.status) }}</span>
              </div>
            </el-descriptions-item>

            <el-descriptions-item label="最后检查">
              {{ formatTime(dataType.currentSource.lastCheck) }}
            </el-descriptions-item>

            <el-descriptions-item v-if="dataType.currentSource.responseTimeMs" label="响应时间">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>{{ dataType.currentSource.responseTimeMs }} ms</span>
                <el-tag
                  v-if="dataType.currentSource.responseTimeMs < 200"
                  type="success"
                  size="small"
                >
                  快速
                </el-tag>
                <el-tag
                  v-else-if="dataType.currentSource.responseTimeMs < 1000"
                  type="warning"
                  size="small"
                >
                  一般
                </el-tag>
                <el-tag
                  v-else
                  type="danger"
                  size="small"
                >
                  慢
                </el-tag>
              </div>
            </el-descriptions-item>

            <el-descriptions-item v-if="dataType.isFallback" label="降级信息">
              <el-text type="warning">{{ dataType.fallbackReason }}</el-text>
            </el-descriptions-item>

            <el-descriptions-item v-if="dataType.primarySource && dataType.canRetry" label="主数据源状态">
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag type="danger" size="small">
                  {{ dataSourceDisplayName(dataType.primarySource.sourceId) }}
                </el-tag>
                <span>{{ dataType.primarySource.status }}</span>
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="handleRetry(dataType.primarySource.sourceId, dataType.dataType)"
                >
                  重试
                </el-button>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-card>
    </div>

    <!-- 响应时间趋势图表 -->
    <el-card class="chart-card">
      <template #header>
        <div class="chart-header">
          <span>响应时间趋势</span>
          <el-radio-group v-model="timeRange" @change="handleTimeRangeChange">
            <el-radio-button label="1h">近1小时</el-radio-button>
            <el-radio-button label="24h">近24小时</el-radio-button>
            <el-radio-button label="7d">近7天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div ref="chartContainer" class="chart-container" />
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

        <el-collapse-item title="Yahoo Finance" name="yahoo_finance">
          <div class="info-content">
            <p><strong>Yahoo Finance</strong> 是免费的金融数据服务提供商，覆盖全球市场。</p>
            <ul>
              <li><strong>优势</strong>: 数据权威、覆盖全、稳定性高、完全免费</li>
              <li><strong>劣势</strong>: 无官方Python SDK，需要使用第三方库</li>
              <li><strong>适用场景</strong>: 美股/港股数据的主要数据源</li>
              <li><strong>优先级</strong>: 1（最高）</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="Alpha Vantage" name="alpha_vantage">
          <div class="info-content">
            <p><strong>Alpha Vantage</strong> 是提供金融数据和新闻的服务商，支持多种技术指标计算。</p>
            <ul>
              <li><strong>优势</strong>: 20+ 技术指标、数据全面</li>
              <li><strong>劣势</strong>: 免费版限制较多（5次/分钟）</li>
              <li><strong>适用场景</strong>: 美股技术指标数据</li>
              <li><strong>优先级</strong>: 2（备用）</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="自动降级策略" name="fallback">
          <div class="info-content">
            <p>系统采用智能降级策略，确保数据获取的高可用性：</p>
            <ol>
              <li><strong>优先使用</strong>: 系统优先使用主数据源获取数据</li>
              <li><strong>故障检测</strong>: 实时监控数据源健康状态</li>
              <li><strong>自动切换</strong>: 主数据源失败时自动切换到备用数据源</li>
              <li><strong>恢复机制</strong>: 主数据源恢复后自动切回</li>
              <li><strong>熔断保护</strong>: 连续失败超过阈值时暂时禁用数据源</li>
            </ol>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`${selectedDataType?.dataTypeName} - 详细信息`"
      width="800px"
      destroy-on-close
    >
      <div v-if="selectedDataTypeDetail" class="detail-dialog">
        <div class="detail-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="数据类型">
              {{ selectedDataTypeDetail.dataTypeName }}
            </el-descriptions-item>
            <el-descriptions-item label="市场">
              {{ MarketTypeName[selectedDataTypeDetail.market] }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div v-for="source in selectedDataTypeDetail.sources" :key="source.sourceId" class="source-section">
          <el-divider>
            <el-tag :type="getDataSourceStatusTagType(source.status)" size="large">
              {{ dataSourceDisplayName(source.sourceName) }}
            </el-tag>
            <span style="margin-left: 12px;">{{ getDataSourceStatusLabel(source.status) }}</span>
          </el-divider>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="优先级">
              {{ source.priority }}
            </el-descriptions-item>
            <el-descriptions-item v-if="source.lastCheck" label="最后检查">
              {{ formatTime(source.lastCheck) }}
            </el-descriptions-item>
            <el-descriptions-item v-if="source.responseTimeMs" label="响应时间">
              {{ source.responseTimeMs }} ms
            </el-descriptions-item>
            <el-descriptions-item v-if="source.avgResponseTimeMs" label="平均响应时间">
              {{ source.avgResponseTimeMs }} ms
            </el-descriptions-item>
            <el-descriptions-item label="失败次数">
              <el-tag :type="source.failureCount > 0 ? 'danger' : 'success'" size="small">
                {{ source.failureCount }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="source.note" label="备注">
              <el-text type="info">{{ source.note }}</el-text>
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="source.apiEndpoints && source.apiEndpoints.length > 0" class="api-endpoints">
            <h4>接口明细</h4>
            <el-table :data="source.apiEndpoints" border size="small">
              <el-table-column prop="endpointNameCn" label="接口名称" width="200" />
              <el-table-column prop="endpointName" label="接口代码" width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getDataSourceStatusTagType(row.status)" size="small">
                    {{ getDataSourceStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="失败次数" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.failureCount > 0 ? 'danger' : 'success'" size="small">
                    {{ row.failureCount }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="最后检查" min-width="150">
                <template #default="{ row }">
                  {{ row.lastCheck ? formatTime(row.lastCheck) : '-' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <el-divider>最近状态变化</el-divider>

        <el-timeline>
          <el-timeline-item
            v-for="(event, index) in selectedDataTypeDetail.recentEvents"
            :key="index"
            :timestamp="formatTime(event.timestamp)"
            placement="top"
          >
            <el-card>
              <p>{{ event.description }}</p>
              <div v-if="event.fromSource && event.toSource" class="event-source-change">
                <el-tag size="small">{{ dataSourceDisplayName(event.fromSource) }}</el-tag>
                <el-icon><Right /></el-icon>
                <el-tag type="success" size="small">{{ dataSourceDisplayName(event.toSource) }}</el-tag>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="handleExportLog" :loading="exporting">
            <el-icon><Download /></el-icon>
            导出日志
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 错误详情对话框 -->
    <el-dialog
      v-model="errorDialogVisible"
      title="接口错误详情"
      width="700px"
      destroy-on-close
    >
      <div v-if="selectedError" class="error-dialog">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="接口">
            {{ selectedError.error?.apiEndpoint || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="数据源">
            {{ selectedError.sourceName }}
          </el-descriptions-item>
          <el-descriptions-item label="市场">
            {{ MarketTypeName[selectedError.market] }}
          </el-descriptions-item>
          <el-descriptions-item label="数据类型">
            {{ selectedError.dataType }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>错误信息</el-divider>

        <el-alert
          v-if="selectedError.error?.status === 'unavailable'"
          type="error"
          :closable="false"
          style="margin-bottom: 16px"
        >
          <template #title>
            状态：❌ 不可用 (连续失败{{ selectedError.error.failureCount }}次)
          </template>
        </el-alert>

        <el-alert
          v-else
          type="warning"
          :closable="false"
          style="margin-bottom: 16px"
        >
          <template #title>
            状态：⚠️ 异常
          </template>
        </el-alert>

        <div v-if="selectedError.error" class="error-details">
          <div class="error-item">
            <span class="label">错误类型：</span>
            <el-text type="danger">{{ selectedError.error.errorType || '-' }}</el-text>
          </div>
          <div class="error-item">
            <span class="label">错误代码：</span>
            <el-text type="danger">{{ selectedError.error.errorCode || '-' }}</el-text>
          </div>
          <div class="error-item">
            <span class="label">错误描述：</span>
            <el-text type="danger">{{ selectedError.error.errorMessage || '-' }}</el-text>
          </div>
          <div v-if="selectedError.error.occurredAt" class="error-item">
            <span class="label">发生时间：</span>
            <el-text>{{ formatTime(selectedError.error.occurredAt) }}</el-text>
          </div>

          <div v-if="selectedError.error.rawResponse" class="error-raw-response">
            <span class="label">完整响应：</span>
            <el-card shadow="never">
              <pre>{{ JSON.stringify(selectedError.error.rawResponse, null, 2) }}</pre>
            </el-card>
          </div>

          <div v-if="selectedError.error.retryHistory && selectedError.error.retryHistory.length > 0" class="retry-history">
            <span class="label">重试记录：</span>
            <el-timeline>
              <el-timeline-item
                v-for="(retry, index) in selectedError.error.retryHistory"
                :key="index"
                :timestamp="formatTime(retry.timestamp)"
                size="small"
              >
                第 {{ retry.attempt }} 次失败 - {{ retry.error }}
              </el-timeline-item>
            </el-timeline>
          </div>

          <!-- 管理员调试信息 -->
          <div v-if="isAdmin && selectedError.adminDebugInfo" class="admin-debug-info">
            <el-divider>管理员调试信息</el-divider>
            <div v-if="selectedError.adminDebugInfo.traceback" class="debug-item">
              <span class="label">完整堆栈：</span>
              <el-card shadow="never">
                <pre>{{ selectedError.adminDebugInfo.traceback }}</pre>
              </el-card>
            </div>
            <div v-if="selectedError.adminDebugInfo.requestParams" class="debug-item">
              <span class="label">请求参数：</span>
              <el-card shadow="never">
                <pre>{{ JSON.stringify(selectedError.adminDebugInfo.requestParams, null, 2) }}</pre>
              </el-card>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="errorDialogVisible = false">关闭</el-button>
          <el-button @click="handleCopyError">
            <el-icon><CopyDocument /></el-icon>
            复制错误信息
          </el-button>
          <el-button
            v-if="selectedError?.error?.status === 'unavailable'"
            type="primary"
            @click="handleRetryFromError"
            :loading="retrying"
          >
            <el-icon><RefreshRight /></el-icon>
            立即重试
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection,
  Refresh,
  Download,
  Right,
  CopyDocument,
  RefreshRight,
  TrendCharts
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import marketDataApi from '../api/marketDataApi'
import {
  MarketType,
  MarketTypeName,
  DataSourceStatus,
  DataSourceStatusLabels,
  DataSourceStatusTagType,
  DataSourceDisplayName,
  DataSourceIconName,
  type DashboardOverview,
  type MarketDetail,
  type DataTypeStatus,
  type DataTypeDetail,
  type ErrorDetail,
  type RetryResponse
} from '../types'

const router = useRouter()

// 状态
const loading = ref(false)
const activeMarket = ref<MarketType>(MarketType.A_STOCK)
const timeRange = ref('1h')
const dashboardOverview = ref<DashboardOverview>({})
const marketDetail = ref<MarketDetail | null>(null)

// 图表
const chartContainer = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// 对话框
const detailDialogVisible = ref(false)
const selectedDataType = ref<DataTypeStatus | null>(null)
const selectedDataTypeDetail = ref<DataTypeDetail | null>(null)

const errorDialogVisible = ref(false)
const selectedError = ref<ErrorDetail | null>(null)
const exporting = ref(false)
const retrying = ref(false)

// 定时刷新
let refreshTimer: any = null

// 用户信息（判断是否管理员）
const isAdmin = ref(false)

// 当前市场数据类型列表
const currentMarketDataTypes = computed(() => {
  if (!marketDetail.value) return []
  return marketDetail.value.dataTypes
})

/**
 * 获取数据源显示名称
 */
const dataSourceDisplayName = (sourceIdOrName: string) => {
  return DataSourceDisplayName[sourceIdOrName] || sourceIdOrName
}

/**
 * 获取数据源状态标签
 */
const getDataSourceStatusLabel = (status: DataSourceStatus) => {
  return DataSourceStatusLabels[status] || status
}

/**
 * 获取数据源状态标签类型
 */
const getDataSourceStatusTagType = (status: DataSourceStatus) => {
  return DataSourceStatusTagType[status] || ''
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
 * 获取仪表板概览
 */
const fetchDashboardOverview = async () => {
  try {
    loading.value = true
    const data = await marketDataApi.getDashboardOverview()
    dashboardOverview.value = data
  } catch (error: any) {
    ElMessage.error(`获取概览失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/**
 * 获取市场详细状态
 */
const fetchMarketDetail = async () => {
  try {
    loading.value = true
    const data = await marketDataApi.getMarketDetail(activeMarket.value)
    marketDetail.value = data
  } catch (error: any) {
    ElMessage.error(`获取状态失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/**
 * 市场变更
 */
const handleMarketChange = () => {
  fetchMarketDetail()
}

/**
 * 刷新
 */
const handleRefresh = async () => {
  await fetchMarketDetail()
  ElMessage.success('状态已刷新')
}

/**
 * 时间范围变更
 */
const handleTimeRangeChange = () => {
  updateChart()
}

/**
 * 初始化图表
 */
const initChart = () => {
  if (!chartContainer.value) return

  chartInstance = echarts.init(chartContainer.value)
  updateChart()

  // 监听窗口大小变化
  window.addEventListener('resize', handleChartResize)
}

/**
 * 处理图表大小变化
 */
const handleChartResize = () => {
  chartInstance?.resize()
}

/**
 * 生成模拟响应时间数据
 */
const generateMockResponseTimeData = () => {
  const now = Date.now()
  const data: Array<{ time: string; value: number }> = []
  const points = timeRange.value === '1h' ? 12 : timeRange.value === '24h' ? 24 : 7
  const interval = timeRange.value === '1h' ? 5 * 60 * 1000 : timeRange.value === '24h' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000

  for (let i = points - 1; i >= 0; i--) {
    const timestamp = now - i * interval
    const date = new Date(timestamp)
    let timeLabel = ''

    if (timeRange.value === '1h') {
      timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    } else if (timeRange.value === '24h') {
      timeLabel = `${date.getHours().toString().padStart(2, '0')}:00`
    } else {
      timeLabel = `${date.getMonth() + 1}/${date.getDate()}`
    }

    // 生成 50-300ms 之间的随机响应时间
    const value = Math.floor(Math.random() * 250) + 50
    data.push({ time: timeLabel, value })
  }

  return data
}

/**
 * 更新图表
 */
const updateChart = () => {
  if (!chartInstance) return

  const mockData = generateMockResponseTimeData()
  const times = mockData.map(d => d.time)
  const values = mockData.map(d => d.value)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: {
        lineStyle: {
          color: '#374151'
        }
      },
      axisLabel: {
        color: '#9ca3af'
      }
    },
    yAxis: {
      type: 'value',
      name: '响应时间 (ms)',
      nameTextStyle: {
        color: '#9ca3af'
      },
      axisLine: {
        lineStyle: {
          color: '#374151'
        }
      },
      axisLabel: {
        color: '#9ca3af'
      },
      splitLine: {
        lineStyle: {
          color: '#374151',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '平均响应时间',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: values,
        itemStyle: {
          color: '#3b82f6'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

/**
 * 销毁图表
 */
const destroyChart = () => {
  window.removeEventListener('resize', handleChartResize)
  chartInstance?.dispose()
  chartInstance = null
}

/**
 * 查看详情
 */
const handleViewDetail = async (dataType: DataTypeStatus) => {
  selectedDataType.value = dataType
  try {
    const detail = await marketDataApi.getDataTypeDetail(
      activeMarket.value,
      dataType.dataType
    )
    selectedDataTypeDetail.value = detail
    detailDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(`获取详情失败: ${error.message || '未知错误'}`)
  }
}

/**
 * 重试数据源
 */
const handleRetry = async (sourceId: string, dataType: string) => {
  try {
    retrying.value = true
    const response = await marketDataApi.retryDataSource(
      activeMarket.value,
      dataType,
      sourceId
    )

    if (response.success) {
      ElMessage.success(response.message)
      await fetchMarketDetail()
      if (detailDialogVisible.value && selectedDataType.value) {
        await handleViewDetail(selectedDataType.value)
      }
    } else {
      ElMessage.error(response.message)
    }
  } catch (error: any) {
    ElMessage.error(`重试失败: ${error.message || '未知错误'}`)
  } finally {
    retrying.value = false
  }
}

/**
 * 从错误对话框重试
 */
const handleRetryFromError = async () => {
  if (!selectedError.value) return

  await handleRetry(
    selectedError.value.sourceId,
    selectedError.value.dataType
  )

  if (errorDialogVisible.value) {
    await handleViewDetail(selectedDataType.value!)
  }
}

/**
 * 导出日志
 */
const handleExportLog = async () => {
  if (!selectedDataTypeDetail) return

  try {
    exporting.value = true
    const history = await marketDataApi.getHistory(
      activeMarket.value,
      selectedDataTypeDetail.dataType,
      timeRange.value === '1h' ? 1 : timeRange.value === '24h' ? 24 : 168
    )

    // 生成 CSV 内容
    const csvContent = [
      '时间,事件类型,描述,原状态,新状态,原数据源,新数据源',
      ...history.events.map(e =>
        `${e.timestamp},${e.eventType},${e.description},${e.fromStatus || ''},${e.toStatus || ''},${e.fromSource || ''},${e.toSource || ''}`
      )
    ].join('\n')

    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `data_source_history_${selectedDataTypeDetail.dataType}_${Date.now()}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('日志导出成功')
  } catch (error: any) {
    ElMessage.error(`导出失败: ${error.message || '未知错误'}`)
  } finally {
    exporting.value = false
  }
}

/**
 * 复制错误信息
 */
const handleCopyError = () => {
  if (!selectedError.value) return

  const errorText = JSON.stringify(selectedError.value.error, null, 2)
  navigator.clipboard.writeText(errorText).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

/**
 * 启动定时刷新
 */
const startRefreshTimer = () => {
  refreshTimer = setInterval(() => {
    fetchMarketDetail()
  }, 30000) // 每30秒自动刷新一次
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
onMounted(async () => {
  await fetchDashboardOverview()
  await fetchMarketDetail()
  startRefreshTimer()

  // TODO: 从用户信息判断是否管理员
  isAdmin.value = false

  // 初始化图表
  await nextTick()
  initChart()
})

onUnmounted(() => {
  stopRefreshTimer()
  destroyChart()
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

.market-tabs {
  margin-bottom: 20px;

  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }
}

.data-types-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.data-type-card {
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--el-box-shadow-light);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .data-type-name {
        font-size: 16px;
        font-weight: 600;
      }
    }
  }

  .card-content {
    margin-top: 16px;
  }
}

.chart-card {
  margin-bottom: 20px;

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chart-container {
    height: 300px;
    width: 100%;
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

// 详情对话框
.detail-dialog {
  .detail-info {
    margin-bottom: 24px;
  }

  .source-section {
    margin-bottom: 32px;

    &:last-child {
      margin-bottom: 0;
    }

    .api-endpoints {
      margin-top: 16px;

      h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 错误详情对话框
.error-dialog {
  .error-details {
    .error-item {
      margin-bottom: 16px;

      .label {
        font-weight: 600;
        color: var(--el-text-color-regular);
        margin-right: 8px;
      }
    }

    .error-raw-response,
    .retry-history {
      margin-top: 24px;

      .label {
        display: block;
        font-weight: 600;
        color: var(--el-text-color-regular);
        margin-bottom: 12px;
      }

      pre {
        margin: 0;
        font-size: 12px;
        line-height: 1.6;
        max-height: 300px;
        overflow: auto;
      }
    }

    .retry-history {
      :deep(.el-timeline-item__timestamp) {
        font-size: 12px;
      }
    }
  }

  .admin-debug-info {
    margin-top: 32px;

    .debug-item {
      margin-bottom: 16px;

      .label {
        display: block;
        font-weight: 600;
        color: var(--el-text-color-regular);
        margin-bottom: 12px;
      }

      pre {
        margin: 0;
        font-size: 11px;
        line-height: 1.4;
        max-height: 400px;
        overflow: auto;
      }
    }
  }
}

.event-source-change {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
</style>
