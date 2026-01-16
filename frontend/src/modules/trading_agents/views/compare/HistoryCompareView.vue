<template>
  <div class="history-compare-view">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2>历史对比分析</h2>
      <div class="header-actions">
        <el-button
          type="primary"
          :icon="Download"
          :loading="exporting"
          @click="exportReport"
        >
          导出报告
        </el-button>
      </div>
    </div>

    <!-- 股票选择区域 -->
    <el-card
      class="search-card"
      shadow="never"
    >
      <el-form
        :model="searchForm"
        inline
        @submit.prevent="handleSearch"
      >
        <el-form-item label="股票代码">
          <el-input
            v-model="searchForm.stock_code"
            placeholder="请输入股票代码"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button
                :icon="Search"
                @click="handleSearch"
              />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="股票名称">
          <el-input
            v-model="stockName"
            placeholder="自动显示"
            disabled
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="handleSearch"
          >
            搜索
          </el-button>
          <el-button @click="handleReset">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 时间范围选择 -->
    <el-card
      class="time-range-card"
      shadow="never"
    >
      <template #header>
        <span>时间范围</span>
      </template>
      <el-radio-group
        v-model="timeRangeType"
        @change="handleTimeRangeChange"
      >
        <el-radio-button label="3m">
          最近 3 个月
        </el-radio-button>
        <el-radio-button label="6m">
          最近 6 个月
        </el-radio-button>
        <el-radio-button label="12m">
          最近 12 个月
        </el-radio-button>
        <el-radio-button label="custom">
          自定义
        </el-radio-button>
      </el-radio-group>
      <el-date-picker
        v-if="timeRangeType === 'custom'"
        v-model="customDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        style="margin-left: 20px"
        @change="handleDateRangeChange"
      />
    </el-card>

    <!-- 对比维度选择 -->
    <el-card
      class="dimension-card"
      shadow="never"
    >
      <template #header>
        <span>对比维度</span>
      </template>
      <el-checkbox-group v-model="selectedDimensions">
        <el-checkbox label="recommendation">
          推荐结果变化
        </el-checkbox>
        <el-checkbox label="risk">
          风险等级变化
        </el-checkbox>
        <el-checkbox label="price">
          目标价格变化
        </el-checkbox>
        <el-checkbox label="accuracy">
          准确率统计
        </el-checkbox>
      </el-checkbox-group>
    </el-card>

    <!-- 加载状态 -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <el-skeleton
        :rows="5"
        animated
      />
    </div>

    <!-- 内容区域 -->
    <div v-else-if="hasData">
      <!-- 推荐结果趋势图 -->
      <el-card
        v-if="selectedDimensions.includes('recommendation')"
        class="chart-card"
        shadow="never"
      >
        <template #header>
          <span>推荐结果趋势</span>
        </template>
        <div
          ref="recommendationChartRef"
          class="chart-container"
        />
      </el-card>

      <!-- 目标价格变化图 -->
      <el-card
        v-if="selectedDimensions.includes('price')"
        class="chart-card"
        shadow="never"
      >
        <template #header>
          <span>目标价格变化</span>
        </template>
        <div
          ref="priceChartRef"
          class="chart-container"
        />
      </el-card>

      <!-- 风险等级变化图 -->
      <el-card
        v-if="selectedDimensions.includes('risk')"
        class="chart-card"
        shadow="never"
      >
        <template #header>
          <span>风险等级变化</span>
        </template>
        <div
          ref="riskChartRef"
          class="chart-container"
        />
      </el-card>

      <!-- 准确率统计 -->
      <el-card
        v-if="selectedDimensions.includes('accuracy')"
        class="accuracy-card"
        shadow="never"
      >
        <template #header>
          <span>准确率统计</span>
        </template>
        <div class="accuracy-stats">
          <el-statistic
            title="总分析次数"
            :value="totalAnalysisCount"
          />
          <el-statistic
            title="准确次数"
            :value="accurateCount"
          >
            <template #suffix>
              <span class="accuracy-percent">({{ accuracyPercent }}%)</span>
            </template>
          </el-statistic>
          <el-statistic
            title="不准确次数"
            :value="inaccurateCount"
          />
        </div>
        <div
          ref="accuracyChartRef"
          class="chart-container"
        />
      </el-card>

      <!-- 分析历史列表 -->
      <el-card
        class="history-list-card"
        shadow="never"
      >
        <template #header>
          <span>分析历史</span>
        </template>
        <el-table
          :data="historyList"
          stripe
          style="width: 100%"
        >
          <el-table-column
            prop="created_at"
            label="分析日期"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="final_recommendation"
            label="推荐"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getRecommendationTagType(row.final_recommendation)">
                {{ getRecommendationLabel(row.final_recommendation) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="risk_level"
            label="风险"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getRiskTagType(row.risk_level)">
                {{ getRiskLabel(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="buy_price"
            label="买入价"
            width="100"
          >
            <template #default="{ row }">
              {{ row.buy_price ? `¥${row.buy_price}` : '-' }}
            </template>
          </el-table-column>
          <el-table-column
            prop="sell_price"
            label="卖出价"
            width="100"
          >
            <template #default="{ row }">
              {{ row.sell_price ? `¥${row.sell_price}` : '-' }}
            </template>
          </el-table-column>
          <el-table-column
            label="准确"
            width="80"
          >
            <template #default="{ row }">
              <el-icon
                v-if="row.accurate === true"
                color="#67C23A"
                :size="20"
              >
                <CircleCheck />
              </el-icon>
              <el-icon
                v-else-if="row.accurate === false"
                color="#F56C6C"
                :size="20"
              >
                <CircleClose />
              </el-icon>
              <span
                v-else
                class="text-gray"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="150"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                @click="viewDetail(row)"
              >
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="请选择股票并搜索"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Download,
  Search,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { taskApi } from '../../api'
import type { AnalysisTask } from '../../types'

const router = useRouter()

// 表单数据
const searchForm = ref({
  stock_code: ''
})

const stockName = ref('')
const timeRangeType = ref<'3m' | '6m' | '12m' | 'custom'>('3m')
const customDateRange = ref<[string, string] | null>(null)
const selectedDimensions = ref<string[]>(['recommendation', 'risk', 'price', 'accuracy'])

// 状态
const loading = ref(false)
const exporting = ref(false)
const historyList = ref<AnalysisTask[]>([])

// 图表引用
const recommendationChartRef = ref<HTMLElement>()
const priceChartRef = ref<HTMLElement>()
const riskChartRef = ref<HTMLElement>()
const accuracyChartRef = ref<HTMLElement>()

// 图表实例
let recommendationChart: echarts.ECharts | null = null
let priceChart: echarts.ECharts | null = null
let riskChart: echarts.ECharts | null = null
let accuracyChart: echarts.ECharts | null = null

// 计算属性
const hasData = computed(() => historyList.value.length > 0)

const totalAnalysisCount = computed(() => historyList.value.length)

const accurateCount = computed(() =>
  historyList.value.filter(t => t.accurate === true).length
)

const inaccurateCount = computed(() =>
  historyList.value.filter(t => t.accurate === false).length
)

const accuracyPercent = computed(() => {
  if (totalAnalysisCount.value === 0) return 0
  return ((accurateCount.value / totalAnalysisCount.value) * 100).toFixed(1)
})

// 获取日期范围
const getDateRange = (): [string, string] => {
  const end = new Date()
  const start = new Date()

  if (timeRangeType.value === 'custom' && customDateRange.value) {
    return customDateRange.value
  }

  switch (timeRangeType.value) {
    case '3m':
      start.setMonth(start.getMonth() - 3)
      break
    case '6m':
      start.setMonth(start.getMonth() - 6)
      break
    case '12m':
      start.setFullYear(start.getFullYear() - 1)
      break
  }

  return [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0]
  ]
}

// 搜索
const handleSearch = async () => {
  if (!searchForm.value.stock_code) {
    ElMessage.warning('请输入股票代码')
    return
  }

  loading.value = true
  try {
    const [startDate, endDate] = getDateRange()

    const result = await taskApi.listTasks({
      stock_code: searchForm.value.stock_code,
      limit: 100,
      offset: 0
    })

    // 过滤日期范围
    let tasks = result.tasks || []
    if (startDate && endDate) {
      tasks = tasks.filter(task => {
        const taskDate = new Date(task.created_at)
        return taskDate >= new Date(startDate) && taskDate <= new Date(endDate)
      })
    }

    // 按日期倒序
    tasks.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )

    historyList.value = tasks

    // TODO: 获取股票名称
    // stockName.value = await getStockName(searchForm.value.stock_code)

    // 渲染图表
    await nextTick()
    renderCharts()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取历史数据失败')
  } finally {
    loading.value = false
  }
}

// 重置
const handleReset = () => {
  searchForm.value.stock_code = ''
  stockName.value = ''
  timeRangeType.value = '3m'
  customDateRange.value = null
  historyList.value = []
  destroyCharts()
}

// 时间范围变化
const handleTimeRangeChange = () => {
  if (searchForm.value.stock_code) {
    handleSearch()
  }
}

// 日期范围变化
const handleDateRangeChange = () => {
  if (searchForm.value.stock_code) {
    handleSearch()
  }
}

// 渲染图表
const renderCharts = () => {
  if (!hasData.value) return

  if (selectedDimensions.value.includes('recommendation')) {
    renderRecommendationChart()
  }
  if (selectedDimensions.value.includes('price')) {
    renderPriceChart()
  }
  if (selectedDimensions.value.includes('risk')) {
    renderRiskChart()
  }
  if (selectedDimensions.value.includes('accuracy')) {
    renderAccuracyChart()
  }
}

// 推荐结果趋势图
const renderRecommendationChart = () => {
  if (!recommendationChartRef.value) return

  if (!recommendationChart) {
    recommendationChart = echarts.init(recommendationChartRef.value)
  }

  // 数据准备（按时间正序）
  const data = [...historyList.value].reverse()

  const dates = data.map(t => formatDate(t.created_at))
  const recommendations = data.map(t => {
    const map: Record<string, number> = {
      'STRONG_BUY': 5,
      'BUY': 4,
      'HOLD': 3,
      'SELL': 2,
      'STRONG_SELL': 1
    }
    return map[t.final_recommendation || ''] || 3
  })

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 6,
      axisLabel: {
        formatter: (value: number) => {
          const map: Record<number, string> = {
            5: '强烈买入',
            4: '买入',
            3: '持有',
            2: '卖出',
            1: '强烈卖出'
          }
          return map[value] || ''
        }
      }
    },
    series: [{
      data: recommendations,
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(64, 158, 255, 0.5)'
          }, {
            offset: 1, color: 'rgba(64, 158, 255, 0.1)'
          }]
        }
      }
    }]
  }

  recommendationChart.setOption(option)
}

// 目标价格变化图
const renderPriceChart = () => {
  if (!priceChartRef.value) return

  if (!priceChart) {
    priceChart = echarts.init(priceChartRef.value)
  }

  const data = [...historyList.value].reverse()

  const dates = data.map(t => formatDate(t.created_at))
  const buyPrices = data.map(t => t.buy_price || null)
  const sellPrices = data.map(t => t.sell_price || null)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['买入价', '卖出价']
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '价格 (元)'
    },
    series: [
      {
        name: '买入价',
        type: 'line',
        data: buyPrices,
        itemStyle: { color: '#67C23A' }
      },
      {
        name: '卖出价',
        type: 'line',
        data: sellPrices,
        itemStyle: { color: '#F56C6C' }
      }
    ]
  }

  priceChart.setOption(option)
}

// 风险等级变化图
const renderRiskChart = () => {
  if (!riskChartRef.value) return

  if (!riskChart) {
    riskChart = echarts.init(riskChartRef.value)
  }

  const data = [...historyList.value].reverse()

  const dates = data.map(t => formatDate(t.created_at))
  const risks = data.map(t => {
    const map: Record<string, number> = {
      'LOW': 1,
      'MEDIUM': 2,
      'HIGH': 3
    }
    return map[t.risk_level || ''] || 2
  })

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 4,
      axisLabel: {
        formatter: (value: number) => {
          const map: Record<number, string> = {
            3: '高风险',
            2: '中风险',
            1: '低风险'
          }
          return map[value] || ''
        }
      }
    },
    series: [{
      data: risks,
      type: 'bar',
      itemStyle: {
        color: (params: any) => {
          const colors = ['#67C23A', '#E6A23C', '#F56C6C']
          return colors[params.data - 1] || '#909399'
        }
      }
    }]
  }

  riskChart.setOption(option)
}

// 准确率图表
const renderAccuracyChart = () => {
  if (!accuracyChartRef.value) return

  if (!accuracyChart) {
    accuracyChart = echarts.init(accuracyChartRef.value)
  }

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '准确率',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {d}%'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        data: [
          { value: accurateCount.value, name: '准确', itemStyle: { color: '#67C23A' } },
          { value: inaccurateCount.value, name: '不准确', itemStyle: { color: '#F56C6C' } }
        ]
      }
    ]
  }

  accuracyChart.setOption(option)
}

// 销毁图表
const destroyCharts = () => {
  recommendationChart?.dispose()
  priceChart?.dispose()
  riskChart?.dispose()
  accuracyChart?.dispose()
  recommendationChart = null
  priceChart = null
  riskChart = null
  accuracyChart = null
}

// 查看详情
const viewDetail = (task: AnalysisTask) => {
  router.push({
    name: 'AnalysisDetail',
    params: { taskId: task.id }
  })
}

// 导出报告
const exportReport = async () => {
  if (!hasData.value) {
    ElMessage.warning('暂无数据可导出')
    return
  }

  exporting.value = true
  try {
    // TODO: 实现导出功能
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('报告导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

// 获取推荐标签
const getRecommendationLabel = (value: string | undefined) => {
  const map: Record<string, string> = {
    'STRONG_BUY': '强烈买入',
    'BUY': '买入',
    'HOLD': '持有',
    'SELL': '卖出',
    'STRONG_SELL': '强烈卖出'
  }
  return map[value || ''] || '-'
}

// 获取推荐标签类型
const getRecommendationTagType = (value: string | undefined) => {
  const map: Record<string, any> = {
    'STRONG_BUY': 'danger',
    'BUY': 'success',
    'HOLD': 'info',
    'SELL': 'warning',
    'STRONG_SELL': 'danger'
  }
  return map[value || ''] || ''
}

// 获取风险标签
const getRiskLabel = (value: string | undefined) => {
  const map: Record<string, string> = {
    'LOW': '低',
    'MEDIUM': '中',
    'HIGH': '高'
  }
  return map[value || ''] || '-'
}

// 获取风险标签类型
const getRiskTagType = (value: string | undefined) => {
  const map: Record<string, any> = {
    'LOW': 'success',
    'MEDIUM': 'warning',
    'HIGH': 'danger'
  }
  return map[value || ''] || ''
}

// 监听窗口大小变化
const handleResize = () => {
  recommendationChart?.resize()
  priceChart?.resize()
  riskChart?.resize()
  accuracyChart?.resize()
}

// 监听维度选择变化
watch(selectedDimensions, () => {
  if (hasData.value) {
    renderCharts()
  }
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  destroyCharts()
})
</script>

<style scoped lang="scss">
.history-compare-view {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }
  }

  .search-card,
  .time-range-card,
  .dimension-card {
    margin-bottom: 20px;
  }

  .loading-container {
    padding: 40px;
  }

  .chart-card {
    margin-bottom: 20px;

    .chart-container {
      height: 400px;
    }
  }

  .accuracy-card {
    margin-bottom: 20px;

    .accuracy-stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 30px;

      .accuracy-percent {
        color: #67C23A;
        font-weight: 600;
      }
    }

    .chart-container {
      height: 300px;
    }
  }

  .history-list-card {
    .text-gray {
      color: #909399;
    }
  }
}
</style>
