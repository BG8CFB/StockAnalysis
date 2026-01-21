<template>
  <div class="data-source-health-view">
    <!-- 页面标题和刷新按钮 -->
    <div class="page-header">
      <h2>数据源状态监控</h2>
      <el-button
        :loading="loading"
        size="small"
        @click="handleRefresh"
      >
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 市场标签页 -->
    <el-tabs
      v-model="activeMarket"
      class="market-tabs"
      @tab-change="handleMarketChange"
    >
      <el-tab-pane
        label="A股"
        :name="MarketType.A_STOCK"
      />
      <el-tab-pane
        label="美股"
        :name="MarketType.US_STOCK"
      />
      <el-tab-pane
        label="港股"
        :name="MarketType.HK_STOCK"
      />
    </el-tabs>

    <!-- 表格布局 -->
    <el-table
      :data="marketDetail?.data_types || []"
      stripe
      size="small"
      class="status-table"
    >
      <el-table-column
        label="数据类型"
        prop="data_type_name"
        width="110"
      />

      <el-table-column
        label="当前数据源"
        width="140"
      >
        <template #default="{ row }">
          <div class="source-cell">
            <span>{{ dataSourceDisplayName(row.current_source.source_id) }}</span>
            <el-tag
              v-if="row.is_fallback"
              type="warning"
              size="small"
              class="fallback-tag"
            >
              已降级
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column
        label="状态"
        width="90"
        align="center"
      >
        <template #default="{ row }">
          <el-tag
            v-if="row.current_source.status"
            :type="getDataSourceStatusTagType(row.current_source.status)"
            size="small"
          >
            {{ dataSourceStatusLabel(row.current_source.status) }}
          </el-tag>
          <span v-else class="status-placeholder">-</span>
        </template>
      </el-table-column>

      <el-table-column
        label="检查时间"
        width="130"
      >
        <template #default="{ row }">
          <span class="time-info">
            {{ row.current_source.last_check_relative || '-' }}
            <span
              v-if="row.current_source.response_time_ms"
              class="response-time"
            >
              {{ row.current_source.response_time_ms }}ms
            </span>
          </span>
        </template>
      </el-table-column>

      <el-table-column
        label="备注/失败原因"
        min-width="200"
      >
        <template #default="{ row }">
          <div class="note-cell">
            <!-- 已降级状态 -->
            <span
              v-if="row.is_fallback"
              class="fallback-info"
            >
              <el-tag
                type="warning"
                size="small"
              >已降级</el-tag>
              {{ row.fallback_reason || '使用备用数据源' }}
            </span>
            <!-- 错误信息 -->
            <span
              v-else-if="row.current_source.error_message"
              class="error-message"
            >
              <el-tag
                type="danger"
                size="small"
              >异常</el-tag>
              {{ row.current_source.error_message }}
            </span>
            <!-- 正常状态 -->
            <span
              v-else-if="row.current_source.status === 'healthy'"
              class="normal-status"
            >
              <el-tag
                type="success"
                size="small"
              >正常</el-tag>
              运行正常
            </span>
            <!-- 未检查或等待 -->
            <span
              v-else
              class="waiting-status"
            >
              等待检查
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column
        label="操作"
        width="140"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            v-if="row.can_retry"
            type="primary"
            link
            size="small"
            @click="handleRetry(row.current_source.source_id, row.data_type)"
          >
            重试主源
          </el-button>
          <el-button
            type="primary"
            link
            size="small"
            @click="handleViewDetail(row)"
          >
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`${selectedDataType?.data_type_name} - 详细信息`"
      width="800px"
      destroy-on-close
    >
      <div
        v-if="selectedDataTypeDetail"
        class="detail-dialog"
      >
        <!-- 基本信息 -->
        <div class="detail-info">
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="数据类型">
              {{ selectedDataTypeDetail.data_type_name }}
            </el-descriptions-item>
            <el-descriptions-item label="市场">
              {{ MarketTypeName[selectedDataTypeDetail.market] }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 数据源详情列表 -->
        <div
          v-for="source in selectedDataTypeDetail.sources"
          :key="source.source_id"
          class="source-section"
        >
          <el-divider>
            <div class="source-divider">
              <el-tag
                :type="getDataSourceStatusTagType(source.status)"
                size="large"
              >
                {{ dataSourceDisplayName(source.source_name) }}
              </el-tag>
              <span class="source-status">
                {{ source.status ? dataSourceStatusLabel(source.status) : '未检查' }}
              </span>
              <el-tag
                v-if="source.note === '当前使用'"
                type="success"
                size="small"
              >
                当前使用
              </el-tag>
            </div>
          </el-divider>

          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="优先级">
              主数据源
            </el-descriptions-item>
            <el-descriptions-item
              v-if="source.last_check"
              label="最后检查"
            >
              {{ formatTime(source.last_check) }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="source.response_time_ms"
              label="响应时间"
            >
              {{ source.response_time_ms }} ms
            </el-descriptions-item>
            <el-descriptions-item
              v-if="source.avg_response_time_ms"
              label="平均响应时间"
            >
              {{ source.avg_response_time_ms }} ms
            </el-descriptions-item>
            <el-descriptions-item label="失败次数">
              <el-tag
                :type="source.failure_count > 0 ? 'danger' : 'success'"
                size="small"
              >
                {{ source.failure_count }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item
              v-if="source.note"
              label="备注"
            >
              <el-text type="info">
                {{ source.note }}
              </el-text>
            </el-descriptions-item>
          </el-descriptions>

          <!-- API接口明细 -->
          <div
            v-if="source.api_endpoints && source.api_endpoints.length > 0"
            class="api-endpoints"
          >
            <h4>接口明细</h4>
            <el-table
              :data="source.api_endpoints"
              border
              size="small"
            >
              <el-table-column
                prop="endpoint_name_cn"
                label="接口名称"
                width="200"
              />
              <el-table-column
                prop="endpoint_name"
                label="接口代码"
                width="180"
              />
              <el-table-column
                label="状态"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag
                    :type="getDataSourceStatusTagType(row.status)"
                    size="small"
                  >
                    {{ dataSourceStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                label="失败次数"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag
                    :type="row.failure_count > 0 ? 'danger' : 'success'"
                    size="small"
                  >
                    {{ row.failure_count }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                label="最后检查"
                min-width="150"
              >
                <template #default="{ row }">
                  {{ row.last_check ? formatTime(row.last_check) : '-' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 最近状态变化 -->
        <el-divider>最近状态变化</el-divider>

        <el-timeline>
          <el-timeline-item
            v-for="(event, index) in selectedDataTypeDetail.recent_events"
            :key="index"
            :timestamp="formatTime(event.timestamp)"
            placement="top"
          >
            <el-card>
              <p>{{ event.description }}</p>
              <div
                v-if="event.from_source && event.to_source"
                class="event-source-change"
              >
                <el-tag size="small">
                  {{ dataSourceDisplayName(event.from_source) }}
                </el-tag>
                <el-icon><Right /></el-icon>
                <el-tag
                  type="success"
                  size="small"
                >
                  {{ dataSourceDisplayName(event.to_source) }}
                </el-tag>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>

        <el-timeline v-if="!selectedDataTypeDetail.recent_events || selectedDataTypeDetail.recent_events.length === 0">
          <el-timeline-item placement="top">
            <el-card>
              <p>暂无状态变化记录</p>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailDialogVisible = false">
            关闭
          </el-button>
          <el-button
            type="primary"
            :loading="exporting"
            @click="handleExportLog"
          >
            <el-icon><Download /></el-icon>
            导出日志
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Right } from '@element-plus/icons-vue'
import marketDataApi from '../api/marketDataApi'
import {
  MarketType,
  MarketTypeName,
  DataSourceStatus,
  DataSourceStatusLabels,
  DataSourceStatusTagType,
  DataSourceDisplayName,
  NextUpdateMap,
  type MarketDetail,
  type DataTypeStatus,
  type DataTypeDetail
} from '../types'

// 状态
const loading = ref(false)
const activeMarket = ref<MarketType>(MarketType.A_STOCK)
const marketDetail = ref<MarketDetail | null>(null)

// 对话框
const detailDialogVisible = ref(false)
const selectedDataType = ref<DataTypeStatus | null>(null)
const selectedDataTypeDetail = ref<DataTypeDetail | null>(null)
const exporting = ref(false)
const retrying = ref(false)

// 定时刷新
let refreshTimer: any = null

/**
 * 获取数据源显示名称
 */
const dataSourceDisplayName = (sourceIdOrName: string) => {
  return DataSourceDisplayName[sourceIdOrName] || sourceIdOrName
}

/**
 * 获取数据源状态标签
 */
const dataSourceStatusLabel = (status: DataSourceStatus | null) => {
  if (!status) return '-'
  return DataSourceStatusLabels[status] || status
}

/**
 * 获取数据源状态标签类型
 */
const getDataSourceStatusTagType = (status: DataSourceStatus | null) => {
  if (!status) return 'info'
  return DataSourceStatusTagType[status] || ''
}

/**
 * 格式化时间
 */
const formatTime = (timeStr?: string | null) => {
  if (!timeStr) return '-'
  return timeStr
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
 * 查看详情
 */
const handleViewDetail = async (dataType: DataTypeStatus) => {
  selectedDataType.value = dataType
  try {
    const detail = await marketDataApi.getDataTypeDetail(
      activeMarket.value,
      dataType.data_type
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
 * 导出日志
 */
const handleExportLog = async () => {
  if (!selectedDataTypeDetail.value) return

  try {
    exporting.value = true
    const history = await marketDataApi.getHistory(
      activeMarket.value,
      selectedDataTypeDetail.value.data_type,
      24
    )

    // 生成 CSV 内容
    const csvContent = [
      '时间,事件类型,描述,原状态,新状态,原数据源,新数据源',
      ...history.events.map(e =>
        `${e.timestamp},${e.event_type},${e.description},${e.from_status || ''},${e.to_status || ''},${e.from_source || ''},${e.to_source || ''}`
      )
    ].join('\n')

    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `data_source_history_${selectedDataTypeDetail.value.data_type}_${Date.now()}.csv`)
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
  await fetchMarketDetail()
  startRefreshTimer()
})

onUnmounted(() => {
  stopRefreshTimer()
})
</script>

<style scoped lang="scss">
.data-source-health-view {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
}

.market-tabs {
  margin-bottom: 12px;

  :deep(.el-tabs__header) {
    margin-bottom: 12px;
  }
}

// 表格样式
.status-table {
  .source-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    .current-tag {
      flex-shrink: 0;
    }
  }

  .status-placeholder {
    color: var(--el-text-color-placeholder);
    font-size: 12px;
  }

  .time-info {
    font-size: 12px;
    color: var(--el-text-color-regular);

    .response-time {
      color: var(--el-color-success);
      margin-left: 8px;
    }
  }

  .note-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .error-message {
      font-size: 12px;
      color: var(--el-color-danger);

      .el-tag {
        margin-right: 4px;
      }
    }

    .fallback-info {
      font-size: 12px;
      color: var(--el-color-warning);

      .el-tag {
        margin-right: 4px;
      }
    }

    .normal-status {
      font-size: 12px;
    }

    .waiting-status {
      font-size: 12px;
      color: var(--el-text-color-secondary);
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

    .source-divider {
      display: flex;
      align-items: center;
      gap: 12px;

      .source-status {
        font-size: 14px;
        color: var(--el-text-color-regular);
      }
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

.event-source-change {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
</style>
