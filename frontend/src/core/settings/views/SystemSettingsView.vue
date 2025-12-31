<template>
  <div class="system-settings">
    <el-row :gutter="20">
      <!-- 系统状态卡片 -->
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <h2>系统状态</h2>
          </template>
          <el-descriptions
            v-if="systemStatus"
            :column="3"
            border
          >
            <el-descriptions-item label="初始化状态">
              <el-tag :type="systemStatus.initialized ? 'success' : 'danger'">
                {{ systemStatus.initialized ? '已初始化' : '未初始化' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="MongoDB">
              <el-tag :type="systemStatus.mongodb_connected ? 'success' : 'danger'">
                {{ systemStatus.mongodb_connected ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Redis">
              <el-tag :type="systemStatus.redis_connected ? 'success' : 'danger'">
                {{ systemStatus.redis_connected ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="总用户数">
              {{ systemStatus.user_stats?.total || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="活跃用户">
              {{ systemStatus.user_stats?.active || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="待审核">
              <el-tag type="warning">
                {{ systemStatus.user_stats?.pending || 0 }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="已禁用">
              {{ systemStatus.user_stats?.disabled || 0 }}
            </el-descriptions-item>
          </el-descriptions>
          <el-button
            type="primary"
            :icon="Refresh"
            :loading="loading"
            style="margin-top: 16px"
            @click="fetchSystemInfo"
          >
            刷新状态
          </el-button>
        </el-card>
      </el-col>

      <!-- 系统配置卡片（仅超级管理员） -->
      <el-col
        v-if="isSuperAdmin"
        :span="24"
      >
        <el-card
          shadow="never"
          style="margin-top: 20px"
        >
          <template #header>
            <h2>系统配置</h2>
          </template>
          <el-form
            v-if="systemConfig"
            ref="configFormRef"
            :model="configForm"
            label-width="180px"
          >
            <el-form-item label="系统名称">
              <el-input
                v-model="configForm.app_name"
                disabled
              />
            </el-form-item>
            <el-form-item label="系统版本">
              <el-input
                v-model="configForm.app_version"
                disabled
              />
            </el-form-item>
            <el-form-item label="调试模式">
              <el-switch
                v-model="configForm.debug"
                disabled
              />
              <span class="form-tip">只能在服务器配置中修改</span>
            </el-form-item>
            <el-divider />
            <el-form-item label="需要管理员审核">
              <el-switch v-model="configForm.require_approval" />
              <span class="form-tip">新注册用户需要管理员审核后才能激活</span>
            </el-form-item>
            <el-form-item label="开放注册">
              <el-switch v-model="configForm.registration_open" />
              <span class="form-tip">关闭后将禁止新用户注册</span>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="saving"
                @click="handleSaveConfig"
              >
                保存配置
              </el-button>
              <el-button @click="fetchSystemConfig">
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useSettingsStore } from '@core/settings'
import { useUserStore } from '@core/auth/store'
import type { SystemConfig, SystemStatus, SystemInfo } from '@core/settings'

const settingsStore = useSettingsStore()
const userStore = useUserStore()

// 是否为超级管理员
const isSuperAdmin = computed(() => userStore.userInfo?.role === 'SUPER_ADMIN')

// 加载状态
const loading = ref(false)
const saving = ref(false)

// 系统状态
const systemStatus = computed(() => settingsStore.systemStatus)
const systemConfig = computed(() => settingsStore.systemConfig)
const systemInfo = computed(() => settingsStore.systemInfo)

// 配置表单
const configForm = ref<Partial<SystemInfo>>({
  app_name: '',
  app_version: '',
  debug: false,
  require_approval: true,
  registration_open: true,
})

// 获取系统信息
async function fetchSystemInfo() {
  loading.value = true
  try {
    await settingsStore.fetchSystemInfo()
    // 更新表单
    if (systemConfig.value) {
      configForm.value = { ...systemConfig.value }
    }
  } catch (error: any) {
    ElMessage.error('获取系统信息失败')
  } finally {
    loading.value = false
  }
}

// 获取系统配置
async function fetchSystemConfig() {
  loading.value = true
  try {
    await settingsStore.fetchSystemConfig()
    if (systemConfig.value) {
      configForm.value = { ...systemConfig.value }
    }
  } catch (error: any) {
    ElMessage.error('获取系统配置失败')
  } finally {
    loading.value = false
  }
}

// 保存配置
async function handleSaveConfig() {
  saving.value = true
  try {
    await settingsStore.updateConfig({
      require_approval: configForm.value.require_approval ?? true,
      registration_open: configForm.value.registration_open ?? true,
    })
    ElMessage.success('配置已保存')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSystemInfo()
})
</script>

<style scoped>
.system-settings {
  padding: 20px;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
