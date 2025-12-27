<template>
  <el-aside
    :width="collapsed ? '64px' : '240px'"
    class="sidebar"
    :class="{ collapsed }"
  >
    <div class="sidebar-content">
      <div
        class="logo"
        @click="handleLogoClick"
      >
        <template v-if="!collapsed">
          <h2>股票分析</h2>
        </template>
        <template v-else>
          <el-icon :size="24">
            <TrendCharts />
          </el-icon>
        </template>
      </div>

      <el-menu
        :default-active="currentRoute"
        :collapse="collapsed"
        router
        background-color="#1a1a2e"
        text-color="#b0b0b0"
        active-text-color="#409eff"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>
            仪表板
          </template>
        </el-menu-item>

        <el-sub-menu index="analysis">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>AI 分析</span>
          </template>
          <el-menu-item index="/trading-agents/analysis/single">
            <el-icon><TrendCharts /></el-icon>
            <template #title>
              单个分析
            </template>
          </el-menu-item>
          <el-menu-item index="/trading-agents/analysis/batch">
            <el-icon><Files /></el-icon>
            <template #title>
              批量分析
            </template>
          </el-menu-item>
          <el-menu-item index="/trading-agents/tasks">
            <el-icon><List /></el-icon>
            <template #title>
              任务中心
            </template>
          </el-menu-item>
        </el-sub-menu>

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

        <!-- 设置菜单 (包含用户管理) -->
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
            <template #title>
              用户管理
            </template>
          </el-menu-item>
          <el-menu-item 
            v-if="isAdmin"
            index="/settings/system"
          >
            <el-icon><Tools /></el-icon>
            <template #title>
              系统设置
            </template>
          </el-menu-item>
          <el-sub-menu index="trading-agents-settings">
            <template #title>
              <el-icon><MagicStick /></el-icon>
              <span>智能体设置</span>
            </template>
            <el-menu-item index="/settings/trading-agents/models">
              <el-icon><Cpu /></el-icon>
              <template #title>
                AI 模型管理
              </template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/mcp-servers">
              <el-icon><Connection /></el-icon>
              <template #title>
                MCP 服务器管理
              </template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/agent-config">
              <el-icon><Odometer /></el-icon>
              <template #title>
                智能体配置
              </template>
            </el-menu-item>
            <el-menu-item index="/settings/trading-agents/analysis">
              <el-icon><Operation /></el-icon>
              <template #title>
                分析设置
              </template>
            </el-menu-item>
          </el-sub-menu>
        </el-sub-menu>
      </el-menu>

      <div
        v-if="userStore.userInfo"
        class="user-profile"
      >
        <div class="user-profile-content">
          <div class="user-avatar">
            <el-avatar
              :size="32"
              :icon="UserFilled"
              :src="userStore.userInfo.avatar"
            />
          </div>
          <div
            v-if="!collapsed"
            class="user-info"
          >
            <span class="username">{{ userStore.userInfo.username || '用户' }}</span>
            <el-tag
              size="small"
              effect="dark"
              type="info"
              class="role-tag"
            >
              {{ userStore.userInfo.role === 'SUPER_ADMIN' ? '管理员' : '用户' }}
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
              @click="handleLogout"
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
              @click="handleLogout"
            />
          </el-tooltip>
        </div>
      </div>
    </div>
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
  Document,
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

function handleLogoClick() {
  router.push('/dashboard')
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
.sidebar {
  background-color: #1a1a2e;
  transition: width 0.3s ease;
  overflow: hidden;
  border-right: 1px solid #2c2c44;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar.collapsed {
  width: 64px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60px;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
  flex-shrink: 0;
}

.logo h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.user-profile {
  padding: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background-color: #161625;
}

.user-profile-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  width: 100%;
  cursor: pointer;
  transition: background-color 0.3s;
  box-sizing: border-box;
}

.user-profile-content:hover {
  background-color: #1e1e30;
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  white-space: nowrap;
  flex: 1;
  text-align: left;
}

.username {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.role-tag {
  transform: scale(0.9);
  transform-origin: left center;
  width: fit-content;
}

.logout-btn {
  color: #909399;
  transition: all 0.2s;
  flex-shrink: 0;
}

.logout-btn:hover {
  color: #f56c6c;
  background-color: rgba(245, 108, 108, 0.1);
}

.logout-btn-collapsed {
  margin: 0 auto;
}
</style>
