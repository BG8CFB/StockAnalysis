<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <h1>仪表盘</h1>
      <p>欢迎回来，{{ userStore.user?.username }}！</p>
    </div>

    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid">
      <n-gi>
        <n-card class="stat-card">
          <n-statistic label="总用户数" :value="dashboardData.system_stats?.total_users || 0">
            <template #prefix>
              <n-icon><UserOutlined /></n-icon>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card class="stat-card">
          <n-statistic label="活跃用户" :value="dashboardData.system_stats?.active_users || 0">
            <template #prefix>
              <n-icon><PeopleOutline /></n-icon>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card class="stat-card">
          <n-statistic label="分析股票数" :value="dashboardData.system_stats?.total_stocks_analyzed || 0">
            <template #prefix>
              <n-icon><TrendingUpOutline /></n-icon>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card class="stat-card">
          <n-statistic label="今日分析请求" :value="dashboardData.system_stats?.analysis_requests_today || 0">
            <template #prefix>
              <n-icon><BarChartOutline /></n-icon>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :cols="3" :x-gap="16" :y-gap="16" class="content-grid">
      <!-- 投资组合概览 -->
      <n-gi :span="2">
        <n-card title="投资组合概览" class="portfolio-card">
          <div class="portfolio-summary">
            <div class="portfolio-value">
              <span class="label">总价值</span>
              <span class="value">¥{{ formatNumber(dashboardData.portfolio_summary?.total_value || 0) }}</span>
            </div>
            <div class="portfolio-change">
              <n-tag
                :type="getChangeType(dashboardData.portfolio_summary?.daily_change || 0)"
                size="small"
              >
                {{ dashboardData.portfolio_summary?.daily_change > 0 ? '+' : '' }}
                {{ formatNumber(dashboardData.portfolio_summary?.daily_change || 0) }}
                ({{ dashboardData.portfolio_summary?.daily_change_percent?.toFixed(2) || 0 }}%)
              </n-tag>
            </div>
          </div>

          <!-- 简单的图表占位符 -->
          <div class="chart-placeholder">
            <div class="chart-title">投资组合趋势</div>
            <div class="chart-content">
              这里将显示投资组合价值趋势图表
            </div>
          </div>
        </n-card>
      </n-gi>

      <!-- 最近活动 -->
      <n-gi>
        <n-card title="最近活动" class="activities-card">
          <n-list>
            <n-list-item
              v-for="activity in dashboardData.recent_activities"
              :key="activity.id"
            >
              <n-thing :title="activity.title" :description="activity.description">
                <template #header-extra>
                  <n-tag size="small" :type="getActivityType(activity.type)">
                    {{ getActivityLabel(activity.type) }}
                  </n-tag>
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
        </n-card>
      </n-gi>

      <!-- 市场概览 -->
      <n-gi>
        <n-card title="市场概览" class="market-card">
          <div class="market-status">
            <n-tag
              :type="dashboardData.market_overview?.market_status === 'open' ? 'success' : 'default'"
              size="large"
            >
              市场{{ dashboardData.market_overview?.market_status === 'open' ? '开放中' : '已关闭' }}
            </n-tag>
          </div>

          <div class="major-indices">
            <div
              v-for="index in dashboardData.market_overview?.major_indices"
              :key="index.name"
              class="index-item"
            >
              <div class="index-name">{{ index.name }}</div>
              <div class="index-value">{{ index.value.toFixed(2) }}</div>
              <n-tag
                :type="getChangeType(index.change)"
                size="small"
              >
                {{ index.change > 0 ? '+' : '' }}{{ index.change.toFixed(2) }}
                ({{ index.change_percent?.toFixed(2) }}%)
              </n-tag>
            </div>
          </div>
        </n-card>
      </n-gi>

      <!-- 热门板块 -->
      <n-gi>
        <n-card title="热门板块" class="sectors-card">
          <div class="hot-sectors">
            <div
              v-for="sector in dashboardData.market_overview?.hot_sectors"
              :key="sector.name"
              class="sector-item"
            >
              <div class="sector-name">{{ sector.name }}</div>
              <div class="sector-change">
                <n-tag :type="getChangeType(sector.change_percent)" size="small">
                  {{ sector.change_percent > 0 ? '+' : '' }}{{ sector.change_percent.toFixed(2) }}%
                </n-tag>
              </div>
              <div class="sector-stocks">{{ sector.stocks_count }} 只股票</div>
            </div>
          </div>
        </n-card>
      </n-gi>

      <!-- 通知 -->
      <n-gi>
        <n-card title="通知" class="notifications-card">
          <div class="notification-list">
            <div
              v-for="notification in notifications.slice(0, 3)"
              :key="notification.id"
              class="notification-item"
              :class="{ unread: !notification.read }"
            >
              <div class="notification-content">
                <div class="notification-title">{{ notification.title }}</div>
                <div class="notification-message">{{ notification.message }}</div>
              </div>
              <div class="notification-time">
                {{ formatTime(notification.timestamp) }}
              </div>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NGrid,
  NGi,
  NCard,
  NStatistic,
  NIcon,
  NTag,
  NList,
  NListItem,
  NThing
} from 'naive-ui'
import {
  UserOutlined,
  PeopleOutline,
  TrendingUpOutline,
  BarChartOutline
} from '@vicons/ionicons5'
import { useUserStore } from '@/modules/user_management/store'
import { httpClient } from '@/core/api/http'

const userStore = useUserStore()

// 响应式数据
const dashboardData = ref<any>({})
const notifications = ref<any[]>([])
const loading = ref(false)

// 获取仪表盘数据
async function fetchDashboardData() {
  try {
    loading.value = true
    const response = await httpClient.get('/dashboard/summary')
    dashboardData.value = response || {}
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    loading.value = false
  }
}

// 获取通知数据
async function fetchNotifications() {
  try {
    const response = await httpClient.get('/dashboard/notifications')
    notifications.value = response?.notifications || []
  } catch (error) {
    console.error('Failed to fetch notifications:', error)
  }
}

// 工具函数
function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

function getChangeType(change: number): 'success' | 'error' | 'default' {
  if (change > 0) return 'success'
  if (change < 0) return 'error'
  return 'default'
}

function getActivityType(type: string): 'info' | 'success' | 'warning' | 'error' {
  switch (type) {
    case 'analysis_completed': return 'success'
    case 'alert_triggered': return 'warning'
    case 'portfolio_update': return 'info'
    default: return 'info'
  }
}

function getActivityLabel(type: string): string {
  switch (type) {
    case 'analysis_completed': return '分析完成'
    case 'alert_triggered': return '预警'
    case 'portfolio_update': return '组合更新'
    default: return '未知'
  }
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 生命周期
onMounted(() => {
  fetchDashboardData()
  fetchNotifications()
})
</script>

<style scoped>
.dashboard {
  padding: 24px;
}

.dashboard-header {
  margin-bottom: 24px;
}

.dashboard-header h1 {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 8px;
}

.dashboard-header p {
  color: #666;
  font-size: 14px;
}

.stats-grid {
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.content-grid {
  gap: 24px;
}

.portfolio-card,
.activities-card,
.market-card,
.sectors-card,
.notifications-card {
  height: 100%;
}

.portfolio-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.portfolio-value .label {
  font-size: 14px;
  color: #666;
}

.portfolio-value .value {
  font-size: 24px;
  font-weight: bold;
  margin-left: 8px;
}

.chart-placeholder {
  height: 200px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.chart-title {
  font-weight: bold;
  margin-bottom: 8px;
}

.index-item,
.sector-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.index-item:last-child,
.sector-item:last-child {
  border-bottom: none;
}

.index-name,
.sector-name {
  font-weight: 500;
}

.index-value {
  font-size: 16px;
  font-weight: bold;
  margin: 0 16px;
}

.sector-stocks {
  font-size: 12px;
  color: #999;
}

.notification-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item.unread {
  background-color: #f9f9f9;
  border-left: 3px solid #2080f0;
  padding-left: 12px;
}

.notification-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.notification-message {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.notification-time {
  font-size: 11px;
  color: #999;
}
</style>