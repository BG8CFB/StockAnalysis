<template>
  <el-aside
    :width="collapsed ? '68px' : '260px'"
    class="sidebar-container"
    :class="{ collapsed }"
  >
    <!-- Brand / Logo -->
    <div
      class="sidebar-header"
      @click="handleLogoClick"
    >
      <div class="logo-wrapper">
        <div class="logo-icon">
          <el-icon :size="20">
            <DataAnalysis />
          </el-icon>
        </div>
        <div
          v-if="!collapsed"
          class="logo-text-group"
        >
          <h1 class="logo-text">
            股票分析
          </h1>
          <p class="logo-subtitle">
            Smart Trading
          </p>
        </div>
      </div>
    </div>

    <!-- Main Navigation -->
    <div class="sidebar-scroll-area">
      <el-menu
        :default-active="currentRoute"
        :collapse="collapsed"
        :collapse-transition="false"
        unique-opened
        router
        class="custom-menu"
      >
        <!-- Section: Overview -->
        <div
          v-if="!collapsed"
          class="menu-label"
        >
          平台概览
        </div>
        
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>
            仪表板
          </template>
        </el-menu-item>

        <el-menu-item index="/screener">
          <el-icon><Search /></el-icon>
          <template #title>
            智能选股
          </template>
        </el-menu-item>

        <el-menu-item index="/ask-stock">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>
            AI 问股
          </template>
        </el-menu-item>

        <!-- Section: Analysis Tools -->
        <div
          v-if="!collapsed"
          class="menu-label mt-4"
        >
          核心分析
        </div>

        <el-sub-menu
          index="analysis"
          popper-class="custom-popper"
        >
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>AI 深度分析</span>
          </template>

          <el-menu-item index="/trading-agents/analysis/single">
            <span class="sub-dot" />
            <span>个股分析</span>
          </el-menu-item>
          <el-menu-item index="/trading-agents/analysis/batch">
            <span class="sub-dot" />
            <span>批量扫描</span>
          </el-menu-item>
          <el-menu-item index="/trading-agents/tasks">
            <span class="sub-dot" />
            <span>任务队列</span>
          </el-menu-item>
          <el-menu-item index="/trading-agents/compare">
            <span class="sub-dot" />
            <span>历史对比</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- Section: Configuration -->
        <div
          v-if="!collapsed"
          class="menu-label mt-4"
        >
          系统管理
        </div>

        <el-sub-menu
          index="settings"
          popper-class="custom-popper"
        >
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>全局设置</span>
          </template>

          <!-- 管理员专区 - 使用 v-show 保持 DOM 结构稳定 -->
          <!-- 注意：isAdmin 计算属性会在 userInfo 加载前临时返回 false -->
          <!-- 使用 v-show 而不是 v-if 可以避免菜单闪烁和状态不一致 -->
          <el-menu-item
            v-show="isAdmin"
            index="/settings/users"
          >
            <span class="sub-dot" />
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item
            v-show="isAdmin"
            index="/settings/system"
          >
            <span class="sub-dot" />
            <span>系统参数</span>
          </el-menu-item>

          <!-- 核心基础设施 -->
          <el-menu-item index="/settings/ai-management/models">
            <span class="sub-dot" />
            <span>AI 管理</span>
          </el-menu-item>

          <!-- 业务配置 -->
          <el-menu-item index="/settings/data-sources">
            <span class="sub-dot" />
            <span>数据源设置</span>
          </el-menu-item>

          <el-menu-item index="/settings/trading">
            <span class="sub-dot" />
            <span>Trading Agent 设置</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </div>

    <!-- User Footer -->
    <div class="sidebar-footer">
      <div
        v-if="userStore.userInfo"
        class="user-card"
        @click="showUserMenu"
      >
        <el-avatar
          :size="32"
          :src="userStore.userInfo.avatar"
          :icon="UserFilled"
          class="user-avatar"
        />
        <div
          v-if="!collapsed"
          class="user-details"
        >
          <div class="user-name">
            {{ userStore.userInfo.username || 'User' }}
          </div>
          <div class="user-role">
            {{ roleLabel }}
          </div>
        </div>
        <el-button
          v-if="!collapsed"
          class="logout-icon"
          link
          :icon="SwitchButton"
          @click.stop="handleLogout"
        />
      </div>
    </div>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  HomeFilled, TrendCharts, DataAnalysis, Search, UserFilled,
  Setting, ChatDotRound, SwitchButton, Monitor
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

defineProps<{ collapsed: boolean }>()

const currentRoute = computed(() => route.path)
const isAdmin = computed(() => ['ADMIN', 'SUPER_ADMIN'].includes(userStore.userInfo?.role || ''))

const roleLabel = computed(() => {
  const map: Record<string, string> = { 'SUPER_ADMIN': '超级管理员', 'ADMIN': '管理员', 'USER': '普通用户' }
  return map[userStore.userInfo?.role || ''] || '访客'
})

/**
 * 处理 Logo 点击
 */
function handleLogoClick() {
  router.push('/dashboard')
}

/**
 * 显示用户菜单（预留功能）
 */
function showUserMenu() {
  // TODO: 实现用户菜单（个人资料、设置等）
}

/**
 * 处理用户登出
 *
 * 设计说明：
 * 1. 显示确认对话框
 * 2. 调用 userStore.logout() 清除状态并触发 USER_LOGOUT 事件
 * 3. 主动跳转到登录页（此时 router-view 已渲染，不会造成死锁）
 */
async function handleLogout() {
  try {
    await ElMessageBox.confirm(
      '确认退出登录?',
      '提示',
      {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await userStore.logout()

    // 用户主动退出时立即跳转登录页（router-view 已渲染，安全）
    router.push({ name: 'Login' })
    ElMessage.success('已安全退出')
  } catch {
    // 用户取消操作，不做任何事
  }
}
</script>

<style scoped>
/* ============================================
   一级侧边栏 - 精致深色主题设计
   Primary Sidebar - Refined Dark Theme
   ============================================ */

/* Theme Variables */
.sidebar-container {
  /* 浅色配色 - 与二级侧边栏（白色）协调但保持轻微层级 */
  --sb-bg: #f1f5f9; /* Slate 100 - 浅灰蓝 */
  --sb-bg-submenu: rgba(0, 0, 0, 0.03);
  --sb-text: #64748b; /* Slate 500 */
  --sb-text-hover: #334155; /* Slate 700 */
  --sb-text-active: #2563eb; /* Blue 600 */
  --sb-border: #e2e8f0; /* Slate 200 */
  --sb-border-glow: rgba(59, 130, 246, 0.2);
  --sb-active-bg: #dbeafe; /* Blue 100 */
  --sb-hover-bg: #e2e8f0; /* Slate 200 */
  --sb-header-height: clamp(56px, 6vh + 50px, 72px);
  --sb-primary: #2563eb; /* Blue 600 */
  --sb-primary-glow: rgba(37, 99, 235, 0.3);
  --sb-accent: #7c3aed; /* Violet 600 */

  background-color: var(--sb-bg);
  border-right: 1px solid var(--sb-border);
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  height: 100vh;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  user-select: none;
}

/* ============================================
   Header / Logo - 头部品牌区
   ============================================ */
.sidebar-header {
  height: var(--sb-header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%);
  border-bottom: 1px solid var(--sb-border);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

/* 头部背景装饰 - 微妙的渐变光晕 */
.sidebar-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: clamp(120px, 15vw + 80px, 200px);
  height: clamp(120px, 15vw + 80px, 200px);
  background: radial-gradient(circle, var(--sb-primary-glow) 0%, transparent 70%);
  opacity: 0.15;
  pointer-events: none;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  position: relative;
  z-index: 1;
}

/* Logo 图标 - 渐变背景 + 发光效果 */
.logo-icon {
  width: clamp(32px, 2vw + 28px, 42px);
  height: clamp(32px, 2vw + 28px, 42px);
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  animation: logo-pulse 3s ease-in-out infinite;
}

.logo-icon .el-icon {
  vertical-align: middle;
}

/* Logo 呼吸动画 */
@keyframes logo-pulse {
 0%, 100% {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }
  50% {
    box-shadow: 0 4px 18px rgba(37, 99, 235, 0.5);
  }
}

/* Logo 文字组 */
.logo-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: #1e293b; /* Slate 800 */
  margin: 0;
  letter-spacing: 0.5px;
  white-space: nowrap;
  line-height: 1.2;
}

/* 副标题 - 英文 */
.logo-subtitle {
  font-size: var(--font-size-xs);
  color: #64748b; /* Slate 500 */
  margin: 0;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  line-height: 1;
}

/* ============================================
   Scroll Area - 滚动区域
   ============================================ */
.sidebar-scroll-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-5) var(--space-3);
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.sidebar-scroll-area::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

/* ============================================
   Menu Reset - 菜单基础样式重置
   ============================================ */
.custom-menu {
  border: none !important;
  background: transparent !important;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--sb-text);
  --el-menu-hover-bg-color: transparent;
  --el-menu-active-color: var(--sb-text-active);
}

/* ============================================
   Menu Label - 分组标签
   ============================================ */
.menu-label {
  position: relative;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  color: #94a3b8; /* Slate 400 */
  font-weight: 700;
  letter-spacing: 0.2em;
  margin: var(--space-5) var(--space-3) var(--space-3);
  padding-left: var(--space-3);
  display: flex;
  align-items: center;
}

/* 分组标签左侧装饰条 - 渐变 + 发光 */
.menu-label::before {
  content: '';
  position: absolute;
  left: 0;
  width: 2px;
  height: clamp(8px, 0.5vw + 6px, 12px);
  background: linear-gradient(to bottom, #2563eb, #7c3aed);
  border-radius: 2px;
  box-shadow: 0 0 6px rgba(37, 99, 235, 0.3);
}

.mt-4 { margin-top: var(--space-5); }

/* ============================================
   Menu Items - 一级菜单项
   ============================================ */
:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: clamp(38px, 2vw + 34px, 46px);
  line-height: clamp(38px, 2vw + 34px, 46px);
  border-radius: var(--radius-base);
  margin-bottom: 4px;
  color: var(--sb-text);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-left: 3px solid transparent;
  position: relative;
}

/* Hover 状态 */
:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: var(--sb-hover-bg) !important;
  color: var(--sb-text-hover);
  transform: translateX(1px);
}

/* Active 状态 - 左边框 + 发光 */
:deep(.el-menu-item.is-active) {
  background-color: var(--sb-active-bg) !important;
  color: var(--sb-text-active) !important;
  font-weight: 600;
  border-left-color: var(--sb-primary);
  box-shadow: 0 0 12px rgba(37, 99, 235, 0.15);
}

/* 子菜单展开状态 */
:deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  background-color: rgba(37, 99, 235, 0.06) !important;
  color: var(--sb-text-hover);
}

/* Icons - 只针对菜单项内的图标 */
:deep(.el-menu-item .el-icon),
:deep(.el-sub-menu__title .el-icon) {
  font-size: clamp(16px, 0.5vw + 15px, 20px);
  margin-right: var(--space-3);
  color: inherit;
}

/* 展开箭头 */
:deep(.el-sub-menu__icon-arrow) {
  font-size: 12px !important;
  margin-right: 0 !important;
  color: inherit;
  transition: transform 0.2s;
}

:deep(.el-sub-menu.is-opened .el-sub-menu__icon-arrow) {
  transform: rotate(180deg);
}

/* ============================================
   Submenu - 二级菜单
   ============================================ */
:deep(.el-sub-menu .el-menu) {
  background: var(--sb-bg-submenu) !important;
  border-radius: var(--radius-base);
  padding: var(--space-2) 0;
  margin-top: 4px;
}

/* Level 2 Items - 二级菜单项 */
:deep(.el-sub-menu .el-menu-item) {
  height: clamp(32px, 1.5vw + 28px, 40px);
  line-height: clamp(32px, 1.5vw + 28px, 40px);
  font-size: var(--font-size-sm);
  padding-left: var(--space-6) !important;
  border-left-width: 2px;
  margin-bottom: 2px;
}

/* 二级菜单装饰圆点 */
.sub-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background-color: #94a3b8; /* Slate 400 */
  margin-right: var(--space-3);
  transition: all 0.2s;
  display: inline-block;
}

:deep(.el-menu-item.is-active) .sub-dot {
  background-color: var(--sb-text-active);
  box-shadow: 0 0 6px rgba(37, 99, 235, 0.4);
}

/* ============================================
   Footer - 底部用户卡片
   ============================================ */
.sidebar-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--sb-border);
}

.user-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: #ffffff;
  border: 1px solid var(--sb-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.user-card:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.user-avatar {
  border: 2px solid #e2e8f0;
  box-shadow: 0 0 0 0 !important;
}

.user-details {
  flex: 1;
  overflow: hidden;
}

.user-name {
  color: #1e293b; /* Slate 800 */
  font-size: var(--font-size-base);
  font-weight: 600;
  white-space: nowrap;
}

.user-role {
  font-size: var(--font-size-xs);
  color: #2563eb; /* Blue 600 */
  background: #dbeafe; /* Blue 100 */
  border: 1px solid #bfdbfe; /* Blue 200 */
  padding: 2px var(--space-2);
  border-radius: var(--radius-base);
  display: inline-block;
  margin-top: 2px;
}

.logout-icon {
  color: #94a3b8; /* Slate 400 */
  transition: all 0.2s;
}

.logout-icon:hover {
  color: #2563eb; /* Blue 600 */
}

/* ============================================
   Collapsed State - 折叠状态
   ============================================ */
.collapsed .logo-text-group,
.collapsed .menu-label,
.collapsed .user-details,
.collapsed .logout-icon {
  display: none;
}

.collapsed :deep(.el-menu-item),
.collapsed :deep(.el-sub-menu__title) {
  padding: 0 !important;
  justify-content: center;
}

.collapsed :deep(.el-icon) {
  margin-right: 0;
}

.collapsed :deep(.el-sub-menu__icon-arrow) {
  display: none;
}

.collapsed .logo-wrapper {
  justify-content: center;
}

.collapsed .user-card {
  justify-content: center;
  padding: var(--space-2);
}

.collapsed .user-avatar {
  margin: 0;
}

/* ============================================
   Mobile Drawer - 移动端抽屉模式
   ============================================ */
@media (max-width: 768px) {
  .sidebar-container {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
    /* 默认隐藏到左侧 */
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.15);
  }

  /* 移动端展开状态 */
  .sidebar-container.mobile-open {
    transform: translateX(0);
  }

  /* 移动端宽度调整为适配屏幕 */
  .sidebar-container {
    width: clamp(260px, 70vw + 60px, 320px);
  }

  /* 确保在移动端遮罩之上时用户卡片等元素不溢出 */
  .sidebar-scroll-area {
    overflow-y: auto;
    overflow-x: hidden;
  }
}
</style>