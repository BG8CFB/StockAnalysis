<template>
  <el-card shadow="never" class="agent-report-tabs">
    <el-tabs v-model="activeTab" type="card">
      <!-- 智能体报告标签（按执行顺序） -->
      <el-tab-pane
        v-for="report in sortedReports"
        :key="report.agent"
        :label="report.name"
        :name="report.agent"
      >
        <div class="report-content" v-html="renderMarkdown(report.report)"></div>
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
import { ref, computed } from 'vue'
import { marked } from 'marked'
import StreamingReport from './StreamingReport.vue'
import type { AgentStatus } from '../../composables/useAnalysisProgress'
import { getAgentDisplayName, AGENT_NAME_MAPPING } from '../../composables/useAnalysisProgress'

interface Props {
  reports: Map<string, string>
  agents: Map<string, AgentStatus>
  finalReport?: string
  finalRecommendation?: string
  buyPrice?: number
  sellPrice?: number
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

// 渲染 Markdown
function renderMarkdown(content: string): string {
  if (!content) return ''
  try {
    return marked(content) as string
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return content
  }
}

// 按智能体顺序排序报告
const sortedReports = computed(() => {
  const reports: { agent: string; name: string; report: string }[] = []

  // 按预定义顺序添加报告
  for (const slug of agentOrder) {
    const report = props.reports.get(slug)
    if (report) {
      const agentInfo = props.agents.get(slug)
      // 使用 getAgentDisplayName 获取中文名称
      const displayName = getAgentDisplayName(slug, agentInfo?.name)
      reports.push({
        agent: slug,
        name: displayName,
        report
      })
    }
  }

  // 添加其他未在列表中的报告
  props.reports.forEach((report, slug) => {
    if (!agentOrder.includes(slug) && slug !== 'final_report') {
      const agentInfo = props.agents.get(slug)
      const displayName = getAgentDisplayName(slug, agentInfo?.name)
      reports.push({
        agent: slug,
        name: displayName,
        report
      })
    }
  })

  // 自动激活第一个标签
  if (reports.length > 0 && !activeTab.value) {
    activeTab.value = reports[0].agent
  } else if (props.finalReport && !activeTab.value) {
    activeTab.value = 'final'
  }

  return reports
})
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
