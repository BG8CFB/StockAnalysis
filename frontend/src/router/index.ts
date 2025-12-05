import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/modules/user_management/store'
import { moduleLoader } from '@/core/router/module_loader'
import MainLayout from '@/core/layout/MainLayout.vue'

// 定义路由
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/modules/user_management/views/LoginView.vue'),
    meta: {
      title: '登录',
      hideInMenu: true,
      requiresAuth: false
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/modules/user_management/views/RegisterView.vue'),
    meta: {
      title: '注册',
      hideInMenu: true,
      requiresAuth: false
    }
  },
  {
    path: '/',
    component: MainLayout,
    meta: {
      requiresAuth: true
    },
    children: [
      // 动态模块路由将在这里添加
      {
        path: '',
        redirect: '/dashboard'
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/core/views/NotFoundView.vue'),
    meta: {
      title: '页面未找到',
      hideInMenu: true
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 动态添加模块路由
function addModuleRoutes() {
  const moduleRoutes = moduleLoader.getRoutes()

  // 找到主布局路由的children
  const mainRoute = router.options.routes.find(route => route.path === '/' && route.component === MainLayout)

  if (mainRoute && mainRoute.children) {
    // 添加模块路由到主布局的children中
    mainRoute.children.push(...moduleRoutes)

    // 重新添加路由以更新配置
    router.addRoute(mainRoute)
  }
}

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 设置页面标题
  document.title = to.meta?.title
    ? `${to.meta.title} - ${import.meta.env.VITE_APP_TITLE || 'TradingAgents-CN'}`
    : import.meta.env.VITE_APP_TITLE || 'TradingAgents-CN'

  // 检查是否需要认证
  if (to.meta?.requiresAuth !== false) {
    // 检查用户是否已登录
    if (!userStore.isAuthenticated) {
      // 尝试从localStorage恢复用户状态
      const token = localStorage.getItem('token')
      if (token) {
        try {
          await userStore.checkAuth()
        } catch (error) {
          // Token无效，清除并重定向到登录页
          userStore.logout()
          return next('/login')
        }
      } else {
        // 未登录，重定向到登录页
        return next('/login')
      }
    }
  }

  // 如果已登录且访问登录/注册页面，重定向到仪表盘
  if (userStore.isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    return next('/dashboard')
  }

  next()
})

router.afterEach((to, from) => {
  // 可以在这里添加页面分析或其他后处理逻辑
})

// 初始化模块路由
addModuleRoutes()

export default router