<template>
  <el-card
    shadow="never"
    class="phase-report-tabs"
  >
    <el-tabs
      v-model="activeTab"
      type="card"
    >
      <!-- Phase 1 报告 -->
      <el-tab-pane
        label="Phase 1 报告"
        name="phase1"
      >
        <div class="reports-container">
          <ReportCard
            v-for="report in phase1Reports"
            :key="report.agent"
            :agent-name="report.name"
            :report="report.report"
          />
          <el-empty
            v-if="phase1Reports.length === 0"
            description="暂无报告"
          />
        </div>
      </el-tab-pane>

      <!-- Phase 2 报告 -->
      <el-tab-pane
        label="Phase 2 报告"
        name="phase2"
      >
        <div class="reports-container">
          <ReportCard
            v-for="report in phase2Reports"
            :key="report.agent"
            :agent-name="report.name"
            :report="report.report"
          />
          <el-empty
            v-if="phase2Reports.length === 0"
            description="暂无报告"
          />
        </div>
      </el-tab-pane>

      <!-- Phase 3 报告 -->
      <el-tab-pane
        label="Phase 3 报告"
        name="phase3"
      >
        <div class="reports-container">
          <ReportCard
            v-for="report in phase3Reports"
            :key="report.agent"
            :agent-name="report.name"
            :report="report.report"
          />
          <el-empty
            v-if="phase3Reports.length === 0"
            description="暂无报告"
          />
        </div>
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
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ReportCard from './ReportCard.vue'
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
const activeTab = ref('phase1')

// Phase 1 智能体列表
const phase1Agents = [
  'financial-news-analyst',
  'social-media-analyst',
  'china-market-analyst',
  'market-analyst',
  'fundamentals-analyst',
  'short-term-capital-analyst'
]

// Phase 2 智能体列表
const phase2Agents = [
  'bull-researcher',
  'bear-researcher',
  'research-manager',
  'trader'
]

// Phase 3 智能体列表
const phase3Agents = [
  'aggressive-debator',
  'neutral-debator',
  'conservative-debator',
  'risk-manager'
]

// 按阶段分组报告
const phase1Reports = computed(() => getReportsByAgents(phase1Agents))
const phase2Reports = computed(() => getReportsByAgents(phase2Agents))
const phase3Reports = computed(() => getReportsByAgents(phase3Agents))

function getReportsByAgents(agentSlugs: string[]) {
  const reports: { agent: string; name: string; report: string }[] = []
  for (const slug of agentSlugs) {
    const report = props.reports.get(slug)
    if (report) {
      const agentInfo = props.agents.get(slug)
      reports.push({
        agent: slug,
        name: getAgentDisplayName(slug, agentInfo?.name),
        report
      })
    }
  }
  return reports
}
</script>

<style scoped>
.phase-report-tabs {
  margin-top: 20px;
}

.reports-container {
  padding: 12px 0;
}
</style>
