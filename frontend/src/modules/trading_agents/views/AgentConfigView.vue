<template>
  <div class="agent-config">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>智能体配置</h2>
      <div class="header-actions">
        <el-button
          :icon="Download"
          @click="handleExport"
        >
          导出配置
        </el-button>
        <el-button
          :icon="Upload"
          @click="showImportDialog = true"
        >
          导入配置
        </el-button>
        <el-button
          type="warning"
          :icon="RefreshLeft"
          @click="handleReset"
        >
          重置为默认
        </el-button>
      </div>
    </div>

    <el-card
      v-loading="store.configLoading"
      shadow="never"
    >
      <el-tabs
        v-model="activePhase"
        type="card"
      >
        <!-- 第一阶段：分析师团队 -->
        <el-tab-pane
          label="第一阶段：分析师团队"
          name="phase1"
        >
          <PhaseConfigPanel
            :phase="1"
            :config="config?.phase1"
            :model-options="enabledModels"
            :server-options="enabledServers"
            @save="handleSavePhase1"
          />
        </el-tab-pane>

        <!-- 第二阶段：辩论 -->
        <el-tab-pane
          label="第二阶段：研究辩论"
          name="phase2"
        >
          <PhaseConfigPanel
            :phase="2"
            :config="config?.phase2"
            :model-options="enabledModels"
            :server-options="enabledServers"
            @save="handleSavePhase2"
          />
        </el-tab-pane>

        <!-- 第三阶段：风险评估 -->
        <el-tab-pane
          label="第三阶段：风险评估"
          name="phase3"
        >
          <PhaseConfigPanel
            :phase="3"
            :config="config?.phase3"
            :model-options="enabledModels"
            :server-options="enabledServers"
            @save="handleSavePhase3"
          />
        </el-tab-pane>

        <!-- 第四阶段：总结 -->
        <el-tab-pane
          label="第四阶段：总结输出"
          name="phase4"
        >
          <PhaseConfigPanel
            :phase="4"
            :config="config?.phase4"
            :model-options="enabledModels"
            :server-options="enabledServers"
            @save="handleSavePhase4"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入配置"
      width="600px"
    >
      <el-alert
        title="请粘贴导出的配置 JSON"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        placeholder="{&quot;phase1&quot;: {...}, &quot;phase2&quot;: {...}}"
      />
      <template #footer>
        <el-button @click="showImportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleImport"
        >
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload, RefreshLeft } from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../store'
import type { UserAgentConfig, UserAgentConfigUpdate, AIModelConfig, MCPServerConfig } from '../types'
import PhaseConfigPanel from '../components/PhaseConfigPanel.vue'

const store = useTradingAgentsStore()

// 当前阶段
const activePhase = ref('phase1')

// 对话框状态
const showImportDialog = ref(false)
const importText = ref('')

// 配置
const config = computed(() => store.agentConfig)

// 可用的模型和服务器
const enabledModels = computed(() => store.enabledModels)
const enabledServers = computed(() => store.enabledServers)

// 保存阶段配置
async function handleSavePhase1(data: any) {
  await store.updateAgentConfig({ phase1: data })
}

async function handleSavePhase2(data: any) {
  await store.updateAgentConfig({ phase2: data })
}

async function handleSavePhase3(data: any) {
  await store.updateAgentConfig({ phase3: data })
}

async function handleSavePhase4(data: any) {
  await store.updateAgentConfig({ phase4: data })
}

// 导出配置
async function handleExport() {
  try {
    const configData = await store.exportAgentConfig()
    const json = JSON.stringify(configData, null, 2)
    navigator.clipboard.writeText(json)
    ElMessage.success('配置已复制到剪贴板')
  } catch (error) {
    ElMessage.error('导出配置失败')
  }
}

// 导入配置
async function handleImport() {
  try {
    const configData = JSON.parse(importText.value)
    await store.importAgentConfig(configData)
    showImportDialog.value = false
    importText.value = ''
  } catch (error) {
    ElMessage.error('导入配置失败，请检查 JSON 格式')
  }
}

// 重置配置
async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '确定要重置为默认配置吗？当前配置将被覆盖。',
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await store.resetAgentConfig()
  } catch {
    // 用户取消
  }
}

// 初始化
onMounted(async () => {
  await store.fetchAgentConfig()
  await store.fetchModels()
  await store.fetchServers()
})
</script>

<style scoped>
.agent-config {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}
</style>
