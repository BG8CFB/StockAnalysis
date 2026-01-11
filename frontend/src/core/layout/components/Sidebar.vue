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
          <el-icon :size="24">
            <TrendCharts />
          </el-icon>
        </div>
        <h1
          v-if="!collapsed"
          class="logo-text"
        >
          StockMind
        </h1>
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

        <!-- Section: Market Data -->
        <div
          v-if="!collapsed"
          class="menu-label mt-4"
        >
          市场数据
        </div>

        <el-sub-menu
          index="market-data"
          popper-class="custom-popper"
        >
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>数据查询</span>
          </template>

          <el-menu-item index="/market-data/stocks">
            <span class="sub-dot" />
            <span>股票列表</span>
          </el-menu-item>
          <el-menu-item index="/market-data/quotes">
            <span class="sub-dot" />
            <span>行情数据</span>
          </el-menu-item>
          <el-menu-item index="/market-data/health">
            <span class="sub-dot" />
            <span>数据源监控</span>
          </el-menu-item>
        </el-sub-menu>

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

          <template v-if="isAdmin">
            <el-menu-item index="/settings/users">
              <span class="sub-dot" />
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/settings/system">
              <span class="sub-dot" />
              <span>系统参数</span>
            </el-menu-item>
          </template>

          <el-menu-item index="/settings/mcp-servers">
            <span class="sub-dot" />
            <span>MCP 服务器管理</span>
          </el-menu-item>

          <el-menu-item index="/settings/trading-agents/models">
            <span class="sub-dot" />
            <span>AI 模型管理</span>
          </el-menu-item>

          <el-menu-item index="/settings/trading-agents/agent-config">
            <span class="sub-dot" />
            <span>智能体配置</span>
          </el-menu-item>

          <el-menu-item index="/settings/trading-agents/analysis">
            <span class="sub-dot" />
            <span>分析设置</span>
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
  Setting, ChatDotRound, SwitchButton
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

function handleLogoClick() { router.push('/dashboard') }
function showUserMenu() { /* Future feature */ }
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确认退出登录?', '提示', { confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning' })
    await userStore.logout()
    router.push('/login')
    ElMessage.success('已安全退出')
  } catch {
  }
}
</script>

<style scoped>
/* Theme Variables - Dark Modern SaaS */
.sidebar-container {
  --sb-bg: #111827; /* Gray 900 */
  --sb-text: #9ca3af; /* Gray 400 */
  --sb-text-hover: #f3f4f6; /* Gray 100 */
  --sb-active-bg: #1f2937; /* Gray 800 */
  --sb-active-text: #60a5fa; /* Blue 400 */
  --sb-border: #1f2937;
  --sb-header-height: 64px;
  
  background-color: var(--sb-bg);
  border-right: 1px solid var(--sb-border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  user-select: none;
}

/* Header / Logo */
.sidebar-header {
  height: var(--sb-header-height);
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--sb-border);
  cursor: pointer;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #f9fafb;
  margin: 0;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

/* Scroll Area */
.sidebar-scroll-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 12px;
}

.sidebar-scroll-area::-webkit-scrollbar { width: 4px; }
.sidebar-scroll-area::-webkit-scrollbar-thumb { background: #374151; border-radius: 2px; }

/* Menu Reset & Base Styles */
.custom-menu {
  border: none !important;
  background: transparent !important;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--sb-text);
  --el-menu-hover-bg-color: transparent;
  --el-menu-active-color: var(--sb-active-text);
}

.menu-label {
  font-size: 11px;
  text-transform: uppercase;
  color: #4b5563; /* Gray 600 */
  font-weight: 600;
  margin: 8px 12px 8px;
  letter-spacing: 0.05em;
}

.mt-4 { margin-top: 24px; }

/* Menu Items */
:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  height: 40px;
  line-height: 40px;
  border-radius: 6px;
  margin-bottom: 4px;
  color: var(--sb-text);
  transition: all 0.2s ease;
}

:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255,255,255,0.05) !important;
  color: var(--sb-text-hover);
}

:deep(.el-menu-item.is-active) {
  background-color: var(--sb-active-bg) !important;
  color: var(--sb-active-text) !important;
  font-weight: 500;
}

/* Icons */
:deep(.el-icon) {
  font-size: 18px;
  margin-right: 10px;
  color: inherit;
  transition: none;
}

/* Fix: Reduce size of expansion arrow */
:deep(.el-sub-menu__icon-arrow) {
  font-size: 12px !important;
  margin-right: 0 !important;
  width: auto;
}

/* Submenu Styles */
:deep(.el-sub-menu .el-menu) {
  background: transparent !important;
  padding-left: 0;
}

/* Level 2 Items */
:deep(.el-sub-menu .el-menu-item) {
  height: 36px;
  line-height: 36px;
  font-size: 13px;
  padding-left: 44px !important; /* Align with text of parent */
}

/* Decoration for Level 2 */
.sub-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: #4b5563;
  margin-right: 12px;
  transition: background 0.2s;
}

:deep(.el-menu-item.is-active) .sub-dot {
  background-color: var(--sb-active-text);
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.5);
}

/* Level 3 (Nested Submenu) */
.nested-submenu :deep(.el-sub-menu__title) {
  padding-left: 44px !important;
  height: 36px;
  line-height: 36px;
  font-size: 13px;
}
.group-dot { margin-right: 12px; }

/* Level 3 Items */
.nested-submenu :deep(.el-menu-item) {
  padding-left: 68px !important;
  position: relative;
}

/* Guide Lines for Deep Nesting */
.line-guide {
  position: absolute;
  left: 54px;
  top: 0;
  bottom: 0;
  width: 1px;
  background-color: #374151;
  opacity: 0.5;
}

/* Collapsed State Tweaks */
.collapsed .logo-text,
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
.collapsed :deep(.el-icon) { margin-right: 0; }
.collapsed :deep(.el-sub-menu__icon-arrow) { display: none; }

/* Footer */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--sb-border);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.user-card:hover { background-color: rgba(255,255,255,0.05); }

.user-details {
  flex: 1;
  overflow: hidden;
}
.user-name {
  color: #f3f4f6;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}
.user-role {
  color: #6b7280;
  font-size: 12px;
}
</style>