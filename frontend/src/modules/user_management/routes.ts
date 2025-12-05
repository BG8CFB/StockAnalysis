import type { ModuleInfo } from '@/core/router/module_loader'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'

export default {
  name: 'user_management',
  version: '1.0.0',
  description: '用户管理模块',
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: LoginView,
      meta: {
        title: '登录',
        hideInMenu: true,
        requiresAuth: false
      }
    },
    {
      path: '/register',
      name: 'Register',
      component: RegisterView,
      meta: {
        title: '注册',
        hideInMenu: true,
        requiresAuth: false
      }
    }
  ]
} as ModuleInfo