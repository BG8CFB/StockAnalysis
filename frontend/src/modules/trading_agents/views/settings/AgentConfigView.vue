<template>
  <div class="agent-config">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-icon">
          <el-icon :size="24">
            <Setting />
          </el-icon>
        </div>
        <div class="header-info">
          <h2>智能体配置</h2>
          <p class="description">自定义各阶段智能体的行为与参数</p>
        </div>
      </div>

      <div class="header-actions">
        <!-- 配置模式提示 -->
        <div
          v-if="config"
          class="config-mode-indicator"
          :class="{ 'is-public': configMode === 'public' }"
        >
          <el-icon>
            <Lock v-if="configMode === 'public' || config.is_public" />
            <User v-else />
          </el-icon>
          <span>{{ configMode === 'public' ? '公共配置模式' : '个人配置模式' }}</span>
        </div>

        <el-divider direction="vertical" />

        <!-- 管理员显示公共/个人配置切换 -->
        <el-switch
          v-if="isAdmin"
          v-model="isPublicMode"
          active-text="公共"
          inactive-text="个人"
          @change="handleConfigModeChange"
        />

        <el-divider direction="vertical" />

        <!-- 操作按钮组 -->
        <el-button-group>
          <el-tooltip content="导出配置" placement="bottom">
            <el-button
              :icon="Download"
              @click="handleExport"
            />
          </el-tooltip>
          <el-tooltip content="导入配置" placement="bottom">
            <el-button
              :icon="Upload"
              @click="showImportDialog = true"
            />
          </el-tooltip>
          <el-tooltip
            :content="configMode === 'public' ? '恢复默认配置' : '重置为公共配置'"
            placement="bottom"
          >
            <el-button
              :icon="RefreshLeft"
              @click="configMode === 'public' ? handleRestoreDefault() : handleReset()"
            />
          </el-tooltip>
        </el-button-group>
      </div>
    </div>

    <!-- 主内容区：左右分栏布局 -->
    <div
      v-loading="configLoading"
      class="main-content"
    >
      <!-- 左侧：阶段选择列表 -->
      <div class="phase-sidebar">
        <div class="sidebar-title">
          <el-icon><Menu /></el-icon>
          <span>分析阶段</span>
        </div>
        <div class="phase-list">
          <div
            v-for="(phase, index) in phases"
            :key="phase.key"
            class="phase-list-item"
            :class="{ 'is-active': activePhase === phase.key }"
            @click="activePhase = phase.key"
          >
            <div class="phase-number">{{ index + 1 }}</div>
            <div class="phase-item-content">
              <div class="phase-item-title">{{ phase.title }}</div>
              <div class="phase-item-desc">{{ phase.shortDesc }}</div>
            </div>
            <div class="phase-item-count">
              <el-tag
                size="small"
                :type="getPhaseAgentCount(phase.key) > 0 ? 'success' : 'info'"
                effect="plain"
              >
                {{ getPhaseAgentCount(phase.key) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：当前阶段配置 -->
      <div class="phase-content">
        <div class="phase-content-header">
          <div class="phase-header-info">
            <div class="phase-icon-large" :class="`phase-icon-${activePhase.slice(-1)}`">
              <el-icon :size="28">
                <component :is="getCurrentPhaseIcon()" />
              </el-icon>
            </div>
            <div>
              <h3>{{ getCurrentPhaseTitle() }}</h3>
              <p>{{ getCurrentPhaseDesc() }}</p>
            </div>
          </div>
        </div>

        <div class="phase-content-body">
          <PhaseConfigPanel
            :phase="getPhaseNumber()"
            :config="getCurrentPhaseConfig()"
            :model-options="[]"
            :server-options="enabledServers"
            @save="handleSave"
          />
        </div>
      </div>
    </div>

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
import {
  Download,
  Upload,
  RefreshLeft,
  RefreshRight,
  Setting,
  User,
  Lock,
  Menu,
  InfoFilled,
  CircleCheckFilled,
  DataAnalysis,
  ChatDotRound,
  Odometer,
  Document,
} from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../../store'
import { useUserStore } from '@core/auth/store'
import type { UserAgentConfig, UserAgentConfigUpdate } from '../../types'
import PhaseConfigPanel from '../../components/settings/PhaseConfigPanel.vue'

const store = useTradingAgentsStore()
const userStore = useUserStore()

// 阶段配置数据
const phases = [
  {
    key: 'phase1',
    title: '第一阶段：信息收集',
    shortDesc: '技术、基本面、情绪、新闻分析',
    fullDesc: '技术分析、基本面分析、情绪分析、新闻分析',
    icon: DataAnalysis,
  },
  {
    key: 'phase2',
    title: '第二阶段：多空博弈',
    shortDesc: '看涨/看跌辩论、投资决策',
    fullDesc: '看涨研究员、看跌研究员辩论，投资组合经理决策',
    icon: ChatDotRound,
  },
  {
    key: 'phase3',
    title: '第三阶段：风险评估',
    shortDesc: '策略风格辩论、风险管理',
    fullDesc: '激进派、中性派、保守派辩论与风险管理主席评估',
    icon: Odometer,
  },
  {
    key: 'phase4',
    title: '第四阶段：总结报告',
    shortDesc: '综合分析、最终建议',
    fullDesc: '综合所有分析结果，生成最终投资建议报告',
    icon: Document,
  },
]

// 是否为管理员
const isAdmin = computed(() => userStore.isAdmin)

// 配置模式：public 或 personal
const configMode = ref<'public' | 'personal'>('personal')

// 是否为公共模式（用于 Switch 绑定）
const isPublicMode = computed({
  get: () => configMode.value === 'public',
  set: (value) => {
    configMode.value = value ? 'public' : 'personal'
  },
})

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

// 获取当前阶段配置
function getCurrentPhaseConfig() {
  const phaseKey = activePhase.value as 'phase1' | 'phase2' | 'phase3' | 'phase4'
  return currentConfig.value?.[phaseKey] || null
}

// 获取当前阶段编号
function getPhaseNumber() {
  const map = { phase1: 1, phase2: 2, phase3: 3, phase4: 4 }
  return map[activePhase.value as keyof typeof map] || 1
}

// 获取当前阶段图标
function getCurrentPhaseIcon() {
  return phases.find(p => p.key === activePhase.value)?.icon || DataAnalysis
}

// 获取当前阶段标题
function getCurrentPhaseTitle() {
  return phases.find(p => p.key === activePhase.value)?.title || ''
}

// 获取当前阶段描述
function getCurrentPhaseDesc() {
  return phases.find(p => p.key === activePhase.value)?.fullDesc || ''
}

// 获取阶段智能体数量
function getPhaseAgentCount(phaseKey: string) {
  const phase = currentConfig.value?.[phaseKey as keyof typeof currentConfig.value]
  return phase?.agents?.filter(a => a.enabled).length || 0
}

// 配置模式切换
async function handleConfigModeChange() {
  if (configMode.value === 'public') {
    await store.fetchPublicConfig()
  } else {
    await store.fetchAgentConfig()
  }
}

// 保存阶段配置
async function handleSave(data: any) {
  const phaseKey = activePhase.value
  if (isAdmin.value && configMode.value === 'public') {
    await store.updatePublicConfig({ [phaseKey]: data })
    await store.fetchPublicConfig()
  } else {
    await store.updateAgentConfig({ [phaseKey]: data })
    await store.fetchAgentConfig()
  }
}

// 导出配置
async function handleExport() {
  try {
    const configData = await store.exportAgentConfig()
    const json = JSON.stringify(configData, null, 2)
    navigator.clipboard.writeText(json)
    ElMessage.success('配置已复制到剪贴板')
  } catch {
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
  } catch {
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
      '确定要恢复默认配置吗？当前公共配置将被 YAML 模板覆盖。',
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
/* ==================== 页面容器 ==================== */
.agent-config {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ==================== 页面头部 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff 0%, #5dadff 100%);
  color: #fff;
}

.header-info h2 {
  margin: 0 0 4px 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.description {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.config-mode-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  color: #409eff;
  font-size: 13px;
  font-weight: 500;
}

.config-mode-indicator.is-public {
  background: #f4f4f5;
  border-color: #d3d4d6;
  color: #606266;
}

/* ==================== 主内容区（左右分栏） ==================== */
.main-content {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
}

/* ==================== 左侧：阶段选择列表 ==================== */
.phase-sidebar {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  overflow: hidden;
  position: sticky;
  top: 20px;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  background: #fafbfc;
}

.phase-list {
  display: flex;
  flex-direction: column;
}

.phase-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid #f5f7fa;
}

.phase-list-item:last-child {
  border-bottom: none;
}

.phase-list-item:hover {
  background: #f5f7fa;
}

.phase-list-item.is-active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
  padding-left: 17px;
}

.phase-number {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #e4e7ed;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  transition: all 0.2s;
}

.phase-list-item.is-active .phase-number {
  background: #409eff;
  color: #fff;
}

.phase-item-content {
  flex: 1;
  min-width: 0;
}

.phase-item-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.phase-item-desc {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.phase-item-count {
  flex-shrink: 0;
}

/* ==================== 右侧：阶段配置内容 ==================== */
.phase-content {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  overflow: hidden;
}

.phase-content-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e4e7ed;
  background: linear-gradient(to bottom, #fafbfc, #fff);
}

.phase-header-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.phase-icon-large {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.phase-icon-large.phase-icon-1 {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.phase-icon-large.phase-icon-2 {
  background: linear-gradient(135deg, #e6a23c 0%, #f0c78a 100%);
}

.phase-icon-large.phase-icon-3 {
  background: linear-gradient(135deg, #f56c6c 0%, #f89898 100%);
}

.phase-icon-large.phase-icon-4 {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.phase-header-info h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.phase-header-info p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.phase-content-body {
  padding: 0;
  background: #fafbfc;
  min-height: 400px;
}

/* ==================== 响应式 ==================== */
@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .phase-sidebar {
    position: static;
  }

  .phase-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .phase-list-item {
    border-bottom: none;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
  }
}

@media (max-width: 768px) {
  .agent-config {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .phase-list {
    grid-template-columns: 1fr;
  }

  .phase-icon-large {
    width: 48px;
    height: 48px;
  }

  .phase-icon-large :deep(.el-icon) {
    font-size: 24px;
  }

  .phase-header-info h3 {
    font-size: 16px;
  }

  .phase-header-info p {
    font-size: 13px;
  }
}
</style>
