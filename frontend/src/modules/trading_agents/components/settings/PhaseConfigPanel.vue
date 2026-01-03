<template>
  <div class="phase-config-panel">
    <!-- 阶段标题 -->
    <div class="section-header">
      <h3>{{ phaseTitle }}</h3>
    </div>

    <el-divider />

    <!-- 智能体列表 -->
    <div class="agents-section">
      <div class="section-header">
        <h4>智能体列表 ({{ localConfig.agents.length }})</h4>
        <!-- 只有第一阶段才显示添加按钮 -->
        <el-button
          v-if="phase === 1"
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
              {{ isPhase1 ? '编辑' : '修改提示词' }}
            </el-button>
            <!-- 只有第一阶段才显示删除按钮 -->
            <el-button
              v-if="isPhase1"
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

    <!-- 智能体编辑对话框 -->
    <el-dialog
      v-model="showAgentDialog"
      :title="dialogTitle"
      width="700px"
      @close="handleAgentDialogClose"
    >
      <el-form
        ref="agentFormRef"
        :model="agentForm"
        :rules="agentRules"
        label-width="120px"
      >
        <!-- 第一阶段：允许修改所有字段 -->
        <template v-if="isPhase1">
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
              placeholder="选择 MCP 服务器（未选择时使用所有已启用的服务器）"
              style="width: 100%"
            >
              <el-option
                v-for="server in serverOptions"
                :key="server.name"
                :label="server.name"
                :value="server.name"
              />
            </el-select>
            <span class="form-tip">该智能体可使用的 MCP 服务器。未选择时，可使用所有已启用的 MCP 服务器。</span>
          </el-form-item>

          <el-form-item label="启用状态">
            <el-switch v-model="agentForm.enabled" />
          </el-form-item>
        </template>

        <!-- 第二、三、四阶段：只能修改提示词 -->
        <template v-else>
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            style="margin-bottom: 16px"
          >
            本阶段只能修改智能体的提示词（角色定义），其他字段不可修改。
          </el-alert>

          <el-form-item label="智能体名称">
            <el-input
              v-model="agentForm.name"
              disabled
            />
          </el-form-item>

          <el-form-item label="唯一标识符">
            <el-input
              v-model="agentForm.slug"
              disabled
            />
          </el-form-item>

          <el-form-item
            label="角色定义"
            prop="role_definition"
          >
            <el-input
              v-model="agentForm.role_definition"
              type="textarea"
              :rows="10"
              placeholder="你是一位专业的股票分析师，负责..."
            />
            <span class="form-tip">系统提示词，定义智能体的角色和职责</span>
          </el-form-item>

          <el-form-item label="启用状态">
            <el-switch v-model="agentForm.enabled" />
            <span class="form-tip">可以启用或禁用此智能体</span>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showAgentDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveAgent"
        >
          保存
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

// 是否为第一阶段
const isPhase1 = computed(() => props.phase === 1)

// 阶段标题
const phaseTitle = computed(() => {
  const titles = ['', '分析师团队', '研究辩论', '风险评估', '总结输出']
  return titles[props.phase] || ''
})

// 对话框标题
const dialogTitle = computed(() => {
  if (isPhase1.value) {
    return isEditAgent.value ? '编辑智能体' : '添加智能体'
  } else {
    return '修改提示词'
  }
})

// 本地配置
const localConfig = reactive<Phase1Config | Phase2Config | Phase3Config | Phase4Config>(
  getDefaultConfig()
)

// 监听配置变化（深拷贝确保数据同步）
watch(() => props.config, (newConfig) => {
  if (newConfig) {
    // 使用深拷贝避免引用问题
    localConfig.enabled = newConfig.enabled
    localConfig.max_rounds = newConfig.max_rounds
    // 深拷贝 agents 数组，确保引用变化时能触发更新
    localConfig.agents = newConfig.agents.map(agent => ({ ...agent }))
    // max_concurrency 是第一阶段特有的属性
    if ('max_concurrency' in newConfig) {
      (localConfig as any).max_concurrency = newConfig.max_concurrency
    }
  }
}, { deep: true, immediate: true })

// 默认配置（模型选择已与智能体配置分离）
function getDefaultConfig(): Phase1Config | Phase2Config | Phase3Config | Phase4Config {
  return {
    enabled: true,
    max_rounds: 1,
    agents: [],
  }
}

// 智能体对话框
const showAgentDialog = ref(false)
const isEditAgent = ref(false)
const editingAgentIndex = ref(-1)
const agentFormRef = ref()

const agentForm = reactive<AgentConfig>({
  slug: '',
  name: '',
  role_definition: undefined, // 可选字段，非管理员用户不会获取到此数据
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
  // role_definition 不再是必填字段（管理员界面可能需要，但在前端表单中不强制）
}

// 保存状态
const saving = ref(false)

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
function handleEditAgent(agent: AgentConfig, index: number) {
  isEditAgent.value = true
  editingAgentIndex.value = index  // 保存当前编辑的索引
  // 将 MCPServerConfig 对象转换为字符串列表（兼容后端返回的对象格式）
  const mcpServers = agent.enabled_mcp_servers.map((s: any) =>
    typeof s === 'string' ? s : s.name
  )
  // 清空并重新赋值，确保响应式
  Object.assign(agentForm, {
    slug: '',
    name: '',
    role_definition: undefined,
    when_to_use: '',
    enabled_mcp_servers: [],
    enabled_local_tools: [],
    enabled: true,
  })
  Object.assign(agentForm, {
    ...agent,
    enabled_mcp_servers: mcpServers,
  })
  showAgentDialog.value = true
}

// 删除智能体
function handleDeleteAgent(index: number) {
  localConfig.agents.splice(index, 1)
}

// 保存智能体（直接保存到后端）
async function handleSaveAgent() {
  await agentFormRef.value?.validate()

  saving.value = true
  try {
    if (isPhase1.value) {
      // 第一阶段：保存所有字段
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
        // 使用 splice 替换数组元素，确保 Vue 响应式能够追踪变化
        localConfig.agents.splice(editingAgentIndex.value, 1, agentData)
      } else {
        localConfig.agents.push(agentData)
      }
    } else {
      // 第二、三、四阶段：只保存 role_definition 和 enabled
      if (isEditAgent.value) {
        const existingAgent = localConfig.agents[editingAgentIndex.value]
        // 使用 splice 触发响应式更新
        localConfig.agents.splice(editingAgentIndex.value, 1, {
          ...existingAgent,
          role_definition: agentForm.role_definition,
          enabled: agentForm.enabled
        })
      }
    }

    // 直接保存到后端
    emit('save', { ...localConfig })
    showAgentDialog.value = false
  } finally {
    saving.value = false
  }
}

// 关闭智能体对话框
function handleAgentDialogClose() {
  agentFormRef.value?.resetFields()
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
</style>
