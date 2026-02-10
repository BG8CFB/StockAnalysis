<script setup lang="ts">
import { ref, defineAsyncComponent, shallowRef, computed } from 'vue'
import { Cpu, Connection, ArrowRight } from '@element-plus/icons-vue'

// 当前激活的导航项（默认第一个：AI 模型管理）
const activeTab = ref('models')

// 异步组件定义
const AIModelManagementView = defineAsyncComponent(() =>
  import('./AIModelManagementView.vue')
)
const MCPServerManagementView = defineAsyncComponent(() =>
  import('./MCPServerManagementView.vue')
)

// 当前显示的组件
const currentComponent = shallowRef(AIModelManagementView)

// 菜单配置
const menuItems = [
  { key: 'models', label: 'AI 模型管理', icon: Cpu, component: AIModelManagementView },
  { key: 'mcp', label: 'MCP 服务器管理', icon: Connection, component: MCPServerManagementView },
]

// 切换标签
function handleTabChange(item: any) {
  activeTab.value = item.key
  currentComponent.value = item.component
}

// 获取当前激活项的标签
const activeLabel = computed(() => {
  const item = menuItems.find(i => i.key === activeTab.value)
  return item ? item.label : ''
})
</script>

<template>
  <div class="ai-management-container">
    <!-- 左侧导航菜单（桌面端） -->
    <div class="settings-sidebar desktop-sidebar">
      <div class="sidebar-header">
        <h2 class="title">
          <el-icon :size="20">
            <Cpu />
          </el-icon>
          AI 管理
        </h2>
        <p class="subtitle">
          配置 AI 模型与 MCP 服务器
        </p>
      </div>

      <div class="menu-list">
        <div
          v-for="item in menuItems"
          :key="item.key"
          class="menu-item"
          :class="{ active: activeTab === item.key }"
          @click="handleTabChange(item)"
        >
          <el-icon
            class="menu-icon"
            :size="18"
          >
            <component :is="item.icon" />
          </el-icon>
          <span class="menu-label">{{ item.label }}</span>
          <el-icon
            v-if="activeTab === item.key"
            class="active-indicator"
          >
            <ArrowRight />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- 右侧内容区域 -->
    <div class="settings-content">
      <div class="content-wrapper full-height">
        <transition
          name="fade-slide"
          mode="out-in"
        >
          <keep-alive>
            <component
              :is="currentComponent"
              :key="activeTab"
            />
          </keep-alive>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-management-container {
  display: flex;
  height: calc(100vh - 100px);
  background-color: var(--color-bg-page);
  gap: var(--space-5);
}

/* 左侧侧边栏 */
.settings-sidebar {
  width: var(--sidebar-width);
  background-color: var(--color-bg-container);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.sidebar-header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-secondary);
}

.title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.title .el-icon {
  color: var(--color-primary);
}

.subtitle {
  margin: var(--space-2) 0 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.menu-list {
  padding: var(--space-3) 0;
  flex: 1;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-regular);
  font-size: var(--font-size-base);
  border-left: 3px solid transparent;
  margin-bottom: 2px;
}

.menu-item:hover {
  background-color: var(--color-bg-light);
  color: var(--color-primary);
}

.menu-item.active {
  background-color: var(--color-primary-bg);
  color: var(--color-primary);
  border-left-color: var(--color-primary);
  font-weight: 500;
}

.menu-icon {
  margin-right: var(--space-3);
}

.active-indicator {
  margin-left: auto;
  font-size: var(--font-size-sm);
}

/* 右侧内容区 */
.settings-content {
  flex: 1;
  background-color: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-wrapper {
  padding: var(--space-6);
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

/* ============================================
   响应式设计 - 平板
   ============================================ */
@media (max-width: 1024px) {
  .sidebar-header {
    padding: var(--space-4);
  }

  .menu-item {
    padding: var(--space-3) var(--space-4);
  }

  .content-wrapper {
    padding: var(--space-5);
  }
}

/* ============================================
   响应式设计 - 移动端
   ============================================ */
@media (max-width: 768px) {
  .ai-management-container {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 100px);
  }

  .desktop-sidebar {
    display: none !important;
  }

  .settings-content {
    width: 100%;
    min-height: 500px;
  }

  .content-wrapper {
    padding: var(--space-4);
  }
}

/* ============================================
   响应式设计 - 小屏幕
   ============================================ */
@media (max-width: 480px) {
  .content-wrapper {
    padding: var(--space-3);
  }
}
</style>
