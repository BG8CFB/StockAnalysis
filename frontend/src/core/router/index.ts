/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import moduleRoutes from './module_loader'
import { eventBus, Events } from '@core/events/bus'
import { useUserStore } from '@core/auth/store'
import { useSystemStore } from '@core/system/store'

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

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 股票分析平台`
  }

  const userStore = useUserStore()
  const systemStore = useSystemStore()
  const routeName = to.name as string | undefined

  const requiresAuth = to.meta.requiresAuth !== false
  const adminOnly = to.meta.adminOnly === true

  // ==================== 系统初始化检查 ====================
  // 优化：只在未检查过时调用 API，避免每次路由跳转都请求后端
  if (!systemStore.statusChecked) {
    await systemStore.checkStatus()
  }

  if (!systemStore.initialized) {
    // 系统未初始化，只允许访问初始化页面
    if (routeName !== 'Init') {
      next({ name: 'Init' })
      return
    }
  } else {
    // 系统已初始化，不允许访问初始化页面
    if (routeName === 'Init') {
      // 如果已登录，跳转到仪表板；否则跳转到登录页
      if (userStore.userInfo) {
        next({ name: 'Dashboard' })
      } else {
        next({ name: 'Login' })
      }
      return
    }
  }

  // ==================== 认证检查（最佳实践：只检查状态，不调用 API）====================
  // 登录状态判断：isLoggedIn 计算属性已包含 token 检查
  // 注意：token 验证已在 main.ts 启动时完成，这里只检查状态
  const isLoggedIn = userStore.isLoggedIn

  if (requiresAuth && !isLoggedIn) {
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
    return
  }

  // ==================== 等待用户信息加载（修复第一次点击跳转问题）====================
  // 如果已登录但用户信息还未加载完成（第一次刷新页面时），等待加载完成
  // 这确保了后续依赖 userInfo 的判断能正确执行
  if (isLoggedIn && !userStore.userInfo) {
    console.log('[Router] User is logged in but userInfo not loaded, waiting...')
    try {
      // 使用 ensureUserInfoLoaded 确保 userInfo 加载完成
      await userStore.ensureUserInfoLoaded()
      console.log('[Router] userInfo loaded successfully', { 
        role: userStore.userInfo?.role 
      })
    } catch (error) {
      // 加载失败，token 可能已过期，清除状态并跳转到登录页
      console.error('[Router] Failed to load user info:', error)
      next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }

  // ==================== 管理员权限检查 ====================
  if (adminOnly) {
    // 检查登录状态
    if (!isLoggedIn) {
      console.log('[Router] Admin route but not logged in, redirecting to Login')
      next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
      return
    }

    // 检查管理员权限
    // 注意：ensureUserInfoLoaded 已确保 userInfo 已加载，可以安全访问
    const role = userStore.userInfo?.role
    const hasAdminPermission = role === 'ADMIN' || role === 'SUPER_ADMIN'
    
    console.log('[Router] Admin permission check', {
      path: to.path,
      role,
      hasAdminPermission
    })
    
    if (!hasAdminPermission) {
      // 非管理员访问管理员专属路由时，记录并跳转到 Dashboard
      console.warn(`[Router] Non-admin user attempted to access admin route: ${to.path}`)
      next({ name: 'Dashboard' })
      return
    }
  }

  // ==================== 已登录用户访问公开页面 ====================
  if (isLoggedIn && !requiresAuth) {
    // 已登录用户访问登录/注册页，跳转到仪表板
    if (routeName === 'Login' || routeName === 'Register') {
      next({ name: 'Dashboard' })
      return
    }
  }

  // ==================== 通过所有检查 ====================
  // 特殊处理：如果访问 /settings（没有子路径），重定向到第一个设置页面
  // 这是因为我们移除了 /settings 的静态重定向路由，避免与菜单导航冲突
  if (to.path === '/settings') {
    // 根据用户权限重定向到合适的设置页面
    const role = userStore.userInfo?.role
    const hasAdminPermission = role === 'ADMIN' || role === 'SUPER_ADMIN'
    if (hasAdminPermission) {
      next('/settings/system')
    } else {
      next('/settings/mcp-servers')
    }
    return
  }

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
