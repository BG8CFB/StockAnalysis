<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 根据当前路由获取页面标题
const pageTitle = computed(() => {
  const title = route.meta?.title as string
  return title || '全局设置'
})

// 判断是否需要显示设置页面头部
// 有二级导航的页面不需要显示头部：AI 管理、数据源设置、Trading Agent 设置
const showHeader = computed(() => {
  const path = route.path
  // 这些路径有二级导航，不需要显示头部
  const hasSecondaryNav = [
    '/settings/ai-management',
    '/settings/data-sources',
    '/settings/trading',
    '/settings/trading-agents/agent-config',
    '/settings/trading-agents/analysis'
  ]
  return !hasSecondaryNav.some(navPath => path.startsWith(navPath))
})
</script>

<template>
  <div class="settings-layout">
    <!-- 设置页面头部 - 仅在没有二级导航的页面显示 -->
    <div v-if="showHeader" class="settings-header">
      <h2 class="settings-title">{{ pageTitle }}</h2>
      <div class="settings-breadcrumb">
        <span class="breadcrumb-item">全局设置</span>
        <el-icon class="breadcrumb-separator"><ArrowRight /></el-icon>
        <span class="breadcrumb-item current">{{ pageTitle }}</span>
      </div>
    </div>

    <!-- 设置内容区域 -->
    <div class="settings-content">
      <el-card class="settings-card">
        <router-view />
      </el-card>
    </div>
  </div>
</template>

<script lang="ts">
// 单独导出 ArrowRight 组件引用
import { ArrowRight } from '@element-plus/icons-vue'
export { ArrowRight }
</script>

<style scoped>
.settings-layout {
  padding: var(--space-6);
  background-color: var(--color-bg-page);
  min-height: 100%;
}

.settings-header {
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-secondary);
}

.settings-title {
  font-size: var(--font-size-xxxl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
}

.settings-breadcrumb {
  display: flex;
  align-items: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.breadcrumb-item {
  display: flex;
  align-items: center;
}

.breadcrumb-item.current {
  color: var(--color-primary);
  font-weight: 500;
}

.breadcrumb-separator {
  margin: 0 var(--space-2);
  font-size: var(--font-size-xs);
}

.settings-content {
  width: 100%;
  max-width: var(--max-width-content);
  margin: 0 auto;
}

.settings-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.settings-card :deep(.el-card__body) {
  padding: var(--space-6);
}

/* 响应式设计 - 平板 */
@media (max-width: 1024px) {
  .settings-layout {
    padding: var(--space-5);
  }

  .settings-title {
    font-size: var(--font-size-xxl);
  }

  .settings-card :deep(.el-card__body) {
    padding: var(--space-5);
  }
}

/* 响应式设计 - 移动端 */
@media (max-width: 768px) {
  .settings-layout {
    padding: var(--space-4);
  }

  .settings-header {
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-3);
  }

  .settings-title {
    font-size: var(--font-size-xl);
  }

  .settings-card :deep(.el-card__body) {
    padding: var(--space-4);
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .settings-layout {
    padding: var(--space-3);
  }

  .settings-title {
    font-size: var(--font-size-lg);
  }

  .settings-card :deep(.el-card__body) {
    padding: var(--space-3);
  }
}
</style>
