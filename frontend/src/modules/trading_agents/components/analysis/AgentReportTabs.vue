<template>
  <el-card
    shadow="never"
    class="agent-report-tabs"
  >
    <el-tabs
      v-model="activeTab"
      type="card"
    >
      <!-- 智能体报告标签（按执行顺序） -->
      <el-tab-pane
        v-for="report in sortedReports"
        :key="report.agent"
        :label="report.name"
        :name="report.agent"
      >
        <div
          class="report-content"
          v-html="renderMarkdown(report.report)"
        />
      </el-tab-pane>

      <!-- 最终报告 -->
      <el-tab-pane
        v-if="finalReport"
        label="最终报告"
        name="final"
      >
        <StreamingReport
          :content="finalReport"
          :recommendation="finalRecommendation"
          :buy-price="buyPrice"
          :sell-price="sellPrice"
          :is-complete="true"
          :is-streaming="false"
          :show-token-stats="false"
        />
      </el-tab-pane>

      <!-- 空状态 -->
      <el-tab-pane
        v-if="sortedReports.length === 0 && !finalReport"
        label="暂无报告"
        name="empty"
      >
        <el-empty description="暂无报告" />
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import StreamingReport from './StreamingReport.vue'
import type { AgentStatus } from '../../composables/useAnalysisProgress'
import { getAgentDisplayName } from '../../composables/useAnalysisProgress'

interface Props {
  reports: Map<string, string>
  agents: Map<string, AgentStatus>
  finalReport?: string
  finalRecommendation?: string | null  // 接受 string | null | undefined
  buyPrice?: number | null  // 接受 number | null | undefined
  sellPrice?: number | null  // 接受 number | null | undefined
}

const props = defineProps<Props>()
const activeTab = ref('')

// 智能体执行顺序（按阶段）
const agentOrder = [
  // Phase 1
  'financial-news-analyst',
  'social-media-analyst',
  'china-market-analyst',
  'market-analyst',
  'fundamentals-analyst',
  'short-term-capital-analyst',
  // Phase 2
  'bull-researcher',
  'bear-researcher',
  'research-manager',
  'trader',
  // Phase 3
  'aggressive-debator',
  'neutral-debator',
  'conservative-debator',
  'risk-manager',
  // Phase 4
  'summarizer'
]

// 渲染 Markdown（加 DOMPurify 净化防止 XSS）
function renderMarkdown(content: string): string {
  if (!content) return ''
  try {
    const html = marked.parse(content) as string
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
    })
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return DOMPurify.sanitize(content)
  }
}

// 按智能体顺序排序报告（纯计算，不含副作用）
const sortedReports = computed(() => {
  const reports: { agent: string; name: string; report: string }[] = []

  for (const slug of agentOrder) {
    const report = props.reports.get(slug)
    if (report) {
      const agentInfo = props.agents.get(slug)
      const displayName = getAgentDisplayName(slug, agentInfo?.name)
      reports.push({ agent: slug, name: displayName, report })
    }
  }

  props.reports.forEach((report, slug) => {
    if (!agentOrder.includes(slug) && slug !== 'final_report') {
      const agentInfo = props.agents.get(slug)
      const displayName = getAgentDisplayName(slug, agentInfo?.name)
      reports.push({ agent: slug, name: displayName, report })
    }
  })

  return reports
})

// 用 watch 初始化 activeTab，避免在 computed 中产生副作用
watch(
  sortedReports,
  (newReports) => {
    if (!activeTab.value) {
      if (newReports.length > 0) {
        activeTab.value = newReports[0].agent
      } else if (props.finalReport) {
        activeTab.value = 'final'
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.agent-report-tabs {
  margin-top: 20px;
}

.agent-report-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.agent-report-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 16px;
}

.agent-report-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.report-content {
  padding: 20px;
  line-height: 1.8;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.report-content :deep(h1) {
  font-size: 24px;
  margin: 20px 0 16px;
  font-weight: 600;
}

.report-content :deep(h2) {
  font-size: 20px;
  margin: 18px 0 14px;
  font-weight: 600;
}

.report-content :deep(h3) {
  font-size: 18px;
  margin: 16px 0 12px;
  font-weight: 600;
}

.report-content :deep(p) {
  margin: 12px 0;
}

.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
}

.report-content :deep(li) {
  margin: 6px 0;
}

.report-content :deep(code) {
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.report-content :deep(pre) {
  background: var(--el-fill-color-light);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.report-content :deep(blockquote) {
  border-left: 4px solid var(--el-color-primary);
  padding-left: 16px;
  margin: 12px 0;
  color: var(--el-text-color-secondary);
}
</style>
