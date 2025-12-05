<template>
  <div class="app-container">
    <!-- 头部 -->
    <div class="header">
      <img src="/logo.svg" alt="TradingAgents-CN Logo" class="logo"
           @error="handleLogoError" />
      <h1>TradingAgents-CN</h1>
      <p class="subtitle">模块化单体架构的股票分析智能体系统</p>
    </div>

    <!-- 状态卡片 -->
    <div class="status-grid">
      <div class="status-card" :class="{ error: !status.backend }">
        <div class="status-title">后端服务</div>
        <div class="status-value">{{ status.backend ? '运行正常' : '无法连接' }}</div>
      </div>

      <div class="status-card">
        <div class="status-title">前端服务</div>
        <div class="status-value">运行正常</div>
      </div>

      <div class="status-card" :class="{ error: !status.api }">
        <div class="status-title">API接口</div>
        <div class="status-value">{{ status.api ? '运行正常' : '无法连接' }}</div>
      </div>

      <div class="status-card" :class="{ error: !status.docs }">
        <div class="status-title">API文档</div>
        <div class="status-value">{{ status.docs ? '可访问' : '无法访问' }}</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <a href="http://localhost:8000/docs" target="_blank" class="btn">查看API文档</a>
      <a href="http://localhost:8000/api/dashboard/summary" target="_blank" class="btn success">测试API</a>
      <button @click="checkAllStatus" class="btn">重新检查状态</button>
    </div>

    <!-- 系统特性 -->
    <div class="system-info">
      <h3>系统特性</h3>
      <div class="feature-grid">
        <div class="feature-item">
          <span class="feature-icon">🧩</span>
          <div>
            <div class="feature-title">模块化架构</div>
            <div class="feature-desc">即插即用的模块系统</div>
          </div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">⚡</span>
          <div>
            <div class="feature-title">事件驱动</div>
            <div class="feature-desc">模块间解耦通信</div>
          </div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">🔒</span>
          <div>
            <div class="feature-title">安全认证</div>
            <div class="feature-desc">JWT认证和权限管理</div>
          </div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">📱</span>
          <div>
            <div class="feature-title">响应式设计</div>
            <div class="feature-desc">现代化用户界面</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

// 响应式状态
const status = ref({
  backend: false,
  api: false,
  docs: false
})

let checkInterval: NodeJS.Timeout | null = null

// 方法
async function checkBackend(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:8000/health')
    const data = await response.json()
    status.value.backend = true
    return true
  } catch (error) {
    status.value.backend = false
    return false
  }
}

async function checkAPI(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:8000/api/dashboard/summary')
    status.value.api = response.ok
    return response.ok
  } catch (error) {
    status.value.api = false
    return false
  }
}

async function checkDocs(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:8000/docs')
    status.value.docs = response.ok
    return response.ok
  } catch (error) {
    status.value.docs = false
    return false
  }
}

async function checkAllStatus() {
  await Promise.all([
    checkBackend(),
    checkAPI(),
    checkDocs()
  ])
}

function handleLogoError(event: Event) {
  const img = event.target as HTMLImageElement
  // 使用内联SVG作为fallback
  img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjQwIiB2aWV3Qm94PSIwIDAgMTIwIDQwIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxyZWN0IHdpZHRoPSIxMjAiIGhlaWdodD0iNDAiIHJ4PSI4IiBmaWxsPSIjNjY3ZWVhIi8+CiAgPHRleHQgeD0iNjAiIHk9IjI1IiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+VHJhZGluZ0FnZW50czwvdGV4dD4KPC9zdmc+'
}

// 生命周期
onMounted(() => {
  checkAllStatus()
  // 每30秒检查一次状态
  checkInterval = setInterval(checkAllStatus, 30000)
})

onUnmounted(() => {
  if (checkInterval) {
    clearInterval(checkInterval)
  }
})
</script>

<style scoped>
.app-container {
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 40px;
  color: white;
}

.logo {
  width: 120px;
  height: 40px;
  margin-bottom: 20px;
  border-radius: 6px;
}

.header h1 {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.subtitle {
  font-size: 16px;
  opacity: 0.9;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.status-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #28a745;
  transition: transform 0.2s, box-shadow 0.2s;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.status-card.error {
  border-left-color: #dc3545;
}

.status-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
  font-size: 16px;
}

.status-value {
  font-size: 14px;
  color: #666;
}

.actions {
  text-align: center;
  margin: 40px 0;
}

.btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  margin: 0 10px;
  text-decoration: none;
  display: inline-block;
  transition: background-color 0.2s;
}

.btn:hover {
  background: #0056b3;
}

.btn.success {
  background: #28a745;
}

.btn.success:hover {
  background: #1e7e34;
}

.system-info {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 30px;
  margin-top: 40px;
  backdrop-filter: blur(10px);
}

.system-info h3 {
  margin-bottom: 25px;
  color: #333;
  text-align: center;
  font-size: 20px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #007bff;
  transition: transform 0.2s;
}

.feature-item:hover {
  transform: translateX(4px);
}

.feature-icon {
  font-size: 32px;
  margin-right: 16px;
  flex-shrink: 0;
}

.feature-title {
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.feature-desc {
  font-size: 14px;
  color: #666;
}

@media (max-width: 768px) {
  .app-container {
    padding: 15px;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .actions .btn {
    display: block;
    margin: 10px auto;
    width: 200px;
  }
}
</style>