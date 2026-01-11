<template>
  <div class="quote-detail-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon class="header-icon" :size="28">
          <TrendCharts />
        </el-icon>
        <div>
          <h2>行情数据</h2>
          <p class="description">
            查询股票历史行情数据，支持日线、周线、月线
          </p>
        </div>
      </div>
      <el-button @click="handleBack">
        <el-icon><Back /></el-icon>
        返回
      </el-button>
    </div>

    <!-- 查询表单 -->
    <el-card class="search-card">
      <el-form :model="queryForm" :inline="true" class="search-form">
        <el-form-item label="股票代码">
          <el-input
            v-model="queryForm.symbol"
            placeholder="如: 000001.SZ"
            clearable
            style="width: 150px"
          />
        </el-form-item>

        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item label="复权类型">
          <el-select v-model="queryForm.adjustType" placeholder="选择复权类型" style="width: 120px">
            <el-option label="不复权" value="" />
            <el-option label="前复权" value="qfq" />
            <el-option label="后复权" value="hfq" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计信息 -->
    <el-card v-if="quotes.length > 0" class="stats-card">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">数据条数</div>
            <div class="stat-value">{{ quotes.length }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">最新收盘</div>
            <div class="stat-value">{{ formatPrice(latestQuote.close) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">涨跌幅</div>
            <div class="stat-value" :class="getChangeClass(latestQuote.changePct)">
              {{ formatPercent(latestQuote.changePct) }}
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">数据源</div>
            <div class="stat-value">
              <el-tag type="success" size="small">{{ latestQuote.dataSource }}</el-tag>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>历史行情</span>
          <div class="header-actions">
            <el-tag type="info">{{ queryForm.symbol }}</el-tag>
            <el-button
              type="primary"
              size="small"
              @click="handleExport"
              :disabled="quotes.length === 0"
            >
              <el-icon><Download /></el-icon>
              导出
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="quotes"
        v-loading="loading"
        stripe
        height="500"
        style="width: 100%"
      >
        <el-table-column prop="trade_date" label="交易日期" width="110" fixed sortable />
        <el-table-column prop="open" label="开盘价" width="100" align="right">
          <template #default="{ row }">
            {{ formatPrice(row.open) }}
          </template>
        </el-table-column>
        <el-table-column prop="high" label="最高价" width="100" align="right">
          <template #default="{ row }">
            {{ formatPrice(row.high) }}
          </template>
        </el-table-column>
        <el-table-column prop="low" label="最低价" width="100" align="right">
          <template #default="{ row }">
            {{ formatPrice(row.low) }}
          </template>
        </el-table-column>
        <el-table-column prop="close" label="收盘价" width="100" align="right">
          <template #default="{ row }">
            {{ formatPrice(row.close) }}
          </template>
        </el-table-column>
        <el-table-column prop="change" label="涨跌额" width="100" align="right">
          <template #default="{ row }">
            <span :class="getChangeClass(row.change)">
              {{ formatPrice(row.change) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="change_pct" label="涨跌幅(%)" width="110" align="right">
          <template #default="{ row }">
            <span :class="getChangeClass(row.changePct)">
              {{ formatPercent(row.changePct) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="volume" label="成交量" width="120" align="right">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="成交额(万)" width="120" align="right">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="data_source" label="数据源" width="100">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.data_source }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { TrendCharts, Back, Search, RefreshLeft, Download } from '@element-plus/icons-vue'
import marketDataApi from '../api/marketDataApi'
import type { Quote } from '../types'

const router = useRouter()
const route = useRoute()

// 查询表单
const queryForm = reactive({
  symbol: '',
  startDate: '',
  endDate: '',
  adjustType: ''
})

// 日期范围
const dateRange = ref<[string, string]>([])

// 状态
const loading = ref(false)
const quotes = ref<Quote[]>([])

// 最新行情
const latestQuote = computed(() => {
  return quotes.value.length > 0 ? quotes.value[0] : ({} as Quote)
})

/**
 * 格式化价格
 */
const formatPrice = (price?: number) => {
  if (price === undefined || price === null) return '-'
  return price.toFixed(2)
}

/**
 * 格式化百分比
 */
const formatPercent = (pct?: number) => {
  if (pct === undefined || pct === null) return '-'
  return `${pct > 0 ? '+' : ''}${pct.toFixed(2)}%`
}

/**
 * 格式化成交量
 */
const formatVolume = (volume: number) => {
  if (volume >= 100000000) {
    return `${(volume / 100000000).toFixed(2)}亿`
  } else if (volume >= 10000) {
    return `${(volume / 10000).toFixed(2)}万`
  }
  return volume.toString()
}

/**
 * 格式化成交额
 */
const formatAmount = (amount?: number) => {
  if (amount === undefined || amount === null) return '-'
  if (amount >= 10000) {
    return `${(amount / 10000).toFixed(2)}亿`
  }
  return amount.toFixed(2)
}

/**
 * 获取涨跌样式类
 */
const getChangeClass = (value?: number) => {
  if (value === undefined || value === null) return ''
  if (value > 0) return 'text-up'
  if (value < 0) return 'text-down'
  return ''
}

/**
 * 查询行情数据
 */
const fetchQuotes = async () => {
  if (!queryForm.symbol) {
    ElMessage.warning('请输入股票代码')
    return
  }

  try {
    loading.value = true
    const data = await marketDataApi.queryQuotes({
      symbol: queryForm.symbol,
      start_date: queryForm.startDate,
      end_date: queryForm.endDate
    })
    quotes.value = data
    ElMessage.success(`成功加载 ${data.length} 条行情数据`)
  } catch (error: any) {
    ElMessage.error(`加载失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  if (dateRange.value && dateRange.value.length === 2) {
    queryForm.startDate = dateRange.value[0].replace(/-/g, '')
    queryForm.endDate = dateRange.value[1].replace(/-/g, '')
  }
  fetchQuotes()
}

/**
 * 重置
 */
const handleReset = () => {
  queryForm.symbol = route.query.symbol as string || ''
  queryForm.startDate = ''
  queryForm.endDate = ''
  queryForm.adjustType = ''
  dateRange.value = []
  pagination.page = 1
}

/**
 * 导出
 */
const handleExport = () => {
  // TODO: 实现导出功能
  ElMessage.info('导出功能开发中...')
}

/**
 * 返回
 */
const handleBack = () => {
  router.back()
}

// 初始化
onMounted(() => {
  // 从路由参数获取股票代码
  if (route.query.symbol) {
    queryForm.symbol = route.query.symbol as string
    fetchQuotes()
  }
})
</script>

<style scoped lang="scss">
.quote-detail-view {
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

.search-card {
  margin-bottom: 20px;

  .search-form {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
}

.stats-card {
  margin-bottom: 20px;

  .stat-item {
    text-align: center;
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 8px;

    .stat-label {
      font-size: 14px;
      color: var(--el-text-color-secondary);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }
}

.table-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }
}

.text-up {
  color: #f56c6c;
  font-weight: 600;
}

.text-down {
  color: #67c23a;
  font-weight: 600;
}
</style>
