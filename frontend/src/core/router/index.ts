/**
 * 路由配置
 *
 * 企业级最佳实践：
 * 1. 路由守卫支持 async/await
 * 2. 用户信息按需加载（有 token 时）
 * 3. 使用 Promise 缓存避免重复请求
 * 4. 权限检查在 userInfo 加载完成后进行
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import moduleRoutes from './module_loader'
import { eventBus, Events } from '@core/events/bus'
import { useUserStore } from '@core/auth/store'
import { useSystemStore } from '@core/system/store'

// 分离路由
const publicRoutes = moduleRoutes.filter(r => r.meta?.requiresAuth === false)
const protectedRoutes = moduleRoutes.filter(r => r.meta?.requiresAuth !== false && r.name !== 'NotFound')
const notFoundRoute = moduleRoutes.find(r => r.name === 'NotFound')

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/',
    component: () => import('@core/layout/MainLayout.vue'),
    children: protectedRoutes,
  },
  ...publicRoutes,
]

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

// ==================== 缓存变量 ====================
// 用于避免重复请求
let systemStatusPromise: Promise<void> | null = null
let userInfoPromise: Promise<void> | null = null

// ==================== 路由守卫 ====================

/**
 * 全局前置守卫
 *
 * 设计原则：
 * - 支持异步操作
 * - 使用缓存避免重复请求
 * - 用户信息按需加载
 */
router.beforeEach(async (to) => {
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

  // ==================== 1. 系统初始化检查 ====================
  // 只在首次访问时检查系统状态，使用 Promise 缓存避免重复请求
  if (!systemStore.statusChecked && !systemStatusPromise) {
    systemStatusPromise = systemStore.checkStatus().finally(() => {
      systemStatusPromise = null
    })
  }
  if (systemStatusPromise) {
    await systemStatusPromise
  }

  // 系统未初始化，只允许访问初始化页面
  if (!systemStore.initialized) {
    if (routeName !== 'Init') {
      return { name: 'Init' }
    }
    return
  }

  // 系统已初始化，不允许访问初始化页面
  if (routeName === 'Init') {
    return userStore.isLoggedIn ? { name: 'Dashboard' } : { name: 'Login' }
  }

  // ==================== 2. 认证检查 ====================
  if (requiresAuth) {
    // 未登录 → 跳转登录页
    if (!userStore.isLoggedIn) {
      return {
        name: 'Login',
        query: { redirect: to.fullPath }
      }
    }

    // 已登录但 userInfo 未加载 → 等待加载（使用缓存避免重复请求）
    if (!userStore.userInfo) {
      if (!userInfoPromise) {
        userInfoPromise = userStore.ensureUserInfoLoaded().finally(() => {
          userInfoPromise = null
        })
      }
      try {
        await userInfoPromise
      } catch {
        // 加载失败（token 无效），清除状态并跳转登录页
        return {
          name: 'Login',
          query: { redirect: to.fullPath }
        }
      }
    }
  }

  // ==================== 3. 管理员权限检查 ====================
  if (adminOnly) {
    const role = userStore.userInfo?.role
    const hasAdminPermission = role === 'ADMIN' || role === 'SUPER_ADMIN'

    if (!hasAdminPermission) {
      console.warn(`[Router] Access denied: ${to.path}`)
      return { name: 'Dashboard' }
    }
  }

  // ==================== 4. 已登录用户访问公开页面 ====================
  if (userStore.isLoggedIn && !requiresAuth) {
    if (routeName === 'Login' || routeName === 'Register') {
      return { name: 'Dashboard' }
    }
  }

  // 通过所有检查
})

// ==================== 监听登录/登出事件 ====================

eventBus.on(Events.USER_LOGOUT, () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false) {
    router.push({
      name: 'Login',
      query: { redirect: currentRoute.fullPath }
    })
  }
})

eventBus.on(Events.USER_LOGIN, () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.name === 'Login' || currentRoute.name === 'Register') {
    router.push({ name: 'Dashboard' })
  }
})

export default router
