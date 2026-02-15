/**
 * 应用入口
 *
 * 企业级最佳实践：
 * 1. main.ts 只负责插件注册和应用挂载
 * 2. 用户信息在应用启动时自动加载（App.vue onMounted）
 * 3. 路由守卫只做同步权限检查，无异步操作
 * 4. 登录成功后立即加载用户信息
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './core/router'
import './assets/styles/main.css'

async function startApp() {
  const app = createApp(App)

  // 注册 Pinia
  const pinia = createPinia()
  app.use(pinia)

  // 注册路由
  app.use(router)

  // 注册 Element Plus（中文）
  app.use(ElementPlus, { locale: zhCn })

  // 注册图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  // 挂载应用
  // 注意：不在这里预加载用户信息
  // - 用户可能未登录
  // - 用户信息在路由守卫中按需加载
  // - 登录成功后会立即加载用户信息
  app.mount('#app')
}

startApp().catch((error) => {
  console.error('[App] Failed to start:', error)
  const el = document.getElementById('app')
  if (el) {
    el.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;">
        <h2 style="color:#f56c6c;">应用启动失败</h2>
        <p style="color:#909399;">请刷新页面重试</p>
      </div>
    `
  }
})
