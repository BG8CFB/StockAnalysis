/**
 * 路由配置
 *
 * 企业级最佳实践：
 * 1. 认证检查只基于 isLoggedIn（有无 token），不检查 userInfo
 * 2. userInfo 由 App.vue 启动时后台加载，不作为路由访问条件
 * 3. token 无效时 API 返回 401，HTTP 拦截器清除认证状态
 * 4. 管理员页面：userInfo 未加载时暂时放行，由页面组件内部检查
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
  {
    path: '/',
    component: () => import('@core/layout/MainLayout.vue'),
    children: [
      // 根路径重定向内联为子路由，消除重复的 path: '/'
      { path: '', redirect: '/dashboard' },
      ...protectedRoutes,
    ],
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
// 用于避免重复请求系统状态
let systemStatusPromise: Promise<void> | null = null

// ==================== 路由守卫 ====================

/**
 * 全局前置守卫
 *
 * 设计原则：
 * - 认证只检查 token（isLoggedIn），不检查 userInfo，避免无限重定向循环
 * - 系统状态使用缓存避免重复请求
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
    // 未登录（无 token）→ 跳转登录页
    if (!userStore.isLoggedIn) {
      return {
        name: 'Login',
        query: { redirect: to.fullPath }
      }
    }
    // 已登录（有 token）→ 允许访问
    // userInfo 由 App.vue 启动时加载，不作为路由访问条件
    // 如果 token 无效，API 请求会返回 401，HTTP 拦截器会处理清除和重定向
  }

  // ==================== 3. 管理员权限检查 ====================
  if (adminOnly) {
    // 等待 userInfo 加载完毕再做权限判断，不能直接放行
    if (!userStore.userInfo) {
      try {
        await userStore.fetchUserInfo()
      } catch {
        return { name: 'Login', query: { redirect: to.fullPath } }
      }
    }
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

// 保存取消订阅函数，防止 Vite HMR 时监听器累积
const unsubLogout = eventBus.on(Events.USER_LOGOUT, () => {
  // Token 过期后主动跳转登录页，不依赖用户手动触发导航
  const current = router.currentRoute.value
  const requiresAuth = current.meta?.requiresAuth !== false
  if (requiresAuth) {
    router.push({ name: 'Login', query: { redirect: current.fullPath } })
  }
})

const unsubLogin = eventBus.on(Events.USER_LOGIN, () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.name === 'Login' || currentRoute.name === 'Register') {
    router.push({ name: 'Dashboard' })
  }
})

// Vite HMR 清理，防止热更新时重复注册监听器
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    unsubLogout()
    unsubLogin()
  })
}

export default router
