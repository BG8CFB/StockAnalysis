<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCoreSettings, updateCoreSettings } from '@/core/user/settings-api'
import type { CoreSettings } from '@/core/user/settings-types'

const settings = ref<CoreSettings>({
  theme: 'light',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  watchlist: []
})

const loading = ref(false)

// 加载设置
const loadSettings = async () => {
  loading.value = true
  try {
    const data = await getCoreSettings()
    settings.value = data.core_settings
  } catch (error: any) {
    ElMessage.error(error.message || '加载设置失败')
  } finally {
    loading.value = false
  }
}

// 保存设置
const saveSettings = async () => {
  loading.value = true
  try {
    await updateCoreSettings({
      theme: settings.value.theme,
      language: settings.value.language,
      timezone: settings.value.timezone,
    })
    ElMessage.success('设置保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存设置失败')
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载设置
onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="user-settings-view">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>核心设置</span>
        </div>
      </template>

      <el-form label-width="120px">
        <!-- 主题 -->
        <el-form-item label="主题">
          <el-radio-group v-model="settings.theme">
            <el-radio label="light">浅色</el-radio>
            <el-radio label="dark">深色</el-radio>
            <el-radio label="auto">自动</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 语言 -->
        <el-form-item label="语言">
          <el-select v-model="settings.language">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>

        <!-- 时区 -->
        <el-form-item label="时区">
          <el-select v-model="settings.timezone">
            <el-option label="Asia/Shanghai" value="Asia/Shanghai" />
            <el-option label="America/New_York" value="America/New_York" />
            <el-option label="Europe/London" value="Europe/London" />
          </el-select>
        </el-form-item>

        <!-- 保存按钮 -->
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.user-settings-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
