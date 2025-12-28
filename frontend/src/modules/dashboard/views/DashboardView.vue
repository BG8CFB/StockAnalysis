<template>
  <div class="dashboard-view">
    <!-- 欢迎卡片 -->
    <div
      class="welcome-card"
      :style="{ background: gradientStyle }"
    >
      <div class="welcome-content">
        <div class="welcome-text">
          <h1 class="welcome-title">
            欢迎回来，{{ displayName }}
          </h1>
          <p class="welcome-description">
            专业 AI 驱动的股票分析平台，为您提供智能投资决策支持
          </p>
        </div>
        <div class="welcome-decoration">
          <div class="decoration-circle circle-1" />
          <div class="decoration-circle circle-2" />
          <div class="decoration-circle circle-3" />
        </div>
      </div>
    </div>

    <!-- 统计卡片网格 -->
    <div class="stats-grid">
      <!-- 关注股票 -->
      <div class="stat-card stat-card-primary">
        <div class="stat-icon">
          <el-icon :size="28">
            <TrendCharts />
          </el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            --
          </div>
          <div class="stat-label">
            关注股票
          </div>
          <div class="stat-trend">
            <el-icon class="trend-icon">
              <TrendCharts />
            </el-icon>
            <span>暂无数据</span>
          </div>
        </div>
      </div>

      <!-- AI 分析次数 -->
      <div class="stat-card stat-card-success">
        <div class="stat-icon">
          <el-icon :size="28">
            <DataLine />
          </el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            --
          </div>
          <div class="stat-label">
            AI 分析次数
          </div>
          <div class="stat-trend">
            <el-icon class="trend-icon">
              <TrendCharts />
            </el-icon>
            <span>本月累计</span>
          </div>
        </div>
      </div>

      <!-- 预警消息 -->
      <div class="stat-card stat-card-warning">
        <div class="stat-icon">
          <el-icon :size="28">
            <Warning />
          </el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            --
          </div>
          <div class="stat-label">
            预警消息
          </div>
          <div class="stat-trend">
            <el-icon class="trend-icon">
              <Bell />
            </el-icon>
            <span>系统通知</span>
          </div>
        </div>
      </div>

      <!-- 当前用户 -->
      <div class="stat-card stat-card-info">
        <div class="stat-icon">
          <el-icon :size="28">
            <User />
          </el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value user-email">
            {{ userStore.email }}
          </div>
          <div class="stat-label">
            当前用户
          </div>
          <div class="stat-trend">
            <el-tag
              size="small"
              :type="userRoleType"
              effect="plain"
            >
              {{ userRoleLabel }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷入口和最近活动 -->
    <div class="content-grid">
      <!-- 快捷入口 -->
      <el-card class="quick-links-card">
        <template #header>
          <div class="card-header">
            <div class="header-title">
              <el-icon><Grid /></el-icon>
              <span>快捷入口</span>
            </div>
          </div>
        </template>
        <div class="quick-links">
          <router-link
            v-for="link in quickLinks"
            :key="link.path"
            :to="link.path"
            class="quick-link-item"
            :class="`quick-link-${link.color}`"
          >
            <div class="quick-link-icon">
              <el-icon :size="24">
                <component :is="link.icon" />
              </el-icon>
            </div>
            <div class="quick-link-content">
              <div class="quick-link-title">
                {{ link.title }}
              </div>
              <div class="quick-link-desc">
                {{ link.description }}
              </div>
            </div>
            <el-icon class="quick-link-arrow">
              <ArrowRight />
            </el-icon>
          </router-link>
        </div>
      </el-card>

      <!-- 系统公告 -->
      <el-card class="announcement-card">
        <template #header>
          <div class="card-header">
            <div class="header-title">
              <el-icon><Bell /></el-icon>
              <span>系统公告</span>
            </div>
            <el-tag
              size="small"
              type="danger"
            >
              NEW
            </el-tag>
          </div>
        </template>
        <div class="announcement-list">
          <div
            v-for="item in announcements"
            :key="item.id"
            class="announcement-item"
          >
            <div class="announcement-dot" />
            <div class="announcement-content">
              <div class="announcement-title">
                {{ item.title }}
              </div>
              <div class="announcement-time">
                {{ item.time }}
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  TrendCharts,
  DataLine,
  Warning,
  User,
  Grid,
  ArrowRight,
  Bell,
  Search,
  DataAnalysis,
  ChatDotRound,
  Setting
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'

const userStore = useUserStore()

// 用户信息
const displayName = computed(() => {
  return userStore.userInfo?.username || '用户'
})

const userRoleLabel = computed(() => {
  const role = userStore.userInfo?.role
  const labels: Record<string, string> = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '管理员',
    'USER': '普通用户',
  }
  return labels[role || ''] || '访客'
})

const userRoleType = computed(() => {
  const role = userStore.userInfo?.role
  const types: Record<string, 'danger' | 'warning' | 'info' | 'success'> = {
    'SUPER_ADMIN': 'danger',
    'ADMIN': 'warning',
    'USER': 'success',
  }
  return types[role || ''] || 'info'
})

// 渐变背景样式
const gradients = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
]
const gradientStyle = computed(() => gradients[0])

// 快捷入口
const quickLinks = ref([
  {
    title: '单股分析',
    description: 'AI 智能分析单只股票',
    path: '/trading-agents/analysis/single',
    icon: DataAnalysis,
    color: 'primary',
  },
  {
    title: '批量分析',
    description: '批量分析多只股票',
    path: '/trading-agents/analysis/batch',
    icon: Grid,
    color: 'success',
  },
  {
    title: '智能选股',
    description: 'AI 辅助选股工具',
    path: '/screener',
    icon: Search,
    color: 'warning',
  },
  {
    title: 'AI 问股',
    description: '智能问答助手',
    path: '/ask-stock',
    icon: ChatDotRound,
    color: 'info',
  },
])

// 系统公告
const announcements = ref([
  {
    id: 1,
    title: '欢迎使用股票分析平台',
    time: '刚刚',
  },
  {
    id: 2,
    title: '新增 AI 批量分析功能',
    time: '1 天前',
  },
  {
    id: 3,
    title: '系统维护通知',
    time: '3 天前',
  },
])

onMounted(async () => {
  // 获取用户配置
  await userStore.fetchPreferences()
})
</script>

<style scoped>
/* ===========================================
   页面容器 Page Container
   =========================================== */

.dashboard-view {
  max-width: var(--max-width-xxl);
  margin: 0 auto;
  animation: fade-in 0.4s var(--ease-out-cubic);
}

/* ===========================================
   欢迎卡片 Welcome Card
   =========================================== */

.welcome-card {
  border-radius: var(--radius-xxl);
  padding: var(--space-8);
  color: #fff;
  margin-bottom: var(--space-6);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.welcome-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 2;
}

.welcome-text {
  flex: 1;
}

.welcome-title {
  font-size: var(--font-size-display);
  font-weight: var(--font-weight-bold);
  margin: 0 0 var(--space-2) 0;
  line-height: 1.2;
}

.welcome-description {
  font-size: var(--font-size-lg);
  opacity: 0.95;
  margin: 0;
  max-width: 600px;
}

.welcome-decoration {
  position: relative;
  width: 200px;
  height: 150px;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 6s ease-in-out infinite;
}

.circle-1 {
  width: 120px;
  height: 120px;
  top: 10px;
  right: 20px;
  animation-delay: 0s;
}

.circle-2 {
  width: 80px;
  height: 80px;
  bottom: 10px;
  right: 80px;
  animation-delay: 2s;
}

.circle-3 {
  width: 50px;
  height: 50px;
  top: 50px;
  right: 10px;
  animation-delay: 4s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-20px) scale(1.05);
  }
}

/* ===========================================
   统计卡片网格 Stats Grid
   =========================================== */

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-bg-container);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  border: 1px solid var(--color-border-secondary);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-base) var(--ease-out-cubic);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  transition: height var(--duration-base) var(--ease-out-cubic);
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.stat-card:hover::before {
  height: 100%;
  opacity: 0.03;
}

.stat-card-primary::before {
  background: var(--gradient-primary);
}

.stat-card-success::before {
  background: var(--gradient-success);
}

.stat-card-warning::before {
  background: var(--gradient-warning);
}

.stat-card-info::before {
  background: var(--gradient-ocean);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.stat-card-primary .stat-icon {
  background: var(--gradient-primary);
}

.stat-card-success .stat-icon {
  background: var(--gradient-success);
}

.stat-card-warning .stat-icon {
  background: var(--gradient-warning);
}

.stat-card-info .stat-icon {
  background: var(--gradient-ocean);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--font-size-xxxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1;
  margin-bottom: var(--space-2);
}

.stat-value.user-email {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.trend-icon {
  font-size: 14px;
}

/* ===========================================
   内容网格 Content Grid
   =========================================== */

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-5);
}

/* ===========================================
   快捷入口卡片 Quick Links Card
   =========================================== */

.quick-links-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.quick-link-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-spotlight);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-tertiary);
  text-decoration: none;
  transition: all var(--duration-base) var(--ease-out-cubic);
  position: relative;
  overflow: hidden;
}

.quick-link-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  transition: width var(--duration-base) var(--ease-out-cubic);
}

.quick-link-item:hover {
  background: var(--color-bg-container);
  box-shadow: var(--shadow-base);
  transform: translateY(-2px);
  border-color: var(--color-border-primary);
}

.quick-link-item:hover::before {
  width: 100%;
  opacity: 0.05;
}

.quick-link-primary::before {
  background: var(--color-primary);
}

.quick-link-success::before {
  background: var(--color-success);
}

.quick-link-warning::before {
  background: var(--color-warning);
}

.quick-link-info::before {
  background: var(--color-info);
}

.quick-link-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.quick-link-primary .quick-link-icon {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.quick-link-success .quick-link-icon {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.quick-link-warning .quick-link-icon {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.quick-link-info .quick-link-icon {
  background: #e6f7ff;
  color: #1890ff;
}

.quick-link-content {
  flex: 1;
}

.quick-link-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.quick-link-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.quick-link-arrow {
  color: var(--color-text-quaternary);
  transition: all var(--duration-base) var(--ease-out-cubic);
}

.quick-link-item:hover .quick-link-arrow {
  color: var(--color-primary);
  transform: translateX(4px);
}

/* ===========================================
   系统公告卡片 Announcement Card
   =========================================== */

.announcement-card {
  height: 100%;
}

.announcement-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.announcement-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-base);
  transition: background var(--duration-fast) var(--ease-out-cubic);
}

.announcement-item:hover {
  background: var(--color-bg-spotlight);
}

.announcement-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  margin-top: 6px;
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(24, 144, 255, 0.4);
}

.announcement-content {
  flex: 1;
}

.announcement-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.announcement-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* ===========================================
   响应式 Responsive
   =========================================== */

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .quick-links {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-view {
    padding: 0;
  }

  .welcome-card {
    padding: var(--space-5);
  }

  .welcome-content {
    flex-direction: column;
    text-align: center;
  }

  .welcome-decoration {
    display: none;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }

  .stat-card {
    padding: var(--space-4);
  }

  .quick-links {
    grid-template-columns: 1fr;
  }
}
</style>
