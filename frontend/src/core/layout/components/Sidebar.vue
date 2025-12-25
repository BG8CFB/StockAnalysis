<template>
  <el-aside
    :width="collapsed ? '64px' : '240px'"
    class="sidebar"
    :class="{ collapsed }"
  >
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
        <el-menu-item index="/analysis/single">
          <el-icon><TrendCharts /></el-icon>
          <template #title>
            单个分析
          </template>
        </el-menu-item>
        <el-menu-item index="/analysis/batch">
          <el-icon><Files /></el-icon>
          <template #title>
            批量分析
          </template>
        </el-menu-item>
      </el-sub-menu>

      <el-menu-item index="/task-center">
        <el-icon><List /></el-icon>
        <template #title>
          任务中心
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
      </el-sub-menu>

      <!-- 预留菜单项 -->
      <el-menu-item
        index="/terminal"
        disabled
      >
        <el-icon><Monitor /></el-icon>
        <template #title>
          交易终端
        </template>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  HomeFilled,
  TrendCharts,
  DataAnalysis,
  Search,
  Monitor,
  User,
  Setting,
  Tools,
  Files,
  List,
  ChatDotRound
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
</script>

<style scoped>
.sidebar {
  background-color: #1a1a2e;
  transition: width 0.3s ease;
  overflow: hidden;
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
}

.logo h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}


</style>
