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
    path: '/analysis/single',
    name: 'SingleAnalysis',
    component: () => import('@modules/analysis/views/SingleAnalysisView.vue'),
    meta: { requiresAuth: true, title: '单个分析' },
  },
  {
    path: '/analysis/batch',
    name: 'BatchAnalysis',
    component: () => import('@modules/analysis/views/BatchAnalysisView.vue'),
    meta: { requiresAuth: true, title: '批量分析' },
  },
  {
    path: '/task-center',
    name: 'TaskCenter',
    component: () => import('@modules/task_center/views/TaskCenterView.vue'),
    meta: { requiresAuth: true, title: '任务中心' },
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
  // TradingAgents 设置模块
  {
    path: '/settings/trading-agents/models',
    name: 'TradingAgentsModels',
    component: () => import('@modules/trading_agents/views/ModelManagementView.vue'),
    meta: { requiresAuth: true, title: 'AI 模型管理' },
  },
  {
    path: '/settings/trading-agents/mcp-servers',
    name: 'TradingAgentsMCPServers',
    component: () => import('@modules/trading_agents/views/MCPServerManagementView.vue'),
    meta: { requiresAuth: true, title: 'MCP 服务器管理' },
  },
  {
    path: '/settings/trading-agents/agent-config',
    name: 'TradingAgentsAgentConfig',
    component: () => import('@modules/trading_agents/views/AgentConfigView.vue'),
    meta: { requiresAuth: true, title: '智能体配置' },
  },
  {
    path: '/settings/trading-agents/analysis',
    name: 'TradingAgentsAnalysis',
    component: () => import('@modules/trading_agents/views/AnalysisSettingsView.vue'),
    meta: { requiresAuth: true, title: '分析设置' },
  },
  // TradingAgents 管理员页面
  {
    path: '/admin/system-models',
    name: 'AdminSystemModels',
    component: () => import('@modules/trading_agents/views/admin/SystemModelView.vue'),
    meta: { requiresAuth: true, title: '系统模型管理', adminOnly: true },
  },
  {
    path: '/admin/all-tasks',
    name: 'AdminAllTasks',
    component: () => import('@modules/trading_agents/views/admin/AllTasksView.vue'),
    meta: { requiresAuth: true, title: '所有任务管理', adminOnly: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@core/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

export default moduleRoutes
