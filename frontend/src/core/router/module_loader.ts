/**
 * 模块路由加载器
 * 自动加载 modules 目录下的路由
 */
import type { RouteRecordRaw } from 'vue-router'

// 动态导入模块路由
const moduleRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/init',
    name: 'Init',
    component: () => import('@core/system/views/InitView.vue'),
    meta: { requiresAuth: false, title: '系统初始化' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@core/auth/views/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@core/auth/views/RegisterView.vue'),
    meta: { requiresAuth: false, title: '注册' },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@modules/dashboard/views/DashboardView.vue'),
    meta: { requiresAuth: true, title: '仪表板' },
  },
  {
    path: '/screener',
    name: 'Screener',
    component: () => import('@modules/screener/views/ScreenerView.vue'),
    meta: { requiresAuth: true, title: '智能选股' },
  },
  {
    path: '/ask-stock',
    name: 'AskStock',
    component: () => import('@modules/ask_stock/views/AskStockView.vue'),
    meta: { requiresAuth: true, title: 'AI 问股' },
  },
  // 市场数据模块 - 系统监控（保留原有路由作为兼容）
  {
    path: '/core/monitor/data-source-status',
    name: 'DataSourceMonitor',
    component: () => import('@modules/market_data/views/DataSourceHealthView.vue'),
    meta: { requiresAuth: true, title: '数据源状态监控' },
  },
  // 数据源设置（统一入口）
  {
    path: '/settings/data-sources',
    name: 'SettingsDataSources',
    component: () => import('@core/settings/views/DataSourceSettingsView.vue'),
    meta: { requiresAuth: true, title: '数据源设置' },
  },
  // 市场数据模块 - 保留原有路由作为兼容
  {
    path: '/settings/data-sync',
    name: 'DataSync',
    component: () => import('@modules/market_data/views/DataSyncView.vue'),
    meta: { requiresAuth: true, title: '数据同步' },
  },
  // TradingAgents 分析模块
  {
    path: '/trading-agents/analysis/single',
    name: 'SingleAnalysis',
    component: () => import('@modules/trading_agents/views/analysis/SingleAnalysisView.vue'),
    meta: { requiresAuth: true, title: '单股分析' },
  },
  {
    path: '/trading-agents/analysis/batch',
    name: 'BatchAnalysis',
    component: () => import('@modules/trading_agents/views/analysis/BatchAnalysisView.vue'),
    meta: { requiresAuth: true, title: '批量分析' },
  },
  {
    path: '/trading-agents/analysis/:taskId',
    name: 'AnalysisDetail',
    component: () => import('@modules/trading_agents/views/analysis/AnalysisDetailView.vue'),
    meta: { requiresAuth: true, title: '分析详情' },
  },
  // TradingAgents 任务中心（融合版）
  {
    path: '/trading-agents/tasks',
    name: 'TaskCenter',
    component: () => import('@modules/trading_agents/views/task/TaskCenterView.vue'),
    meta: { requiresAuth: true, title: '任务中心' },
  },
  // TradingAgents 历史对比分析
  {
    path: '/trading-agents/compare',
    name: 'HistoryCompare',
    component: () => import('@modules/trading_agents/views/compare/HistoryCompareView.vue'),
    meta: { requiresAuth: true, title: '历史对比' },
  },
  {
    path: '/settings/users',
    name: 'SettingsUsers',
    component: () => import('@core/admin/views/UserManagementView.vue'),
    meta: { requiresAuth: true, title: '用户管理', adminOnly: true },
  },
  {
    path: '/settings/system',
    name: 'SettingsSystem',
    component: () => import('@core/settings/views/SystemSettingsView.vue'),
    meta: { requiresAuth: true, title: '系统设置', adminOnly: true },
  },
  // AI 模型管理（核心设置模块）
  {
    path: '/settings/ai-models',
    name: 'SettingsAIModels',
    component: () => import('@core/settings/views/AIModelManagementView.vue'),
    meta: { requiresAuth: true, title: 'AI 模型管理' },
  },
  // MCP 服务器管理
  {
    path: '/settings/mcp-servers',
    name: 'SettingsMCPServers',
    component: () => import('@core/settings/views/MCPServerManagementView.vue'),
    meta: { requiresAuth: true, title: 'MCP 服务器管理' },
  },
  // Trading Agent 设置（统一入口）
  {
    path: '/settings/trading',
    name: 'SettingsTrading',
    component: () => import('@core/settings/views/TradingSettingsView.vue'),
    meta: { requiresAuth: true, title: 'Trading Agent 设置' },
  },
  // TradingAgents 设置模块（保留原有路由作为兼容）
  {
    path: '/settings/trading-agents/agent-config',
    name: 'TradingAgentsAgentConfig',
    component: () => import('@modules/trading_agents/views/settings/AgentConfigView.vue'),
    meta: { requiresAuth: true, title: '智能体配置' },
  },
  {
    path: '/settings/trading-agents/analysis',
    name: 'TradingAgentsAnalysis',
    component: () => import('@modules/trading_agents/views/settings/AnalysisSettingsView.vue'),
    meta: { requiresAuth: true, title: '分析设置' },
  },
  // TradingAgents 管理员页面
  {
    path: '/admin/all-tasks',
    name: 'AdminAllTasks',
    component: () => import('@modules/trading_agents/views/admin/AllTasksView.vue'),
    meta: {requiresAuth: true, title: '所有任务管理', adminOnly: true},
  },
  {
    path: '/admin/alerts',
    name: 'AdminAlerts',
    component: () => import('@modules/trading_agents/views/admin/AlertsView.vue'),
    meta: { requiresAuth: true, title: '告警管理', adminOnly: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@core/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

export default moduleRoutes
