<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <n-layout-sider
      v-model:value="collapsed"
      :collapsed-width="64"
      :width="240"
      show-trigger
      bordered
      collapse-mode="width"
    >
      <div class="logo">
        <img src="/logo.svg" alt="Logo" v-if="!collapsed" />
        <img src="/logo-icon.svg" alt="Logo" v-else />
        <span v-if="!collapsed">TradingAgents-CN</span>
      </div>

      <!-- 动态菜单 -->
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :options="menuOptions"
        :value="currentRoute"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <!-- 主要内容区域 -->
    <n-layout>
      <!-- 顶部导航栏 -->
      <n-layout-header bordered class="header">
        <div class="header-left">
          <n-button quaternary circle @click="collapsed = !collapsed">
            <template #icon>
              <n-icon>
                <MenuOutlined />
              </n-icon>
            </template>
          </n-button>

          <!-- 面包屑导航 -->
          <n-breadcrumb class="breadcrumb">
            <n-breadcrumb-item
              v-for="item in breadcrumbs"
              :key="item.path"
              @click="navigateTo(item.path)"
            >
              {{ item.title }}
            </n-breadcrumb-item>
          </n-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 通知 -->
          <n-dropdown :options="notificationOptions" @select="handleNotificationSelect">
            <n-badge :value="unreadNotifications" :max="99">
              <n-button quaternary circle>
                <template #icon>
                  <n-icon>
                    <BellOutlined />
                  </n-icon>
                </template>
              </n-button>
            </n-badge>
          </n-dropdown>

          <!-- 用户菜单 -->
          <n-dropdown :options="userMenuOptions" @select="handleUserMenuSelect">
            <n-button quaternary>
              <template #icon>
                <n-icon>
                  <UserOutlined />
                </n-icon>
              </template>
              {{ userStore.user?.username || 'User' }}
            </n-button>
          </n-dropdown>
        </div>
      </n-layout-header>

      <!-- 页面内容 -->
      <n-layout-content class="content">
        <router-view />
      </n-layout-content>
    </n-layout>

    <!-- 全局加载指示器 -->
    <n-loading-bar-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-message-provider>
            <div id="global-providers"></div>
          </n-message-provider>
        </n-notification-provider>
      </n-dialog-provider>
    </n-loading-bar-provider>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
  NButton,
  NIcon,
  NBreadcrumb,
  NBreadcrumbItem,
  NDropdown,
  NBadge,
  NLoadingBarProvider,
  NDialogProvider,
  NNotificationProvider,
  NMessageProvider
} from 'naive-ui'
import {
  MenuOutlined,
  BellOutlined,
  UserOutlined,
  DashboardOutlined,
  SettingOutlined,
  LogoutOutlined
} from '@vicons/ionicons5'

import { useUserStore } from '@/modules/user_management/store'
import { moduleLoader } from '@/core/router/module_loader'
import { eventBus, EventTypes } from '@/core/events/bus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 响应式状态
const collapsed = ref(false)
const currentRoute = ref(route.path)

// 计算属性
const menuOptions = computed(() => {
  const routes = moduleLoader.getMenuRoutes()
  return routes.map(routeToMenuItem)
})

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta && item.meta.title)
  return matched.map(item => ({
    title: item.meta?.title || item.name,
    path: item.path
  }))
})

const unreadNotifications = computed(() => {
  return eventState.notifications.filter(n => !n.read).length
})

const userMenuOptions = [
  {
    label: '个人设置',
    key: 'profile',
    icon: () => h(UserOutlined)
  },
  {
    label: '系统设置',
    key: 'settings',
    icon: () => h(SettingOutlined)
  },
  {
    type: 'divider'
  },
  {
    label: '退出登录',
    key: 'logout',
    icon: () => h(LogoutOutlined)
  }
]

const notificationOptions = [
  {
    label: '查看所有通知',
    key: 'view-all'
  },
  {
    label: '清除所有通知',
    key: 'clear-all'
  }
]

// 方法
function routeToMenuItem(route: any): any {
  return {
    label: route.meta?.title || route.name,
    key: route.path,
    icon: () => route.meta?.icon ? h(resolveComponent(route.meta.icon)) : null,
    children: route.children?.map(routeToMenuItem)
  }
}

function handleMenuSelect(key: string) {
  router.push(key)
}

function navigateTo(path: string) {
  router.push(path)
}

function handleUserMenuSelect(key: string) {
  switch (key) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}

function handleNotificationSelect(key: string) {
  switch (key) {
    case 'view-all':
      router.push('/notifications')
      break
    case 'clear-all':
      eventState.notifications.length = 0
      break
  }
}

// 生命周期
onMounted(() => {
  // 监听路由变化
  watch(() => route.path, (newPath) => {
    currentRoute.value = newPath
  })

  // 发布系统启动事件
  eventBus.emit(EventTypes.SYSTEM_STARTUP, {
    modules: moduleLoader.getLoadedModules().map(m => m.name)
  })
})

// 导入h和resolveComponent
import { h, resolveComponent } from 'vue'
import { eventState } from '@/core/events/bus'
</script>

<style scoped>
.main-layout {
  height: 100vh;
  display: flex;
}

.logo {
  display: flex;
  align-items: center;
  padding: 16px;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid var(--n-border-color);
}

.logo img {
  height: 32px;
  margin-right: 8px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb {
  margin-left: 16px;
}

.content {
  padding: 16px;
  overflow: auto;
}
</style>