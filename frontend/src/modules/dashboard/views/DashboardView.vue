<template>
  <div class="dashboard-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <h2>欢迎使用股票分析平台</h2>
          <p>这是一个模块化的股票数据分析系统</p>
        </el-card>
      </el-col>
    </el-row>

    <el-row
      :gutter="20"
      style="margin-top: 20px"
    >
      <el-col
        :xs="24"
        :sm="12"
        :md="6"
      >
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon
              class="stat-icon"
              color="#409eff"
            >
              <TrendCharts />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">
                --
              </div>
              <div class="stat-label">
                关注股票
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :md="6"
      >
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon
              class="stat-icon"
              color="#67c23a"
            >
              <DataLine />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">
                --
              </div>
              <div class="stat-label">
                AI 分析次数
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :md="6"
      >
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon
              class="stat-icon"
              color="#e6a23c"
            >
              <Warning />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">
                --
              </div>
              <div class="stat-label">
                预警消息
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :md="6"
      >
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon
              class="stat-icon"
              color="#909399"
            >
              <User />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">
                {{ userStore.email }}
              </div>
              <div class="stat-label">
                当前用户
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row
      :gutter="20"
      style="margin-top: 20px"
    >
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快捷入口</span>
            </div>
          </template>
          <div class="quick-links">
            <el-button disabled>
              市场中心
            </el-button>
            <el-button disabled>
              AI 分析
            </el-button>
            <el-button disabled>
              智能选股
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { TrendCharts, DataLine, Warning, User } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'

const userStore = useUserStore()

onMounted(async () => {
  // 获取用户配置
  await userStore.fetchPreferences()
})
</script>

<style scoped>
.dashboard-view {
  padding: 20px;
}

.welcome-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.welcome-card h2 {
  margin: 0 0 8px;
  font-size: 24px;
}

.welcome-card p {
  margin: 0;
  opacity: 0.9;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  font-size: 40px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-links {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
