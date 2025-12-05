import { createApp } from 'vue'
import { createPinia } from 'pinia'
import NaiveUI from 'naive-ui'
import AppSimple from './AppSimple.vue'

// 创建应用实例
const app = createApp(AppSimple)

// 安装插件
app.use(createPinia())
app.use(NaiveUI)

// 挂载应用
app.mount('#app')