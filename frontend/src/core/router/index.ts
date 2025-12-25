/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import moduleRoutes from './module_loader'
import { eventBus, Events } from '@core/events/bus'
import { useUserStore } from '@core/auth/store'
import { systemApi } from '@core/system/api'

// 公开路由（不需要登录）
const PUBLIC_ROUTE_NAMES = ['Login', 'Register', 'Init', 'NotFound']

// 分离路由
const publicRoutes = moduleRoutes.filter(r => r.meta?.requiresAuth === false)
const protectedRoutes = moduleRoutes.filter(r => r.meta?.requiresAuth !== false && r.name !== 'NotFound')
const notFoundRoute = moduleRoutes.find(r => r.name === 'NotFound')

const routes: RouteRecordRaw[] = [
  // 根路径重定向到仪表板（由路由守卫处理登录状态）
  {
    path: '/',
    redirect: '/dashboard',
  },
  // 受保护路由 (使用 MainLayout)
  {
    path: '/',
    component: () => import('@core/layout/MainLayout.vue'),
    children: protectedRoutes,
  },
  // 公开路由 - 直接展开到顶层
  ...publicRoutes,
]

// 404 路由
if (notFoundRoute) {
  routes.push(notFoundRoute)
}

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// ==================== 路由守卫 ====================

/**
 * 检查系统是否已初始化
 */
async function checkSystemInitialized(): Promise<boolean> {
  try {
    const status = await systemApi.getStatus()
    return status.initialized
  } catch (error) {
    console.error('Failed to check system status:', error)
    // API 请求失败时，假设已初始化（避免卡在初始化页面）
    return true
  }
}

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 股票分析平台`
  }

  const userStore = useUserStore()
  const routeName = to.name as string | undefined

  const requiresAuth = to.meta.requiresAuth !== false
  const adminOnly = to.meta.adminOnly === true

  // ==================== 系统初始化检查 ====================
  // 仅对非公开路由进行系统初始化检查
  if (routeName && !PUBLIC_ROUTE_NAMES.includes(routeName)) {
    const isInitialized = await checkSystemInitialized()
    if (!isInitialized) {
      // 系统未初始化，跳转到初始化页面
      if (routeName !== 'Init') {
        next({ name: 'Init' })
        return
      }
    } else if (routeName === 'Init') {
      // 系统已初始化但访问初始化页面，跳转到仪表板
      next({ name: 'Dashboard' })
      return
    }
  }

  // ==================== 认证检查（最佳实践：只检查状态，不调用 API）====================
  // 需要登录但未登录（userStore.userInfo 为 null 表示未登录）
  // 注意：token 验证已在 main.ts 启动时完成，这里只检查状态
  if (requiresAuth && !userStore.userInfo) {
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
    return
  }

  // ==================== 管理员权限检查 ====================
  if (adminOnly) {
    if (!userStore.userInfo) {
      next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
      return
    }

    const role = userStore.userInfo?.role
    const hasAdminPermission = role === 'ADMIN' || role === 'SUPER_ADMIN'
    if (!hasAdminPermission) {
      next({ name: 'Dashboard' })
      return
    }
  }

  // ==================== 已登录用户访问公开页面 ====================
  if (userStore.userInfo && !requiresAuth) {
    // 已登录用户访问登录/注册页，跳转到仪表板
    if (routeName === 'Login' || routeName === 'Register') {
      next({ name: 'Dashboard' })
      return
    }
  }

  // ==================== 通过所有检查 ====================
  next()
})

// ==================== 监听登录/登出事件 ====================

eventBus.on(Events.USER_LOGOUT, () => {
  // 登出后跳转到登录页
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false) {
    // 携带当前路径作为重定向参数，以便登录后返回
    router.push({ 
      name: 'Login',
      query: { redirect: currentRoute.fullPath }
    })
  }
})

eventBus.on(Events.USER_LOGIN, () => {
  // 登录后如果当前在登录/注册页，跳转到仪表板
  const currentRoute = router.currentRoute.value
  if (currentRoute.name === 'Login' || currentRoute.name === 'Register') {
    router.push({ name: 'Dashboard' })
  }
})

export default router
