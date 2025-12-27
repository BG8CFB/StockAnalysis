<template>
  <el-aside
    :width="collapsed ? '64px' : '240px'"
    class="sidebar"
    :class="{ collapsed }"
  >
    <div class="sidebar-content">
      <!-- Logo 区域 -->
      <div class="logo" @click="handleLogoClick">
        <template v-if="!collapsed">
          <div class="logo-icon">
            <el-icon :size="28">
              <TrendCharts />
            </el-icon>
          </div>
          <div class="logo-text">
            <h1>股票分析</h1>
            <span class="logo-subtitle">Financial AI</span>
          </div>
        </template>
        <template v-else>
          <div class="logo-icon-collapsed">
            <el-icon :size="24">
              <TrendCharts />
            </el-icon>
          </div>
        </template>
      </div>

      <!-- 菜单区域 -->
      <el-menu
        :default-active="currentRoute"
        :collapse="collapsed"
        router
        background-color="transparent"
        text-color="rgba(255, 255, 255, 0.75)"
        active-text-color="#ffffff"
        class="sidebar-menu"
      >
        <!-- 仪表板 -->
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>仪表板</template>
        </el-menu-item>

        <!-- AI 分析子菜单 -->
        <el-sub-menu index="analysis">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>AI 分析</span>
          </template>
          <el-menu-item index="/trading-agents/analysis/single">
            <el-icon><TrendCharts /></el-icon>
            <template #title>单个分析</template>
          </el-menu-item>
          <el-menu-item index="/trading-agents/analysis/batch">
            <el-icon><Files /></el-icon>
            <template #title>批量分析</template>
          </el-menu-item>
          <el-menu-item index="/trading-agents/tasks">
            <el-icon><List /></el-icon>
            <template #title>任务中心</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- 智能选股 -->
        <el-menu-item index="/screener">
          <el-icon><Search /></el-icon>
          <template #title>智能选股</template>
        </el-menu-item>

        <!-- AI 问股 -->
        <el-menu-item index="/ask-stock">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>AI 问股</template>
        </el-menu-item>

        <!-- 设置菜单 -->
        <el-sub-menu index="settings">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>设置</span>
          </template>
          <el-menu-item
            v-if="isAdmin"
            index="/settings/users"
          >
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          <el-menu-item
            v-if="isAdmin"
            index="/settings/system"
          >
            <el-icon><Tools /></el-icon>
            <template #title>系统设置</template>
          </el-menu-item>
          <el-sub-menu index="trading-agents-settings">
            <template #title>
              <el-icon><MagicStick /></el-icon>
              <span>智能体设置</span>
            </template>
            <el-menu-item index="/settings/trading-agents/models">
              <el-icon><Cpu /></el-icon>
              <template #title>AI 模型管理</template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/mcp-servers">
              <el-icon><Connection /></el-icon>
              <template #title>MCP 服务器管理</template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/agent-config">
              <el-icon><Odometer /></el-icon>
              <template #title>智能体配置</template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/analysis">
              <el-icon><Operation /></el-icon>
              <template #title>分析设置</template>
            </el-menu-item>
          </el-sub-menu>
        </el-sub-menu>
      </el-menu>

      <!-- 用户区域 -->
      <div v-if="userStore.userInfo" class="user-profile">
        <div class="user-profile-content" @click="showUserMenu">
          <div class="user-avatar">
            <el-avatar
              :size="36"
              :icon="UserFilled"
              :src="userStore.userInfo.avatar"
            />
            <div v-if="!collapsed" class="user-status-dot" />
          </div>
          <div v-if="!collapsed" class="user-info">
            <span class="username">{{ userStore.userInfo.username || '用户' }}</span>
            <el-tag
              size="small"
              effect="dark"
              :type="roleTagType"
              class="role-tag"
            >
              {{ roleLabel }}
            </el-tag>
          </div>
          <el-tooltip
            v-if="!collapsed"
            content="退出登录"
            placement="top"
          >
            <el-button
              class="logout-btn"
              :icon="SwitchButton"
              circle
              text
              @click.stop="handleLogout"
            />
          </el-tooltip>
          <el-tooltip
            v-else
            content="退出登录"
            placement="right"
          >
            <el-button
              class="logout-btn logout-btn-collapsed"
              :icon="SwitchButton"
              circle
              text
              @click.stop="handleLogout"
            />
          </el-tooltip>
        </div>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="sidebar-decoration" />
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  HomeFilled,
  TrendCharts,
  DataAnalysis,
  Search,
  User,
  UserFilled,
  Setting,
  Tools,
  Files,
  List,
  ChatDotRound,
  MagicStick,
  Cpu,
  Connection,
  Odometer,
  Operation,
  SwitchButton
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

defineProps<{
  collapsed: boolean
}>()

const currentRoute = computed(() => route.path)
const isAdmin = computed(() => userStore.userInfo?.role === 'ADMIN' || userStore.userInfo?.role === 'SUPER_ADMIN')

const roleLabel = computed(() => {
  const role = userStore.userInfo?.role
  const labels: Record<string, string> = {
    'SUPER_ADMIN': '超管',
    'ADMIN': '管理员',
    'USER': '用户',
  }
  return labels[role || ''] || '访客'
})

const roleTagType = computed(() => {
  const role = userStore.userInfo?.role
  const types: Record<string, 'danger' | 'warning' | 'info' | 'success'> = {
    'SUPER_ADMIN': 'danger',
    'ADMIN': 'warning',
    'USER': 'success',
  }
  return types[role || ''] || 'info'
})

function handleLogoClick() {
  router.push('/dashboard')
}

function showUserMenu() {
  // 可以扩展为显示用户菜单
}

async function handleLogout() {
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
}
</script>

<style scoped>
/* ===========================================
   侧边栏容器 Sidebar Container
   =========================================== */

.sidebar {
  background-color: var(--sidebar-bg);
  transition: width var(--duration-slow) var(--ease-out-cubic);
  overflow: hidden;
  border-right: 1px solid var(--sidebar-border);
  position: relative;
  z-index: 100;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

/* ===========================================
   侧边栏内容 Sidebar Content
   =========================================== */

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  position: relative;
  z-index: 2;
}

/* ===========================================
   Logo 区域 Logo Section
   =========================================== */

.logo {
  display: flex;
  align-items: center;
  height: var(--header-height);
  padding: 0 var(--space-5);
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-cubic);
  position: relative;
}

.logo:hover {
  background-color: var(--sidebar-hover-bg);
}

.logo > div {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: var(--shadow-primary);
  flex-shrink: 0;
}

.logo-icon-collapsed {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: var(--shadow-primary);
  margin: 0 auto;
}

.logo-text h1 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: #fff;
  margin: 0;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: var(--font-weight-medium);
}

/* ===========================================
   菜单区域 Menu Section
   =========================================== */

.sidebar-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-2) 0;
}

.sidebar-menu::-webkit-scrollbar {
  width: 4px;
}

.sidebar-menu::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

/* 菜单项样式 */
.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 2px var(--space-3);
  border-radius: var(--radius-base);
  transition: all var(--duration-base) var(--ease-out-cubic);
  color: var(--sidebar-text);
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background-color: var(--sidebar-hover-bg);
  color: var(--sidebar-text-hover);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: var(--shadow-primary);
  font-weight: var(--font-weight-medium);
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item) {
  height: 40px;
  line-height: 40px;
  margin: 2px var(--space-3) 2px var(--space-5);
  padding-left: var(--space-4) !important;
  background: transparent !important;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active) {
  background: rgba(24, 144, 255, 0.15) !important;
}

/* 子菜单图标 */
.sidebar-menu :deep(.el-sub-menu__icon-arrow) {
  color: rgba(255, 255, 255, 0.5);
}

/* 菜单折叠时的样式 */
.sidebar.collapsed .sidebar-menu :deep(.el-menu-item),
.sidebar.collapsed .sidebar-menu :deep(.el-sub-menu__title) {
  margin: 2px var(--space-2);
  padding: 0 !important;
  justify-content: center;
}

/* ===========================================
   用户区域 User Profile Section
   =========================================== */

.user-profile {
  padding: 0;
  border-top: 1px solid var(--sidebar-border);
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.2) 100%);
}

.user-profile-content {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  width: 100%;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-cubic);
  position: relative;
}

.user-profile-content:hover {
  background-color: var(--sidebar-hover-bg);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.user-status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  background: var(--color-success);
  border: 2px solid var(--sidebar-bg);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(82, 196, 26, 0.5);
  animation: pulse 2s ease-in-out infinite;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  overflow: hidden;
  white-space: nowrap;
  flex: 1;
  text-align: left;
}

.username {
  font-size: var(--font-size-sm);
  color: #fff;
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.3px;
}

.role-tag {
  transform: scale(0.85);
  transform-origin: left center;
  width: fit-content;
  font-weight: var(--font-weight-medium);
}

.logout-btn {
  color: rgba(255, 255, 255, 0.5);
  transition: all var(--duration-base) var(--ease-out-cubic);
  flex-shrink: 0;
}

.logout-btn:hover {
  color: var(--color-danger-light);
  background-color: rgba(245, 34, 45, 0.15) !important;
}

.logout-btn-collapsed {
  margin: 0 auto;
  color: rgba(255, 255, 255, 0.6);
}

/* ===========================================
   背景装饰 Background Decoration
   =========================================== */

.sidebar-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(24, 144, 255, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(82, 196, 26, 0.05) 0%, transparent 50%);
  pointer-events: none;
  z-index: 1;
}

/* ===========================================
   菜单图标 Menu Icons
   =========================================== */

:deep(.el-icon) {
  font-size: 18px;
}
</style>
