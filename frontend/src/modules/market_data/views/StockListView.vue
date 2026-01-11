<template>
  <div class="stock-list-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <el-icon class="header-icon" :size="28">
          <List />
        </el-icon>
        <div>
          <h2>股票列表</h2>
          <p class="description">
            查询和管理市场股票信息，支持A股、美股、港股
          </p>
        </div>
      </div>
    </div>

    <!-- 查询表单 -->
    <el-card class="search-card">
      <el-form :model="queryForm" :inline="true" class="search-form">
        <el-form-item label="市场类型">
          <el-select v-model="queryForm.market" placeholder="选择市场" @change="handleMarketChange">
            <el-option
              v-for="item in marketOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="上市状态">
          <el-select v-model="queryForm.status" placeholder="选择状态">
            <el-option label="全部" value="" />
            <el-option label="上市" value="L" />
            <el-option label="退市" value="D" />
            <el-option label="暂停" value="P" />
            <el-option label="IPO" value="I" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词">
          <el-input
            v-model="queryForm.keyword"
            placeholder="股票代码/名称"
            clearable
            style="width: 200px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
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

    <!-- 数据表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>股票列表</span>
          <div class="header-actions">
            <el-tag type="info">共 {{ filteredStocks.length }} 只股票</el-tag>
            <el-button
              type="primary"
              size="small"
              @click="handleExport"
              :disabled="filteredStocks.length === 0"
            >
              <el-icon><Download /></el-icon>
              导出
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedStocks"
        v-loading="loading"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        style="width: 100%"
      >
        <el-table-column prop="symbol" label="股票代码" width="120" fixed />
        <el-table-column prop="name" label="股票名称" width="150" />
        <el-table-column prop="market" label="市场" width="80">
          <template #default="{ row }">
            <el-tag :type="getMarketTagType(row.market)" size="small">
              {{ MarketTypeLabels[row.market] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="100">
          <template #default="{ row }">
            {{ ExchangeLabels[row.exchange] || row.exchange }}
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" width="120" show-overflow-tooltip />
        <el-table-column prop="sector" label="板块" width="120" show-overflow-tooltip />
        <el-table-column prop="listing_date" label="上市日期" width="110" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ StockStatusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="data_source" label="数据源" width="100">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.data_source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="handleViewQuotes(row)"
            >
              查看行情
            </el-button>
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="handleViewFinancials(row)"
            >
              财务数据
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="filteredStocks.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { List, Search, RefreshLeft, Download } from '@element-plus/icons-vue'
import marketDataApi from '../api/marketDataApi'
import { MarketType, StockStatus, MarketTypeLabels, StockStatusLabels, ExchangeLabels, type StockInfo, type QueryForm } from '../types'

const router = useRouter()

// 查询表单
const queryForm = reactive<QueryForm>({
  symbol: '',
  market: MarketType.A_STOCK,
  startDate: '',
  endDate: ''
})

// 市场选项
const marketOptions = [
  { label: 'A股', value: MarketType.A_STOCK },
  { label: '美股', value: MarketType.US_STOCK },
  { label: '港股', value: MarketType.HK_STOCK }
]

// 状态
const loading = ref(false)
const stocks = ref<StockInfo[]>([])

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0
})

// 过滤后的股票列表
const filteredStocks = computed(() => {
  let result = stocks.value

  // 关键词过滤
  if (queryForm.symbol) {
    const keyword = queryForm.symbol.toLowerCase()
    result = result.filter(stock =>
      stock.symbol.toLowerCase().includes(keyword) ||
      stock.name.toLowerCase().includes(keyword)
    )
  }

  return result
})

// 当前页的股票列表
const paginatedStocks = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  return filteredStocks.value.slice(start, end)
})

/**
 * 获取市场标签类型
 */
const getMarketTagType = (market: MarketType) => {
  const typeMap: Record<MarketType, any> = {
    [MarketType.A_STOCK]: 'danger',
    [MarketType.US_STOCK]: 'warning',
    [MarketType.HK_STOCK]: 'success'
  }
  return typeMap[market] || ''
}

/**
 * 获取状态标签类型
 */
const getStatusTagType = (status: StockStatus) => {
  const typeMap: Record<StockStatus, any> = {
    [StockStatus.LISTED]: 'success',
    [StockStatus.DELISTED]: 'danger',
    [StockStatus.SUSPENDED]: 'warning',
    [StockStatus.IPO]: 'info'
  }
  return typeMap[status] || ''
}

/**
 * 查询股票列表
 */
const fetchStockList = async () => {
  try {
    loading.value = true
    const data = await marketDataApi.getStockList({
      market: queryForm.market,
      status: queryForm.startDate || 'L'
    })
    stocks.value = data
    ElMessage.success(`成功加载 ${data.length} 只股票`)
  } catch (error: any) {
    ElMessage.error(`加载失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/**
 * 市场变更
 */
const handleMarketChange = () => {
  pagination.page = 1
  fetchStockList()
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  fetchStockList()
}

/**
 * 重置
 */
const handleReset = () => {
  queryForm.symbol = ''
  queryForm.startDate = ''
  pagination.page = 1
  fetchStockList()
}

/**
 * 导出
 */
const handleExport = () => {
  // TODO: 实现导出功能
  ElMessage.info('导出功能开发中...')
}

/**
 * 行点击
 */
const handleRowClick = (row: StockInfo) => {
  handleViewQuotes(row)
}

/**
 * 查看行情
 */
const handleViewQuotes = (row: StockInfo) => {
  router.push({
    name: 'MarketDataQuotes',
    query: { symbol: row.symbol, market: row.market }
  })
}

/**
 * 查看财务数据
 */
const handleViewFinancials = (row: StockInfo) => {
  router.push({
    name: 'MarketDataFinancials',
    query: { symbol: row.symbol }
  })
  ElMessage.info('财务数据页面开发中...')
}

/**
 * 分页大小变更
 */
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
}

/**
 * 页码变更
 */
const handlePageChange = (page: number) => {
  pagination.page = page
}

// 初始化
onMounted(() => {
  fetchStockList()
})
</script>

<style scoped lang="scss">
.stock-list-view {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;

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

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}

:deep(.el-table) {
  cursor: pointer;

  .el-table__row:hover {
    background-color: var(--el-fill-color-light);
  }
}
</style>
