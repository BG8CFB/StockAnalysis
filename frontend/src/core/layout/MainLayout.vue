<template>
  <el-container class="main-layout">
    <!-- 移动端遮罩 -->
    <div
      v-if="sidebarOpen && isMobile"
      class="sidebar-overlay"
      @click="closeSidebar"
    />

    <!-- 侧边栏 -->
    <Sidebar
      :collapsed="collapsed"
      :class="{ 'mobile-open': sidebarOpen && isMobile }"
    />

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 头部 -->
      <el-header class="header">
        <div class="header-left">
          <!-- 移动端菜单按钮 -->
          <el-button
            class="mobile-menu-btn"
            text
            @click="toggleSidebar"
          >
            <el-icon :size="20">
              <Menu />
            </el-icon>
          </el-button>

          <!-- 桌面端折叠按钮 -->
          <el-button
            class="collapse-btn"
            text
            @click="collapsed = !collapsed"
          >
            <el-icon :size="20">
              <Fold v-if="!collapsed" /><Expand v-else />
            </el-icon>
          </el-button>

          <!-- 面包屑 -->
          <el-breadcrumb
            separator="/"
            class="breadcrumb"
          >
            <el-breadcrumb-item
              :class="{ 'is-link': isLoggedIn }"
              @click="handleBreadcrumbHomeClick"
            >
              <el-icon><HomeFilled /></el-icon>
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRouteName">
              {{ currentRouteName }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <!-- 头部右侧 -->
        <div class="header-right">
          <!-- 系统状态指示器 -->
          <div class="system-status">
            <div class="status-dot status-online" />
            <span class="status-text">系统正常</span>
          </div>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component, route: currentRouteSlot }">
          <transition
            :name="getTransitionName(currentRouteSlot)"
            mode="out-in"
            @before-enter="handleBeforeEnter"
            @after-enter="handleAfterEnter"
          >
            <component
              :is="Component"
              :key="currentRouteSlot.path"
            />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  HomeFilled,
  Menu,
  Fold,
  Expand,
} from '@element-plus/icons-vue'
import { eventBus, Events } from '@core/events/bus'
import { useUserStore } from '@core/auth/store'
import Sidebar from './components/Sidebar.vue'

Sidebar.name = 'Sidebar'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 侧边栏状态
const collapsed = ref(false)
const sidebarOpen = ref(false)

// 响应式断点
const isMobile = ref(false)

const currentRoute = computed(() => route.path)
const currentRouteName = computed(() => route.meta.title as string)
const isLoggedIn = computed(() => userStore.isLoggedIn)

// 检查屏幕尺寸
const checkScreenSize = () => {
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
  if (isMobile.value) {
    collapsed.value = true
  }
}

// 切换侧边栏
function toggleSidebar() {
  if (isMobile.value) {
    sidebarOpen.value = !sidebarOpen.value
  } else {
    collapsed.value = !collapsed.value
  }
}

// 关闭移动端侧边栏
function closeSidebar() {
  sidebarOpen.value = false
}

/**
 * 处理面包屑首页点击
 * 设计说明：检查登录状态后再决定是否跳转
 * - 已登录：跳转到 /dashboard
 * - 未登录：不跳转（因为 /dashboard 需要 auth，会触发路由守卫跳转到登录页）
 */
function handleBreadcrumbHomeClick() {
  if (!isLoggedIn.value) {
    // 未登录状态，不跳转
    return
  }
  // 已登录，跳转到仪表板
  router.push('/dashboard')
}

// 获取页面过渡动画名称
function getTransitionName(route: any) {
  // 可以根据路由层级或meta配置返回不同的过渡动画
  if (route.meta?.transition) {
    return route.meta.transition
  }
  return 'fade-slide'
}

// 页面进入前钩子
function handleBeforeEnter() {
  // 可以添加页面加载前的逻辑
}

// 页面进入后钩子
function handleAfterEnter() {
  // 可以添加页面加载后的逻辑
}

onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<style scoped>
/* ===========================================
   主布局容器 Main Layout Container
   =========================================== */

.main-layout {
  height: 100vh;
  overflow: hidden;
  background: var(--color-bg-page);
}

/* ===========================================
   主内容容器 Main Container
   =========================================== */

.main-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ===========================================
   头部 Header
   =========================================== */

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-container);
  border-bottom: 1px solid var(--color-border-secondary);
  padding: 0 var(--space-6);
  height: var(--header-height);
  box-shadow: var(--shadow-sm);
  position: relative;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

/* 菜单按钮 */
.mobile-menu-btn {
  display: none;
}

.collapse-btn {
  display: inline-flex;
  color: var(--color-text-secondary);
}

.collapse-btn:hover {
  color: var(--color-primary);
  background-color: var(--color-primary-bg);
}

/* 面包屑 */
.breadcrumb {
  margin-left: var(--space-2);
}

.breadcrumb :deep(.el-breadcrumb__item) {
  font-size: var(--font-size-sm);
}

.breadcrumb :deep(.el-breadcrumb__inner) {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-normal);
  cursor: default;
}

/* 只有 is-link 类时才显示为可点击 */
.breadcrumb :deep(.is-link .el-breadcrumb__inner) {
  cursor: pointer;
}

.breadcrumb :deep(.is-link .el-breadcrumb__inner:hover) {
  color: var(--color-primary);
}

.breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

/* 系统状态指示器 */
.system-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-spotlight);
  border-radius: var(--radius-round);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-online {
  background: var(--color-success);
  box-shadow: 0 0 8px rgba(82, 196, 26, 0.4);
}

.status-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* ===========================================
   主内容区 Main Content
   =========================================== */

.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-6);
  position: relative;
}

/* ===========================================
   侧边栏遮罩（移动端）Sidebar Overlay
   =========================================== */

.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 999;
  animation: fade-in var(--duration-base) var(--ease-out-cubic);
}

/* ===========================================
   页面过渡动画 Page Transitions
   =========================================== */

/* 淡入滑动 Fade Slide */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all var(--duration-slow) var(--ease-out-cubic);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 淡入 Fade */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-base) var(--ease-out-cubic);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滑动 Slide */
.slide-enter-active,
.slide-leave-active {
  transition: all var(--duration-slow) var(--ease-out-cubic);
}

.slide-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* 缩放 Scale */
.scale-enter-active,
.scale-leave-active {
  transition: all var(--duration-slow) var(--ease-out-cubic);
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* ===========================================
   响应式适配 Responsive
   =========================================== */

@media (max-width: 1024px) {
  .main-content {
    padding: var(--space-4);
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .header {
    padding: 0 var(--space-4);
  }

  .mobile-menu-btn {
    display: inline-flex;
    color: var(--color-text-secondary);
  }

  .mobile-menu-btn:hover {
    color: var(--color-primary);
    background-color: var(--color-primary-bg);
  }

  .collapse-btn {
    display: none;
  }

  .breadcrumb {
    display: none;
  }

  .system-status {
    display: none;
  }

  .main-content {
    padding: var(--space-3);
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .header {
    padding: 0 var(--space-3);
  }

  .header-left {
    gap: var(--space-2);
  }
}
</style>
