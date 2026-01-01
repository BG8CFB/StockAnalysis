/**
 * 应用入口
 * 最佳实践：应用启动时验证 token，路由守卫只检查状态
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './core/router'
import { useUserStore } from './core/auth/store'
import './assets/styles/main.css'

// 注意：CodeMirror 6 通过 JavaScript 自动注入样式，无需手动导入 CSS

/**
 * 异步启动函数
 * 在应用挂载前尝试验证/刷新 token
 * 这样可以避免在路由守卫中进行 API 调用，防止无限循环
 */
async function startApp() {
  const app = createApp(App)

  // 注册 Pinia（必须先注册才能使用 store）
  const pinia = createPinia()
  app.use(pinia)

  // 注册路由
  app.use(router)

  // 注册 Element Plus（使用中文语言包）
  app.use(ElementPlus, {
    locale: zhCn,
  })

  // 注册 Element Plus 图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  // 尝试自动刷新 token（应用启动时）
  // 如果用户之前登录过，localStorage 中有 refresh_token
  // 成功：用户自动登录，app 直接进入主页面
  // 失败：静默失败，用户保持未登录状态，路由守卫会重定向到登录页
  try {
    const userStore = useUserStore()
    // 只使用静默初始化，避免在启动时显示错误消息
    await userStore.initializeSilent()
  } catch (error: unknown) {
    // Token 无效或已过期，静默失败
    // 用户状态保持未登录，路由守卫会处理重定向
    // 详细日志记录，帮助调试
    if (error instanceof Error) {
      if (error.message === 'Token expired') {
        console.debug('[App] Auto-login failed: Token expired')
      } else if (error.message.includes('Network Error')) {
        console.debug('[App] Auto-login failed: Network error')
      } else {
        console.debug('[App] Auto-login failed:', error.message)
      }
    } else {
      console.debug('[App] Auto-login failed: Unknown error')
    }
  }

  // 挂载应用
  app.mount('#app')
}

// 启动应用
startApp()
