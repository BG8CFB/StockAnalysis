import { createApp } from 'vue'
import { createPinia } from 'pinia'
import NaiveUI from 'naive-ui'
import router from './router'
import App from './App.vue'

// 导入全局样式
import './assets/styles/main.css'

// 创建应用实例
const app = createApp(App)

// 安装Pinia
app.use(createPinia())

// 安装Naive UI
app.use(NaiveUI)

// 安装路由
app.use(router)

// 挂载应用
app.mount('#app')