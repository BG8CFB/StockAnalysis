<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportSettings, importSettings } from '@/core/user/settings-api'
import type { SettingsImport } from '@/core/user/settings-types'

const emit = defineEmits(['imported'])

const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importStrategy = ref<'merge' | 'replace'>('merge')
const importing = ref(false)

// 导出配置
const handleExport = async () => {
  try {
    await exportSettings()
    ElMessage.success('配置导出成功')
  } catch (error: any) {
    ElMessage.error(error.message || '配置导出失败')
  }
}

// 显示导入对话框
const showImportDialog = () => {
  importDialogVisible.value = true
  importFile.value = null
  importStrategy.value = 'merge'
}

// 处理文件选择
const handleFileChange = (file: File) => {
  importFile.value = file
  return false // 阻止自动上传
}

// 导入配置
const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的配置文件')
    return
  }

  importing.value = true
  try {
    // 读取文件内容
    const text = await importFile.value.text()
    const data = JSON.parse(text)

    // 调用导入API
    const result = await importSettings({
      ...data,
      merge_strategy: importStrategy.value,
    })

    ElMessage.success('配置导入成功')
    importDialogVisible.value = false
    emit('imported', result.settings)
  } catch (error: any) {
    ElMessage.error(error.message || '配置导入失败')
  } finally {
    importing.value = false
  }
}

// 暴露方法给父组件
defineExpose({
  showImportDialog,
})
</script>

<template>
  <div class="settings-import-export">
    <el-button @click="handleExport">
      导出配置
    </el-button>
    <el-button @click="showImportDialog">
      导入配置
    </el-button>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入配置"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="导入策略">
          <el-radio-group v-model="importStrategy">
            <el-radio label="merge">
              合并（保留未修改的设置）
            </el-radio>
            <el-radio label="replace">
              完全覆盖（替换所有设置）
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="配置文件">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            accept=".json"
          >
            <el-button>选择文件</el-button>
          </el-upload>
          <div
            v-if="importFile"
            class="file-name"
          >
            {{ importFile.name }}
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="importDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="importing"
          @click="handleImport"
        >
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.settings-import-export {
  display: inline-block;
}

.file-name {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
