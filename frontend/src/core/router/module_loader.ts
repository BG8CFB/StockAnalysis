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
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@core/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

export default moduleRoutes
