<template>
  <div class="report-card">
    <div class="card-header">
      <div class="header-left">
        <el-icon
          class="report-icon"
          :size="18"
        >
          <Document />
        </el-icon>
        <span class="agent-name">{{ agentName }}</span>
      </div>
      <el-tag
        type="success"
        size="small"
      >
        已完成
      </el-tag>
    </div>

    <div class="card-body">
      <div
        class="report-content"
        v-html="renderedContent"
      />
    </div>

    <div class="card-footer">
      <el-button
        text
        type="primary"
        :icon="expanded ? ArrowUp : ArrowDown"
        @click="toggleExpand"
      >
        {{ expanded ? '收起' : '展开详情' }}
      </el-button>
      <el-button
        text
        type="primary"
        :icon="CopyDocument"
        @click="copyReport"
      >
        复制
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, ArrowUp, ArrowDown, CopyDocument } from '@element-plus/icons-vue'

interface Props {
  agentName: string
  report: string
}

const props = defineProps<Props>()

const expanded = ref(false)

// 渲染的内容
const renderedContent = computed(() => {
  const content = props.report || '暂无报告内容'
  return formatMarkdown(content)
})

// 切换展开/收起
function toggleExpand() {
  expanded.value = !expanded.value
}

// 复制报告
function copyReport() {
  navigator.clipboard.writeText(props.report).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

/**
 * 简单的 Markdown 渲染
 * 生产环境建议使用专门的 Markdown 渲染库
 */
function formatMarkdown(text: string): string {
  return text
    // 标题
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    // 粗体
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    // 代码块
    .replace(/```([\s\S]*?)```/gim, '<pre class="code-block"><code>$1</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/gim, '<code class="inline-code">$1</code>')
    // 链接
    .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
    // 列表
    .replace(/^\d+\. (.*$)/gim, '<ol><li>$1</li></ol>')
    .replace(/^- (.*$)/gim, '<ul><li>$1</li></ul>')
    // 换行
    .replace(/\n\n/gim, '</p><p>')
    .replace(/\n/gim, '<br>')
}
</script>

<style scoped>
.report-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-icon {
  color: var(--el-color-primary);
}

.agent-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.card-body {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.report-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--el-text-color-primary);
}

.report-content :deep(h2),
.report-content :deep(h3),
.report-content :deep(h4) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

.report-content :deep(h2) {
  font-size: 18px;
}

.report-content :deep(h3) {
  font-size: 16px;
}

.report-content :deep(h4) {
  font-size: 14px;
}

.report-content :deep(.code-block) {
  margin: 12px 0;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  overflow-x: auto;
}

.report-content :deep(.code-block code) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.report-content :deep(.inline-code) {
  padding: 2px 6px;
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.report-content :deep(a) {
  color: var(--el-color-primary);
  text-decoration: none;
}

.report-content :deep(a:hover) {
  text-decoration: underline;
}

.report-content :deep(ol),
.report-content :deep(ul) {
  margin: 8px 0;
  padding-left: 24px;
}

.report-content :deep(li) {
  margin: 4px 0;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-fill-color-lighter);
}
</style>
