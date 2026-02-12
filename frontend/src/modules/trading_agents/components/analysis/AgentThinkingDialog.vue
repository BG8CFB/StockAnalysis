<template>
  <el-dialog
    :model-value="props.visible"
    :title="`${agentName} - 思考过程`"
    width="70%"
    :close-on-click-modal="false"
    @update:model-value="handleVisibleChange"
    @close="handleClose"
  >
    <!-- 加载状态 -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <el-skeleton
        :rows="8"
        animated
      />
    </div>

    <!-- 思考内容 -->
    <div
      v-else-if="thinkingContent"
      class="thinking-content"
    >
      <div
        class="markdown-body"
        v-html="renderedContent"
      />
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="暂无思考过程记录"
    />

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button
          type="primary"
          @click="handleCopy"
        >
          复制内容
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

interface Props {
  visible: boolean
  agentName: string
  thinkingContent: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// 渲染 Markdown 内容
const renderedContent = computed(() => {
  if (!props.thinkingContent) return ''

  try {
    // 配置 marked 选项
    marked.setOptions({
      breaks: true, // 支持换行
      gfm: true, // 启用 GitHub 风格 Markdown
    })

    // 解析 Markdown
    const rawHtml = marked(props.thinkingContent) as string

    // 清理 HTML（防止 XSS）
    return DOMPurify.sanitize(rawHtml)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return `<pre>${props.thinkingContent}</pre>`
  }
})

// 关闭对话框
const handleClose = () => {
  emit('update:visible', false)
}

// 处理对话框可见性变化
const handleVisibleChange = (value: boolean) => {
  emit('update:visible', value)
}

// 复制内容
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(props.thinkingContent)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped lang="scss">
.thinking-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;

  .markdown-body {
    line-height: 1.8;
    color: #303133;

    // 标题样式
    :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
      margin-top: 24px;
      margin-bottom: 16px;
      font-weight: 600;
      line-height: 1.25;
      color: #1f2937;
    }

    :deep(h1) {
      font-size: 2em;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 0.3em;
    }

    :deep(h2) {
      font-size: 1.5em;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 0.3em;
    }

    :deep(h3) {
      font-size: 1.25em;
    }

    // 段落样式
    :deep(p) {
      margin-top: 0;
      margin-bottom: 16px;
    }

    // 列表样式
    :deep(ul), :deep(ol) {
      margin-top: 0;
      margin-bottom: 16px;
      padding-left: 2em;
    }

    :deep(li) {
      margin-bottom: 4px;
    }

    // 代码块样式
    :deep(pre) {
      background-color: #1f2937;
      color: #f9fafb;
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
      margin-bottom: 16px;

      code {
        background-color: transparent;
        color: inherit;
        padding: 0;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.9em;
      }
    }

    :deep(code) {
      background-color: #f3f4f6;
      color: #ef4444;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 0.9em;
    }

    // 引用样式
    :deep(blockquote) {
      margin: 0 0 16px 0;
      padding: 0 1em;
      color: #6b7280;
      border-left: 0.25em solid #d1d5db;
    }

    // 表格样式
    :deep(table) {
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 16px;

      th, td {
        padding: 8px 16px;
        border: 1px solid #e5e7eb;
        text-align: left;
      }

      th {
        background-color: #f9fafb;
        font-weight: 600;
      }

      tr:nth-child(even) {
        background-color: #f9fafb;
      }
    }

    // 链接样式
    :deep(a) {
      color: #3b82f6;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }

    // 分隔线
    :deep(hr) {
      height: 0.25em;
      padding: 0;
      margin: 24px 0;
      background-color: #e5e7eb;
      border: 0;
    }

    // 图片样式
    :deep(img) {
      max-width: 100%;
      height: auto;
      border-radius: 4px;
    }

    // 强调样式
    :deep(strong) {
      font-weight: 600;
      color: #1f2937;
    }

    :deep(em) {
      font-style: italic;
    }

    // 删除线
    :deep(del) {
      text-decoration: line-through;
      color: #6b7280;
    }
  }
}

.loading-container {
  padding: 40px 20px;
}
</style>
