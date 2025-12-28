<template>
  <div class="agent-config">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>智能体配置</h2>
      <div class="header-actions">
        <!-- 管理员显示公共/个人配置切换 -->
        <el-radio-group
          v-if="isAdmin"
          v-model="configMode"
          @change="handleConfigModeChange"
        >
          <el-radio-button value="personal">
            个人配置
          </el-radio-button>
          <el-radio-button value="public">
            公共配置
          </el-radio-button>
        </el-radio-group>

        <!-- 普通用户显示当前配置来源 -->
        <el-tag
          v-else-if="config"
          :type="config.is_public ? 'info' : 'success'"
        >
          {{ config.is_public ? '当前使用公共配置' : '个人配置' }}
        </el-tag>

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
          v-if="configMode === 'public' && isAdmin"
          type="danger"
          :icon="RefreshRight"
          @click="handleRestoreDefault"
        >
          恢复默认配置
        </el-button>
        <el-button
          v-if="configMode === 'personal' || !isAdmin"
          type="warning"
          :icon="RefreshLeft"
          @click="handleReset"
        >
          重置为公共配置
        </el-button>
      </div>
    </div>

    <!-- 公共配置说明 -->
    <el-alert
      v-if="configMode === 'public'"
      title="公共配置"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
    >
      您正在编辑公共配置。修改后，所有未自定义的用户将使用新的公共配置。
    </el-alert>

    <!-- 个人配置说明 -->
    <el-alert
      v-if="configMode === 'personal'"
      title="个人配置"
      type="success"
      :closable="false"
      style="margin-bottom: 16px"
    >
      您正在编辑个人配置。修改后的配置将保存为您的个人配置，不再使用公共配置。
    </el-alert>

    <el-card
      v-loading="configLoading"
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
            :config="currentConfig?.phase1"
            :model-options="[]"
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
            :config="currentConfig?.phase2"
            :model-options="[]"
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
            :config="currentConfig?.phase3"
            :model-options="[]"
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
            :config="currentConfig?.phase4"
            :model-options="[]"
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
import { Download, Upload, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../store'
import { useUserStore } from '@core/auth/store'
import type { UserAgentConfig, UserAgentConfigUpdate } from '../types'
import PhaseConfigPanel from '../components/PhaseConfigPanel.vue'

const store = useTradingAgentsStore()
const userStore = useUserStore()

// 是否为管理员
const isAdmin = computed(() => userStore.isAdmin)

// 调试日志
console.log('[AgentConfigView] isAdmin:', isAdmin.value)
console.log('[AgentConfigView] userInfo:', userStore.userInfo)

// 配置模式：public 或 personal
// 管理员默认显示个人配置，可以切换到公共配置
// 普通用户始终是 personal（个人配置，但可能是公共配置内容）
const configMode = ref<'public' | 'personal'>('personal')

// 当前阶段
const activePhase = ref('phase1')

// 对话框状态
const showImportDialog = ref(false)
const importText = ref('')

// 配置加载状态
const configLoading = computed(() => store.configLoading)

// 用户配置（个人）
const userConfig = computed(() => store.agentConfig)

// 公共配置
const publicConfig = computed(() => store.publicConfig)

// 当前编辑的配置
const currentConfig = computed(() => {
  if (isAdmin.value && configMode.value === 'public') {
    return publicConfig.value
  }
  return userConfig.value
})

// 当前显示的配置（用于标签显示）
const config = computed(() => {
  if (isAdmin.value && configMode.value === 'public') {
    return publicConfig.value
  }
  return userConfig.value
})

// 可用的服务器
const enabledServers = computed(() => store.enabledServers)

// 配置模式切换
async function handleConfigModeChange() {
  if (configMode.value === 'public') {
    await store.fetchPublicConfig()
  } else {
    await store.fetchAgentConfig()
  }
}

// 保存阶段配置
async function handleSavePhase1(data: any) {
  if (isAdmin.value && configMode.value === 'public') {
    await store.updatePublicConfig({ phase1: data })
  } else {
    await store.updateAgentConfig({ phase1: data })
  }
}

async function handleSavePhase2(data: any) {
  if (isAdmin.value && configMode.value === 'public') {
    await store.updatePublicConfig({ phase2: data })
  } else {
    await store.updateAgentConfig({ phase2: data })
  }
}

async function handleSavePhase3(data: any) {
  if (isAdmin.value && configMode.value === 'public') {
    await store.updatePublicConfig({ phase3: data })
  } else {
    await store.updateAgentConfig({ phase3: data })
  }
}

async function handleSavePhase4(data: any) {
  if (isAdmin.value && configMode.value === 'public') {
    await store.updatePublicConfig({ phase4: data })
  } else {
    await store.updateAgentConfig({ phase4: data })
  }
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
      '确定要重置为公共配置吗？当前的个人配置将被删除。',
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

// 恢复默认配置（管理员）
async function handleRestoreDefault() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复默认配置吗？当前公共配置将被YAML模板覆盖。',
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'error',
      }
    )
    await store.restorePublicConfig()
    ElMessage.success('公共配置已恢复为默认值')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('恢复默认配置失败：' + (error.message || error))
    }
  }
}

// 初始化
onMounted(async () => {
  await store.fetchServers()
  if (isAdmin.value) {
    configMode.value = 'personal'
    await store.fetchAgentConfig()
  } else {
    configMode.value = 'personal'
    await store.fetchAgentConfig()
  }
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
  gap: 12px;
  align-items: center;
}
</style>
