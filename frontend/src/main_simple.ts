import { createApp } from 'vue'
import { createPinia } from 'pinia'
import NaiveUI from 'naive-ui'

// 简单的主应用组件
const App = {
  template: `
    <div style="padding: 20px; font-family: Arial, sans-serif;">
      <div style="text-align: center; margin-bottom: 40px;">
        <img src="/logo.svg" alt="Logo" style="height: 40px; margin-bottom: 10px;" />
        <h1>TradingAgents-CN</h1>
        <p>模块化单体架构的股票分析智能体系统</p>
      </div>

      <div style="max-width: 1200px; margin: 0 auto;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">

          <!-- 用户管理卡片 -->
          <n-card title="用户管理" style="text-align: left;">
            <template #header-extra>
              <n-tag type="primary" size="small">可用</n-tag>
            </template>
            <p>• 用户注册和登录</p>
            <p>• JWT认证系统</p>
            <p>• 个人资料管理</p>
            <div style="margin-top: 15px;">
              <n-button @click="navigateTo('/login')" type="primary" style="margin-right: 10px;">
                登录
              </n-button>
              <n-button @click="navigateTo('/register')">
                注册
              </n-button>
            </div>
          </n-card>

          <!-- 仪表盘卡片 -->
          <n-card title="仪表盘" style="text-align: left;">
            <template #header-extra>
              <n-tag type="success" size="small">可用</n-tag>
            </template>
            <p>• 系统概览数据</p>
            <p>• 实时市场信息</p>
            <p>• 用户活动统计</p>
            <div style="margin-top: 15px;">
              <n-button @click="navigateTo('/dashboard')" type="info">
                查看仪表盘
              </n-button>
            </div>
          </n-card>

          <!-- API接口卡片 -->
          <n-card title="API接口" style="text-align: left;">
            <template #header-extra>
              <n-tag type="warning" size="small">运行中</n-tag>
            </template>
            <p>• RESTful API</p>
            <p>• 自动文档生成</p>
            <p>• 模块化路由</p>
            <div style="margin-top: 15px;">
              <n-button @click="openDocs" type="default">
                查看API文档
              </n-button>
            </div>
          </n-card>

          <!-- 系统状态卡片 -->
          <n-card title="系统状态" style="text-align: left;">
            <template #header-extra>
              <n-tag type="success" size="small">健康</n-tag>
            </template>
            <p>• 后端服务：运行正常</p>
            <p>• 前端服务：运行正常</p>
            <p>• 数据库：待配置</p>
            <div style="margin-top: 15px;">
              <n-button @click="checkHealth" type="success">
                健康检查
              </n-button>
            </div>
          </n-card>
        </div>

        <!-- 系统特性 -->
        <div style="margin-top: 40px;">
          <h2 style="text-align: center; margin-bottom: 20px;">系统特性</h2>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
            <div style="text-align: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h4 style="color: #666;">🧩 模块化架构</h4>
              <p style="font-size: 14px;">即插即用的模块系统</p>
            </div>
            <div style="text-align: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h4 style="color: #666;">⚡ 事件驱动</h4>
              <p style="font-size: 14px;">模块间解耦通信</p>
            </div>
            <div style="text-align: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h4 style="color: #666;">🔒 安全认证</h4>
              <p style="font-size: 14px;">JWT认证和权限管理</p>
            </div>
            <div style="text-align: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h4 style="color: #666;">📱 响应式设计</h4>
              <p style="font-size: 14px;">现代化用户界面</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  methods: {
    navigateTo(path) {
      window.location.href = path
    },
    openDocs() {
      window.open('http://localhost:8000/docs', '_blank')
    },
    async checkHealth() {
      try {
        const response = await fetch('http://localhost:8000/health')
        const data = await response.json()
        alert(`系统状态：${data.status}\n消息：${data.message}`)
      } catch (error) {
        alert('健康检查失败，请确认后端服务是否运行')
      }
    }
  }
}

// 创建应用实例
const app = createApp(App)

// 安装插件
app.use(createPinia())
app.use(NaiveUI)

// 挂载应用
app.mount('#app')