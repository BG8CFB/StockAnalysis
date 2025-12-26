<template>
  <div class="report-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分析报告列表</span>
          <el-button
            type="primary"
            @click="handleRefresh"
          >
            刷新
          </el-button>
        </div>
      </template>

      <div class="content">
        <div class="filters">
          <el-form
            :inline="true"
            :model="filters"
          >
            <el-form-item label="股票代码">
              <el-input
                v-model="filters.stock_code"
                placeholder="请输入股票代码"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>

            <el-form-item label="推荐操作">
              <el-select
                v-model="filters.recommendation"
                placeholder="全部"
                clearable
                @change="handleSearch"
              >
                <el-option
                  label="买入"
                  value="买入"
                />
                <el-option
                  label="卖出"
                  value="卖出"
                />
                <el-option
                  label="持有"
                  value="持有"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="风险等级">
              <el-select
                v-model="filters.risk_level"
                placeholder="全部"
                clearable
                @change="handleSearch"
              >
                <el-option
                  label="低"
                  value="low"
                />
                <el-option
                  label="中"
                  value="medium"
                />
                <el-option
                  label="高"
                  value="high"
                />
              </el-select>
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
        </div>

        <el-table
          v-loading="loading"
          :data="reports"
          style="width: 100%"
        >
          <el-table-column
            prop="stock_code"
            label="股票代码"
            width="100"
          />
          <el-table-column
            prop="recommendation"
            label="推荐操作"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getRecommendationType(row.recommendation)">
                {{ row.recommendation }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="risk_level"
            label="风险等级"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getRiskLevelType(row.risk_level)">
                {{ getRiskLevelText(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="buy_price"
            label="买入价格"
            width="100"
          />
          <el-table-column
            prop="sell_price"
            label="卖出价格"
            width="100"
          />
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="150"
          >
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="handleViewReport(row)"
              >
                查看详情
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="handleDeleteReport(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="total > 0"
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="reportDetailVisible"
      title="报告详情"
      width="80%"
    >
      <div
        v-if="currentReport"
        class="report-detail"
      >
        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="股票代码">
            {{ currentReport.stock_code }}
          </el-descriptions-item>
          <el-descriptions-item label="推荐操作">
            <el-tag :type="getRecommendationType(currentReport.recommendation)">
              {{ currentReport.recommendation }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="getRiskLevelType(currentReport.risk_level)">
              {{ getRiskLevelText(currentReport.risk_level) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="买入价格">
            {{ currentReport.buy_price }}
          </el-descriptions-item>
          <el-descriptions-item label="卖出价格">
            {{ currentReport.sell_price }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentReport.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="reports-section">
          <h4>各智能体报告</h4>
          <el-tabs v-model="activeReportTab">
            <el-tab-pane
              v-for="(report, slug) in currentReport.reports"
              :key="slug"
              :label="getAgentName(slug)"
              :name="slug"
            >
              <div class="report-content">
                {{ report }}
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reportApi } from '@modules/trading_agents/api'
import type { AnalysisReport } from '@modules/trading_agents/types'

const loading = ref(false)
const reports = ref<AnalysisReport[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const reportDetailVisible = ref(false)
const currentReport = ref<AnalysisReport | null>(null)
const activeReportTab = ref('')

const filters = reactive({
  stock_code: '',
  recommendation: '',
  risk_level: '',
})

const AGENT_NAMES: Record<string, string> = {
  market_technical: '市场技术分析师',
  market_fundamental: '市场基本面分析师',
  news_sentiment: '新闻情绪分析师',
  bull_debater: '看涨研究员',
  bear_debater: '看跌研究员',
  risk_assessor: '首席风控官',
  final_summarizer: '总结智能体',
}

onMounted(() => {
  loadReports()
})

async function loadReports() {
  try {
    loading.value = true
    const result = await reportApi.listReports({
      stock_code: filters.stock_code || undefined,
      recommendation: filters.recommendation || undefined,
      risk_level: filters.risk_level || undefined,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
    reports.value = result.reports
    total.value = result.reports.length
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '加载报告列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  loadReports()
}

function handleReset() {
  filters.stock_code = ''
  filters.recommendation = ''
  filters.risk_level = ''
  currentPage.value = 1
  loadReports()
}

function handleRefresh() {
  loadReports()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadReports()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadReports()
}

function handleViewReport(report: AnalysisReport) {
  currentReport.value = report
  if (report.reports && Object.keys(report.reports).length > 0) {
    activeReportTab.value = Object.keys(report.reports)[0]
  }
  reportDetailVisible.value = true
}

async function handleDeleteReport(report: AnalysisReport) {
  try {
    await ElMessageBox.confirm(
      `确定要删除股票 ${report.stock_code} 的分析报告吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await reportApi.deleteReport(report.id)
    ElMessage.success('删除成功')
    loadReports()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

function getRecommendationType(recommendation: string | null): string {
  const typeMap: Record<string, string> = {
    '买入': 'success',
    '卖出': 'danger',
    '持有': 'warning',
  }
  return typeMap[recommendation || ''] || 'info'
}

function getRiskLevelType(riskLevel: string | null): string {
  const typeMap: Record<string, string> = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger',
  }
  return typeMap[riskLevel || ''] || 'info'
}

function getRiskLevelText(riskLevel: string | null): string {
  const textMap: Record<string, string> = {
    'low': '低',
    'medium': '中',
    'high': '高',
  }
  return textMap[riskLevel || ''] || '-'
}

function getAgentName(slug: string): string {
  return AGENT_NAMES[slug] || slug
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('zh-CN')
}
</script>

<style scoped>
.report-list-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content {
  max-width: 1400px;
  margin: 0 auto;
}

.filters {
  margin-bottom: 20px;
}

.el-pagination {
  margin-top: 20px;
  text-align: center;
}

.report-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.reports-section {
  margin-top: 20px;
}

.reports-section h4 {
  margin-bottom: 10px;
}

.report-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
