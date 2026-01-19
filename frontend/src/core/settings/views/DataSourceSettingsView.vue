<script setup lang="ts">
import { ref, defineAsyncComponent, shallowRef } from 'vue'
import { Setting, Refresh, Monitor, DataLine, ArrowRight } from '@element-plus/icons-vue'

// 当前激活的导航项（默认第一个：数据源状态监控）
const activeTab = ref('status')

// 异步组件定义
const UserDataSourceConfigView = defineAsyncComponent(() =>
  import('@modules/market_data/views/UserDataSourceConfigView.vue')
)
const DataSyncView = defineAsyncComponent(() =>
  import('@modules/market_data/views/DataSyncView.vue')
)
const DataSourceHealthView = defineAsyncComponent(() =>
  import('@modules/market_data/views/DataSourceHealthView.vue')
)

// 当前显示的组件
const currentComponent = shallowRef(DataSourceHealthView)

// 菜单配置（数据源状态监控放在第一位）
const menuItems = [
  { key: 'status', label: '数据源状态监控', icon: Monitor, component: DataSourceHealthView },
  { key: 'config', label: '数据源配置', icon: Setting, component: UserDataSourceConfigView },
  { key: 'sync', label: '数据同步', icon: Refresh, component: DataSyncView },
]

// 切换标签
function handleTabChange(item: any) {
  activeTab.value = item.key
  currentComponent.value = item.component
}
</script>

<template>
  <div class="datasource-settings-container">
    <!-- 左侧导航菜单 -->
    <div class="settings-sidebar">
      <div class="sidebar-header">
        <h2 class="title">
          <el-icon :size="20"><DataLine /></el-icon>
          数据源设置
        </h2>
        <p class="subtitle">配置数据源与同步策略</p>
      </div>

      <div class="menu-list">
        <div
          v-for="item in menuItems"
          :key="item.key"
          class="menu-item"
          :class="{ active: activeTab === item.key }"
          @click="handleTabChange(item)"
        >
          <el-icon class="menu-icon" :size="18">
            <component :is="item.icon" />
          </el-icon>
          <span class="menu-label">{{ item.label }}</span>
          <el-icon v-if="activeTab === item.key" class="active-indicator">
            <ArrowRight />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- 右侧内容区域 -->
    <div class="settings-content">
      <div class="content-wrapper full-height">
        <transition name="fade-slide" mode="out-in">
          <keep-alive>
            <component :is="currentComponent" :key="activeTab" />
          </keep-alive>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.datasource-settings-container {
  display: flex;
  height: calc(100vh - 100px);
  background-color: var(--color-bg-page);
  gap: 20px;
}

/* 左侧侧边栏 */
.settings-sidebar {
  width: 240px;
  background-color: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  flex-shrink: 0;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid var(--color-border);
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title .el-icon {
  color: var(--color-primary);
}

.subtitle {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.menu-list {
  padding: 12px 0;
  flex: 1;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-regular);
  font-size: 14px;
  border-left: 3px solid transparent;
  margin-bottom: 2px;
}

.menu-item:hover {
  background-color: var(--color-bg-light);
  color: var(--color-primary);
}

.menu-item.active {
  background-color: var(--color-primary-light-9);
  color: var(--color-primary);
  border-left-color: var(--color-primary);
  font-weight: 500;
}

.menu-icon {
  margin-right: 12px;
}

.active-indicator {
  margin-left: auto;
  font-size: 14px;
}

/* 右侧内容区 */
.settings-content {
  flex: 1;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-wrapper {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.content-wrapper.full-height {
  padding: 0;
}

/* 动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
