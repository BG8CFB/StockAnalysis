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

          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRouteName">
              {{ currentRouteName }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 角色标签 -->
          <el-tag
            v-if="userStore.userInfo"
            :type="roleType"
            size="small"
            class="role-tag"
          >
            {{ roleLabel }}
          </el-tag>

          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar
                :size="32"
                :icon="UserFilled"
              />
              <span class="username">{{ displayName }}</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <div class="user-detail">
                    <div class="user-email">
                      {{ userStore.userInfo?.email }}
                    </div>
                    <el-tag
                      :type="roleType"
                      size="small"
                    >
                      {{ roleLabel }}
                    </el-tag>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  command="settings"
                >
                  <el-icon><Setting /></el-icon>
                  设置
                </el-dropdown-item>
                <el-dropdown-item
                  command="logout"
                  style="color: #f56c6c"
                >
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition
            name="fade"
            mode="out-in"
          >
            <component :is="Component" />
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
  TrendCharts,
  DataAnalysis,
  Search,
  Monitor,
  User,
  UserFilled,
  Setting,
  SwitchButton,
  ArrowDown,
  Menu,
  Fold,
  Expand,
} from '@element-plus/icons-vue'
import { eventBus, Events } from '@core/events/bus'
import { useUserStore } from '@core/auth/store'
// 使用相对路径导入 Sidebar 组件
import Sidebar from './components/Sidebar.vue'

// 给组件一个显式的名称，方便调试
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

// 用户信息
const displayName = computed(() => {
  return userStore.userInfo?.username || userStore.email || '用户'
})

const isAdmin = computed(() => {
  const role = userStore.userInfo?.role
  return role === 'ADMIN' || role === 'SUPER_ADMIN'
})

const roleLabel = computed(() => {
  const role = userStore.userInfo?.role
  const labels: Record<string, string> = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '管理员',
    'USER': '用户',
  }
  return labels[role || ''] || '访客'
})

const roleType = computed(() => {
  const role = userStore.userInfo?.role
  const types: Record<string, any> = {
    'SUPER_ADMIN': 'danger',
    'ADMIN': 'warning',
    'USER': 'info',
  }
  return types[role || ''] || 'info'
})

// 检查屏幕尺寸
const checkScreenSize = () => {
  // 使用 matchMedia 确保与 CSS 媒体查询完全一致
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
  // 移动端默认收起侧边栏
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

async function handleCommand(command: string) {
  switch (command) {
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}

onMounted(() => {
  // 检查屏幕尺寸
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background-color: #1a1a2e;
  transition: width 0.3s ease;
  overflow: hidden;
  z-index: 1000;
}

.sidebar.collapsed {
  width: 64px;
}

.main-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-menu-btn {
  display: none;
}

.collapse-btn {
  display: inline-flex;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.role-tag {
  display: inline-flex;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #606266;
}

.arrow {
  font-size: 12px;
  color: #909399;
}

.user-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 200px;
}

.user-email {
  font-size: 14px;
  color: #303133;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background-color: #f5f7fa;
  padding: 20px;
}

/* 侧边栏遮罩（移动端） */
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .main-content {
    padding: 16px;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 240px !important;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    width: 240px !important;
  }

  .header {
    padding: 0 16px;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }

  .collapse-btn {
    display: none;
  }

  .username {
    display: none;
  }

  .role-tag {
    display: none;
  }

  .user-detail {
    min-width: 180px;
  }

  .main-content {
    padding: 12px;
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .header {
    padding: 0 12px;
  }

  .header-left :deep(.el-breadcrumb) {
    font-size: 13px;
  }
}
</style>
