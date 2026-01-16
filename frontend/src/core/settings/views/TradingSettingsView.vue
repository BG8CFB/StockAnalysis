<script setup lang="ts">
import { ref, defineAsyncComponent, shallowRef } from 'vue'
import { DataAnalysis, TrendCharts, Setting, ArrowRight, Cpu } from '@element-plus/icons-vue'

// 当前激活的导航项（默认第一个）
const activeTab = ref('agent')

// 异步组件定义
const AgentConfigView = defineAsyncComponent(() =>
  import('@modules/trading_agents/views/settings/AgentConfigView.vue')
)
const AnalysisSettingsView = defineAsyncComponent(() =>
  import('@modules/trading_agents/views/settings/AnalysisSettingsView.vue')
)

// 当前显示的组件
const currentComponent = shallowRef(AgentConfigView)

// 菜单配置
const menuItems = [
  { key: 'agent', label: '智能体配置', icon: DataAnalysis, component: AgentConfigView },
  { key: 'analysis', label: '分析设置', icon: TrendCharts, component: AnalysisSettingsView },
]

// 切换标签
function handleTabChange(item: any) {
  activeTab.value = item.key
  currentComponent.value = item.component
}
</script>

<template>
  <div class="trading-settings-container">
    <!-- 左侧导航菜单 -->
    <div class="settings-sidebar">
      <div class="sidebar-header">
        <h2 class="title">
          <el-icon class="title-icon"><Cpu /></el-icon>
          Trading Agent
        </h2>
        <p class="subtitle">配置智能体参数与分析流程</p>
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
.trading-settings-container {
  display: flex;
  height: calc(100vh - 100px); /* 减去 header 高度，确保不滚动整个页面 */
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

/* 移除原来的左侧色条 */
/* .title::before {
  content: '';
  display: block;
  width: 4px;
  height: 18px;
  background-color: var(--color-primary);
  border-radius: 2px;
} */

.title-icon {
  color: var(--color-primary);
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  margin-bottom: 2px; /* 紧凑间距 */
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
  overflow: hidden; /* 防止内容溢出 */
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