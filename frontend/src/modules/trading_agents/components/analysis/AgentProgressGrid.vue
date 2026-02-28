<template>
  <div class="agent-progress-grid">
    <!-- 总进度条 -->
    <div class="overall-progress">
      <div class="progress-header">
        <span class="label">总进度</span>
        <span class="stats">{{ completedAgentsCount }}/{{ totalAgentsCount }}</span>
      </div>
      <el-progress
        :percentage="overallProgress"
        :stroke-width="12"
        :show-text="true"
      />
    </div>

    <!-- 各阶段智能体进度 -->
    <div
      v-for="phase in phaseProgress"
      :key="phase.id"
      class="phase-section"
    >
      <div class="phase-header">
        <span class="phase-name">{{ phase.name }}</span>
        <span class="phase-stats">
          {{ phase.completedCount }}/{{ phase.totalCount }}
        </span>
      </div>

      <div class="agents-grid">
        <div
          v-for="agent in phase.agents"
          :key="agent.slug"
          class="agent-card"
          :class="{
            'completed': agent.status === 'completed',
            'running': agent.status === 'running',
            'pending': agent.status === 'pending'
          }"
        >
          <div class="agent-icon">
            <el-icon
              v-if="agent.status === 'completed'"
              :size="20"
            >
              <CircleCheck />
            </el-icon>
            <el-icon
              v-else-if="agent.status === 'running'"
              :size="20"
              class="rotating"
            >
              <Loading />
            </el-icon>
            <el-icon
              v-else
              :size="20"
            >
              <Clock />
            </el-icon>
          </div>
          <div class="agent-name">
            {{ agent.displayName }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, Loading, Clock } from '@element-plus/icons-vue'
import type { AgentStatus } from '../../composables/useAnalysisProgress'

interface Props {
  agents: Map<string, AgentStatus>
  phaseExecutions: Array<any>
  totalAgents: number
  completedAgents: number
  phaseAgentCounts: Record<number, number>
}

const props = defineProps<Props>()

// 计算总进度
const overallProgress = computed(() => {
  if (props.totalAgents === 0) return 0
  return Math.round((props.completedAgents / props.totalAgents) * 100)
})

const totalAgentsCount = computed(() => props.totalAgents || props.agents.size)

const completedAgentsCount = computed(() => {
  let count = 0
  props.agents.forEach((agent) => {
    if (agent.status === 'completed') count++
  })
  return count
})

// 按阶段分组智能体
const phaseProgress = computed(() => {
  const phases = [
    { id: 1, name: 'Phase 1: 信息收集与基础分析' },
    { id: 2, name: 'Phase 2: 多空博弈与投资决策' },
    { id: 3, name: 'Phase 3: 策略风格与风险评估' },
    { id: 4, name: 'Phase 4: 总结智能体' }
  ]

  const phase1Agents = ['financial-news-analyst', 'social-media-analyst', 'china-market-analyst', 'market-analyst', 'fundamentals-analyst', 'short-term-capital-analyst']
  const phase2Agents = ['bull-researcher', 'bear-researcher', 'research-manager', 'trader']
  const phase3Agents = ['aggressive-debator', 'neutral-debator', 'conservative-debator', 'risk-manager']
  const phase4Agents = ['summarizer']

  return phases.map(phase => {
    let agentSlugs: string[] = []
    if (phase.id === 1) agentSlugs = phase1Agents
    else if (phase.id === 2) agentSlugs = phase2Agents
    else if (phase.id === 3) agentSlugs = phase3Agents
    else if (phase.id === 4) agentSlugs = phase4Agents

    const agents: any[] = []
    agentSlugs.forEach(slug => {
      const agent = props.agents.get(slug)
      if (agent) {
        agents.push({
          ...agent,
          displayName: agent.name || slug
        })
      }
    })

    return {
      ...phase,
      agents,
      completedCount: agents.filter(a => a.status === 'completed').length,
      totalCount: props.phaseAgentCounts[phase.id] || agents.length || 0
    }
  })
})
</script>

<style scoped>
.agent-progress-grid {
  padding: 16px;
}

.overall-progress {
  margin-bottom: 24px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.label {
  font-size: 14px;
  font-weight: 500;
}

.stats {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.phase-section {
  margin-bottom: 20px;
}

.phase-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.phase-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.phase-stats {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
}

.agent-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
  transition: all 0.3s;
}

.agent-card.completed {
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-5);
}

.agent-card.running {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.agent-card.pending {
  background: var(--el-fill-color-lighter);
}

.agent-icon {
  margin-bottom: 8px;
}

.agent-name {
  font-size: 12px;
  text-align: center;
  color: var(--el-text-color-regular);
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
