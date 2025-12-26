<template>
  <div class="phase-config-panel">
    <!-- 阶段开关 -->
    <div class="section-header">
      <h3>{{ phaseTitle }}</h3>
      <div class="header-controls">
        <el-switch
          v-model="localConfig.enabled"
          active-text="启用"
          @change="handleEnabledChange"
        />
      </div>
    </div>

    <el-divider />

    <template v-if="localConfig.enabled">
      <!-- 基础配置 -->
      <el-form
        :model="localConfig"
        label-width="140px"
      >
        <el-form-item label="使用模型">
          <el-select
            v-model="localConfig.model_id"
            placeholder="选择 AI 模型"
          >
            <el-option
              v-for="model in modelOptions"
              :key="model.id"
              :label="`${model.name} (${model.provider})`"
              :value="model.model_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="phase === 1"
          label="最大并发数"
        >
          <el-input-number
            v-model="localConfig.max_concurrency"
            :min="1"
            :max="10"
          />
          <span class="form-tip">智能体最大并行执行数量</span>
        </el-form-item>

        <el-form-item
          v-if="phase >= 2"
          label="最大轮次"
        >
          <el-input-number
            v-model="localConfig.max_rounds"
            :min="0"
            :max="10"
          />
          <span class="form-tip">
            <template v-if="phase === 2">辩论/讨论轮次</template>
            <template v-else-if="phase === 3">风险评估轮次</template>
            <template v-else>总结轮次</template>
          </span>
        </el-form-item>
      </el-form>

      <!-- 智能体列表 -->
      <div class="agents-section">
        <div class="section-header">
          <h4>智能体列表 ({{ localConfig.agents.length }})</h4>
          <el-button
            type="primary"
            size="small"
            :icon="Plus"
            @click="handleAddAgent"
          >
            添加智能体
          </el-button>
        </div>

        <el-table
          :data="localConfig.agents"
          stripe
          size="small"
        >
          <el-table-column
            prop="name"
            label="名称"
            width="180"
          />
          <el-table-column
            prop="slug"
            label="标识符"
            width="150"
          />
          <el-table-column
            prop="enabled"
            label="启用"
            width="80"
          >
            <template #default="{ row }">
              <el-switch
                v-model="row.enabled"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="200"
          >
            <template #default="{ row, $index }">
              <el-button
                link
                type="primary"
                size="small"
                @click="handleEditAgent(row)"
              >
                编辑
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="handleDeleteAgent($index)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 保存按钮 -->
      <div class="action-bar">
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          保存配置
        </el-button>
      </div>
    </template>

    <el-empty
      v-else
      description="该阶段已禁用"
    />

    <!-- 智能体编辑对话框 -->
    <el-dialog
      v-model="showAgentDialog"
      :title="isEditAgent ? '编辑智能体' : '添加智能体'"
      width="700px"
      @close="handleAgentDialogClose"
    >
      <el-form
        ref="agentFormRef"
        :model="agentForm"
        :rules="agentRules"
        label-width="120px"
      >
        <el-form-item
          label="智能体名称"
          prop="name"
        >
          <el-input
            v-model="agentForm.name"
            placeholder="例如: 技术分析师"
          />
        </el-form-item>

        <el-form-item
          label="唯一标识符"
          prop="slug"
        >
          <el-input
            v-model="agentForm.slug"
            placeholder="例如: technical_analyst"
            :disabled="isEditAgent"
          />
          <span class="form-tip">只能包含字母、数字和下划线</span>
        </el-form-item>

        <el-form-item
          label="角色定义"
          prop="role_definition"
        >
          <el-input
            v-model="agentForm.role_definition"
            type="textarea"
            :rows="6"
            placeholder="你是一位专业的股票分析师，负责..."
          />
          <span class="form-tip">系统提示词，定义智能体的角色和职责</span>
        </el-form-item>

        <el-form-item label="使用场景">
          <el-input
            v-model="agentForm.when_to_use"
            type="textarea"
            :rows="2"
            placeholder="用于分析股票的技术指标..."
          />
        </el-form-item>

        <el-form-item label="启用的 MCP 服务器">
          <el-select
            v-model="agentForm.enabled_mcp_servers"
            multiple
            placeholder="选择 MCP 服务器"
          >
            <el-option
              v-for="server in serverOptions"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            />
          </el-select>
          <span class="form-tip">该智能体可使用的 MCP 服务器</span>
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="agentForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAgentDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSaveAgent"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { AgentConfig, Phase1Config, Phase2Config, Phase3Config, Phase4Config, AIModelConfig, MCPServerConfig } from '../types'

interface Props {
  phase: number
  config?: Phase1Config | Phase2Config | Phase3Config | Phase4Config | null
  modelOptions: AIModelConfig[]
  serverOptions: MCPServerConfig[]
}

interface Emits {
  (e: 'save', data: Phase1Config | Phase2Config | Phase3Config | Phase4Config): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 阶段标题
const phaseTitle = computed(() => {
  const titles = ['', '分析师团队', '研究辩论', '风险评估', '总结输出']
  return titles[props.phase] || ''
})

// 本地配置
const localConfig = reactive<Phase1Config | Phase2Config | Phase3Config | Phase4Config>(
  props.config || getDefaultConfig()
)

// 监听配置变化
watch(() => props.config, (newConfig) => {
  if (newConfig) {
    Object.assign(localConfig, newConfig)
  }
}, { deep: true })

// 默认配置
function getDefaultConfig(): Phase1Config | Phase2Config | Phase3Config | Phase4Config {
  const base = {
    enabled: false,
    model_id: '',
    max_rounds: 1,
    agents: [],
  }

  if (props.phase === 1) {
    return { ...base, max_concurrency: 3 }
  }

  return base
}

// 智能体对话框
const showAgentDialog = ref(false)
const isEditAgent = ref(false)
const editingAgentIndex = ref(-1)
const agentFormRef = ref()

const agentForm = reactive<AgentConfig>({
  slug: '',
  name: '',
  role_definition: '',
  when_to_use: '',
  enabled_mcp_servers: [],
  enabled_local_tools: [],
  enabled: true,
})

const agentRules = {
  name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入唯一标识符', trigger: 'blur' },
    { pattern: /^[a-z0-9_]+$/, message: '只能包含小写字母、数字和下划线', trigger: 'blur' },
  ],
  role_definition: [{ required: true, message: '请输入角色定义', trigger: 'blur' }],
}

// 保存状态
const saving = ref(false)

// 启用变更
function handleEnabledChange() {
  if (!localConfig.enabled) {
    // 禁用时清空智能体列表
    localConfig.agents = []
  }
}

// 添加智能体
function handleAddAgent() {
  isEditAgent.value = false
  Object.assign(agentForm, {
    slug: '',
    name: '',
    role_definition: '',
    when_to_use: '',
    enabled_mcp_servers: [],
    enabled_local_tools: [],
    enabled: true,
  })
  showAgentDialog.value = true
}

// 编辑智能体
function handleEditAgent(agent: AgentConfig) {
  isEditAgent.value = true
  Object.assign(agentForm, agent)
  showAgentDialog.value = true
}

// 删除智能体
function handleDeleteAgent(index: number) {
  localConfig.agents.splice(index, 1)
}

// 保存智能体
async function handleSaveAgent() {
  await agentFormRef.value?.validate()

  const agentData: AgentConfig = {
    slug: agentForm.slug,
    name: agentForm.name,
    role_definition: agentForm.role_definition,
    when_to_use: agentForm.when_to_use,
    enabled_mcp_servers: [...agentForm.enabled_mcp_servers],
    enabled_local_tools: [],
    enabled: agentForm.enabled,
  }

  if (isEditAgent.value) {
    localConfig.agents[editingAgentIndex.value] = agentData
  } else {
    localConfig.agents.push(agentData)
  }

  showAgentDialog.value = false
}

// 关闭智能体对话框
function handleAgentDialogClose() {
  agentFormRef.value?.resetFields()
}

// 保存配置
async function handleSave() {
  if (!localConfig.model_id) {
    ElMessage.warning('请选择使用模型')
    return
  }

  if (localConfig.agents.length === 0) {
    ElMessage.warning('请至少添加一个智能体')
    return
  }

  saving.value = true
  try {
    emit('save', { ...localConfig })
    ElMessage.success('配置已保存')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.phase-config-panel {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.section-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.agents-section {
  margin-top: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.action-bar {
  margin-top: 24px;
  text-align: right;
}
</style>
