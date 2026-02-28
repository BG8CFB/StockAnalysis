<template>
  <div class="streaming-report">
    <div class="report-header">
      <div class="header-left">
        <el-icon
          :class="streamClass"
          :size="20"
        >
          <Document />
        </el-icon>
        <h3>最终分析报告</h3>
      </div>
      <div class="header-right">
        <el-tag
          v-if="isStreaming"
          type="primary"
          size="small"
        >
          生成中...
        </el-tag>
        <el-tag
          v-else-if="isComplete"
          type="success"
          size="small"
        >
          已完成
        </el-tag>
      </div>
    </div>

    <!-- 流式输出内容 -->
    <div class="report-content">
      <div
        v-if="displayContent"
        class="markdown-content"
        v-html="renderedContent"
      />
      <el-skeleton
        v-else
        :rows="5"
        animated
      />
    </div>

    <!-- 推荐结果卡片 -->
    <div
      v-if="recommendation"
      class="recommendation-card"
    >
      <div class="recommendation-header">
        <span class="recommendation-label">投资建议</span>
        <el-tag
          :type="getRecommendationType()"
          size="large"
        >
          {{ recommendation }}
        </el-tag>
      </div>
      <div class="recommendation-body">
        <div
          v-if="buyPrice != null"
          class="price-item"
        >
          <span class="price-label">建议买入价:</span>
          <span class="price-value">¥{{ buyPrice.toFixed(2) }}</span>
        </div>
        <div
          v-if="sellPrice != null"
          class="price-item"
        >
          <span class="price-label">建议卖出价:</span>
          <span class="price-value">¥{{ sellPrice.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <!-- Token 使用统计 -->
    <div
      v-if="showTokenStats"
      class="token-stats"
    >
      <div class="stat-item">
        <span class="stat-label">Token 使用:</span>
        <span class="stat-value">{{ formatTokenCount(totalTokens) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">估算成本:</span>
        <span class="stat-value">¥{{ estimatedCost.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

interface Props {
  content?: string
  recommendation?: string | null  // 接受字符串类型（如 "买入"、"卖出"、"持有"）
  buyPrice?: number | null
  sellPrice?: number | null
  totalTokens?: number
  estimatedCost?: number
  isStreaming: boolean
  isComplete: boolean
  showTokenStats: boolean
}

const props = withDefaults(defineProps<Props>(), {
  content: '',
  recommendation: null,
  buyPrice: null,
  sellPrice: null,
  totalTokens: 0,
  estimatedCost: 0,
  isStreaming: false,
  isComplete: false,
  showTokenStats: true,
})

// 显示的内容（使用 computed 替代冗余的 ref + watch 镜像）
const displayContent = computed(() => props.content || '')

// 流动动画类
const streamClass = computed(() => {
  return props.isStreaming ? 'streaming' : ''
})

// 渲染的内容（使用 marked + DOMPurify 替代有缺陷的自定义 formatMarkdown）
const renderedContent = computed(() => {
  if (!displayContent.value) return ''
  try {
    const html = marked.parse(displayContent.value) as string
    return DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      ALLOWED_TAGS: [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'del', 'pre', 'code',
        'a', 'ol', 'ul', 'li', 'p', 'br',
        'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr', 'img',
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'src', 'alt'],
      ALLOW_DATA_ATTR: false,
    })
  } catch {
    return DOMPurify.sanitize(displayContent.value)
  }
})

/**
 * 获取推荐结果对应的标签类型
 */
function getRecommendationType(): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    '买入': 'success',
    '卖出': 'danger',
    '持有': 'info',
  }
  return typeMap[props.recommendation || ''] || 'info'
}

/**
 * 格式化 Token 数量
 */
function formatTokenCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`
  }
  return count.toString()
}

</script>

<style scoped>
.streaming-report {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  overflow: hidden;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left > .el-icon {
  color: var(--el-color-primary);
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

/* 修正：.streaming 和 .el-icon 在同一元素上，使用并列选择器而非后代选择器 */
.el-icon.streaming {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.report-content {
  padding: 20px;
  min-height: 200px;
}

.markdown-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--el-text-color-primary);
}

.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

.markdown-content :deep(h2) {
  font-size: 20px;
}

.markdown-content :deep(h3) {
  font-size: 18px;
}

.markdown-content :deep(h4) {
  font-size: 16px;
}

.markdown-content :deep(.code-block) {
  margin: 12px 0;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  overflow-x: auto;
}

.markdown-content :deep(.code-block code) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.markdown-content :deep(.inline-code) {
  padding: 2px 6px;
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.markdown-content :deep(ol),
.markdown-content :deep(ul) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.recommendation-card {
  margin: 0 20px 20px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.recommendation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.recommendation-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

.recommendation-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.price-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.price-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.token-stats {
  display: flex;
  gap: 24px;
  padding: 12px 20px;
  background: var(--el-fill-color-lighter);
  border-top: 1px solid var(--el-border-color);
}

.stat-item {
  display: flex;
  gap: 8px;
  font-size: 14px;
}

.stat-label {
  color: var(--el-text-color-secondary);
}

.stat-value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}
</style>
