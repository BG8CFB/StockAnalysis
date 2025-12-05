import type { ModuleInfo } from '@/core/router/module_loader'
import DashboardView from './views/DashboardView.vue'

export default {
  name: 'dashboard',
  version: '1.0.0',
  description: '仪表盘模块',
  routes: [
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: DashboardView,
      meta: {
        title: '仪表盘',
        icon: 'DashboardOutlined',
        requiresAuth: true
      }
    }
  ]
} as ModuleInfo