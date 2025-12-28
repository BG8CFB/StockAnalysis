<script setup lang="ts">
import { ref } from 'vue'
import UserSettingsForm from './UserSettingsView.vue'
import SettingsImportExport from '../components/SettingsImportExport.vue'
import QuotaDisplay from '../components/QuotaDisplay.vue'

const importExportRef = ref<InstanceType<typeof SettingsImportExport>>()
const quotaRef = ref<InstanceType<typeof QuotaDisplay>>()

// 配置导入完成后刷新
const handleImported = () => {
  if (quotaRef.value) {
    quotaRef.value.loadQuota()
  }
}
</script>

<template>
  <div class="settings-view">
    <el-row :gutter="20">
      <el-col :span="16">
        <!-- 用户设置表单 -->
        <UserSettingsForm />

        <!-- 配置导入导出 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>配置管理</span>
            </div>
          </template>

          <div class="config-actions">
            <SettingsImportExport
              ref="importExportRef"
              @imported="handleImported"
            />
          </div>

          <el-alert
            title="配置导入说明"
            type="info"
            :closable="false"
            style="margin-top: 16px"
          >
            <ul>
              <li>导出配置会下载一个JSON文件，包含您的所有个人设置</li>
              <li>导入配置可以从备份文件恢复设置</li>
              <li>合并模式：保留未在文件中指定的设置</li>
              <li>完全覆盖：使用文件中的所有设置替换当前设置</li>
            </ul>
          </el-alert>
        </el-card>
      </el-col>

      <el-col :span="8">
        <!-- 配额信息 -->
        <QuotaDisplay ref="quotaRef" />
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.config-actions {
  display: flex;
  gap: 12px;
}

.config-actions ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.config-actions li {
  margin: 4px 0;
}
</style>
