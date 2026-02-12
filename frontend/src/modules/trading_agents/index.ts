/**
 * TradingAgents 模块入口
 */

// 设置模块
export { default as AgentConfigView } from './views/settings/AgentConfigView.vue'
export { default as AnalysisSettingsView } from './views/settings/AnalysisSettingsView.vue'

// 分析模块
export { default as SingleAnalysisView } from './views/analysis/SingleAnalysisView.vue'
export { default as BatchAnalysisView } from './views/analysis/BatchAnalysisView.vue'
export { default as AnalysisDetailView } from './views/analysis/AnalysisDetailView.vue'

// 任务中心
export { default as TaskCenterView } from './views/task/TaskCenterView.vue'

// 管理员页面
export { default as AdminAllTasksView } from './views/admin/AllTasksView.vue'

// Composables
export * from './composables'

// 组件
export { default as AgentStatusCard } from './components/analysis/AgentStatusCard.vue'
export { default as ToolCallLog } from './components/analysis/ToolCallLog.vue'
export { default as ReportCard } from './components/analysis/ReportCard.vue'
export { default as StreamingReport } from './components/analysis/StreamingReport.vue'
