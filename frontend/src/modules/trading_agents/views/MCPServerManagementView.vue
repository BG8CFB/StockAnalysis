<template>
  <div class="mcp-server-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>MCP 服务器管理</h2>
      <el-button
        type="primary"
        :icon="Plus"
        @click="showCreateDialog = true"
      >
        添加服务器
      </el-button>
    </div>

    <!-- 服务器列表 -->
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 我的服务器 -->
        <el-tab-pane
          label="我的服务器"
          name="user"
        >
          <el-table
            v-loading="store.serversLoading"
            :data="store.userServers"
            stripe
          >
            <el-table-column
              prop="name"
              label="名称"
              width="180"
            />
            <el-table-column
              prop="transport"
              label="传输模式"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getTransportTagType(row.transport)"
                  size="small"
                >
                  {{ row.transport.toUpperCase() }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="url"
              label="地址/命令"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                {{ row.transport === 'stdio' ? row.command : row.url }}
              </template>
            </el-table-column>
            <el-table-column
              prop="status"
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getStatusTagType(row.status)"
                  size="small"
                >
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="enabled"
              label="启用"
              width="80"
            >
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  @change="handleToggleEnabled(row)"
                />
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="220"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Tools"
                  @click="handleViewTools(row)"
                >
                  工具
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Edit"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 系统服务器 -->
        <el-tab-pane
          label="系统服务器"
          name="system"
        >
          <el-table
            v-loading="store.serversLoading"
            :data="store.systemServers"
            stripe
          >
            <el-table-column
              prop="name"
              label="名称"
              width="180"
            />
            <el-table-column
              prop="transport"
              label="传输模式"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ row.transport.toUpperCase() }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="url"
              label="地址/命令"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                {{ row.transport === 'stdio' ? row.command : row.url }}
              </template>
            </el-table-column>
            <el-table-column
              prop="status"
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getStatusTagType(row.status)"
                  size="small"
                >
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="150"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Tools"
                  @click="handleViewTools(row)"
                >
                  工具
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEdit ? '编辑服务器' : '添加服务器'"
      width="700px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item
          label="服务器名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="请输入服务器名称"
          />
        </el-form-item>

        <el-form-item
          label="传输模式"
          prop="transport"
        >
          <el-radio-group
            v-model="formData.transport"
            @change="handleTransportChange"
          >
            <el-radio value="stdio">
              STDIO
            </el-radio>
            <el-radio value="sse">
              SSE
            </el-radio>
            <el-radio value="http">
              HTTP
            </el-radio>
          </el-radio-group>
          <div class="form-tip">
            STDIO: 标准输入输出 | SSE: Server-Sent Events | HTTP: HTTP 请求
          </div>
        </el-form-item>

        <!-- STDIO 模式配置 -->
        <template v-if="formData.transport === 'stdio'">
          <el-form-item
            label="启动命令"
            prop="command"
          >
            <el-input
              v-model="formData.command"
              placeholder="例如: node server.js"
            />
          </el-form-item>
          <el-form-item label="命令参数">
            <el-input
              v-model="argsText"
              type="textarea"
              :rows="2"
              placeholder="每行一个参数"
            />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input
              v-model="envText"
              type="textarea"
              :rows="3"
              placeholder="每行一个环境变量，格式: KEY=value"
            />
          </el-form-item>
        </template>

        <!-- SSE/HTTP 模式配置 -->
        <template v-if="formData.transport === 'sse' || formData.transport === 'http'">
          <el-form-item
            label="服务器 URL"
            prop="url"
          >
            <el-input
              v-model="formData.url"
              placeholder="https://example.com/mcp"
            />
          </el-form-item>
          <el-form-item label="认证方式">
            <el-select v-model="formData.auth_type">
              <el-option
                label="无认证"
                value="none"
              />
              <el-option
                label="Bearer Token"
                value="bearer"
              />
              <el-option
                label="Basic Auth"
                value="basic"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            v-if="formData.auth_type !== 'none'"
            label="认证令牌"
          >
            <el-input
              v-model="formData.auth_token"
              type="password"
              show-password
              placeholder="请输入认证令牌"
            />
          </el-form-item>
        </template>

        <el-form-item label="自动批准工具">
          <el-input
            v-model="autoApproveText"
            type="textarea"
            :rows="2"
            placeholder="每行一个工具名称，留空表示手动确认所有工具"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 工具列表对话框 -->
    <el-dialog
      v-model="showToolsDialog"
      title="可用工具"
      width="600px"
    >
      <el-table
        v-loading="toolsLoading"
        :data="serverTools"
        stripe
        max-height="400"
      >
        <el-table-column
          prop="name"
          label="工具名称"
          width="200"
        />
        <el-table-column
          prop="description"
          label="描述"
          show-overflow-tooltip
        />
      </el-table>
      <template #footer>
        <el-button @click="showToolsDialog = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试连接对话框 -->
    <el-dialog
      v-model="showTestDialog"
      title="测试连接"
      width="500px"
    >
      <div
        v-if="testResult"
        class="test-result"
      >
        <el-result
          :icon="testResult.success ? 'success' : 'error'"
          :title="testResult.success ? '连接成功' : '连接失败'"
        >
          <template #sub-title>
            <p>{{ testResult.message }}</p>
            <p v-if="testResult.latency_ms">
              延迟: {{ testResult.latency_ms }}ms
            </p>
          </template>
        </el-result>
      </div>
      <div
        v-else
        class="test-loading"
      >
        <p>正在测试连接...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Connection, Tools } from '@element-plus/icons-vue'
import { useTradingAgentsStore } from '../store'
import {
  TransportModeEnum,
  MCPServerStatusEnum,
  AuthTypeEnum,
  type MCPServerConfig,
  type MCPServerConfigCreate,
  type MCPTool,
} from '../types'

const store = useTradingAgentsStore()

// 当前标签页
const activeTab = ref('user')

// 对话框状态
const showCreateDialog = ref(false)
const showToolsDialog = ref(false)
const showTestDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)

// 表单引用
const formRef = ref()

// 提交状态
const submitting = ref(false)
const toolsLoading = ref(false)

// 工具列表
const serverTools = ref<MCPTool[]>([])

// 测试结果
const testResult = ref<{ success: boolean; message: string; latency_ms?: number } | null>(null)

// 表单数据
const formData = reactive<MCPServerConfigCreate>({
  name: '',
  transport: TransportModeEnum.STDIO,
  command: '',
  args: [],
  env: {},
  url: '',
  auth_type: AuthTypeEnum.NONE,
  auth_token: '',
  auto_approve: [],
  enabled: true,
  is_system: false,
})

// 文本格式字段（用于输入）
const argsText = ref('')
const envText = ref('')
const autoApproveText = ref('')

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
  ],
  transport: [
    { required: true, message: '请选择传输模式', trigger: 'change' },
  ],
  command: [
    { required: true, message: '请输入启动命令', trigger: 'blur' },
  ],
  url: [
    { required: true, message: '请输入服务器 URL', trigger: 'blur' },
  ],
}

// 获取传输模式标签类型
function getTransportTagType(transport: TransportModeEnum) {
  const types: Record<TransportModeEnum, string> = {
    [TransportModeEnum.STDIO]: 'primary',
    [TransportModeEnum.SSE]: 'success',
    [TransportModeEnum.HTTP]: 'warning',
  }
  return types[transport] || 'info'
}

// 获取状态标签类型
function getStatusTagType(status: MCPServerStatusEnum) {
  const types: Record<MCPServerStatusEnum, string> = {
    [MCPServerStatusEnum.AVAILABLE]: 'success',
    [MCPServerStatusEnum.UNAVAILABLE]: 'danger',
    [MCPServerStatusEnum.UNKNOWN]: 'info',
  }
  return types[status] || 'info'
}

// 获取状态标签
function getStatusLabel(status: MCPServerStatusEnum): string {
  const labels: Record<MCPServerStatusEnum, string> = {
    [MCPServerStatusEnum.AVAILABLE]: '可用',
    [MCPServerStatusEnum.UNAVAILABLE]: '不可用',
    [MCPServerStatusEnum.UNKNOWN]: '未知',
  }
  return labels[status] || status
}

// 传输模式变更
function handleTransportChange() {
  // 清空模式特定字段
  formData.command = ''
  formData.args = []
  formData.env = {}
  formData.url = ''
  argsText.value = ''
  envText.value = ''
}

// 提交表单
async function handleSubmit() {
  await formRef.value?.validate()

  // 解析文本字段
  if (formData.transport === 'stdio') {
    formData.args = argsText.value.split('\n').filter(s => s.trim())
    formData.env = Object.fromEntries(
      envText.value.split('\n')
        .filter(s => s.trim() && s.includes('='))
        .map(s => {
          const [key, ...valueParts] = s.split('=')
          return [key.trim(), valueParts.join('=').trim()]
        })
    )
  }

  formData.auto_approve = autoApproveText.value.split('\n').filter(s => s.trim())

  submitting.value = true

  try {
    if (isEdit.value && editingId.value) {
      await store.updateServer(editingId.value, formData)
    } else {
      await store.createServer(formData)
    }
    showCreateDialog.value = false
  } finally {
    submitting.value = false
  }
}

// 编辑服务器
function handleEdit(server: MCPServerConfig) {
  isEdit.value = true
  editingId.value = server.id

  Object.assign(formData, {
    name: server.name,
    transport: server.transport,
    command: server.command || '',
    args: server.args || [],
    env: server.env || {},
    url: server.url || '',
    auth_type: server.auth_type,
    auth_token: server.auth_token || '',
    auto_approve: server.auto_approve || [],
    enabled: server.enabled,
    is_system: server.is_system,
  })

  // 转换为文本格式
  argsText.value = (server.args || []).join('\n')
  envText.value = Object.entries(server.env || {})
    .map(([k, v]) => `${k}=${v}`)
    .join('\n')
  autoApproveText.value = (server.auto_approve || []).join('\n')

  showCreateDialog.value = true
}

// 删除服务器
async function handleDelete(server: MCPServerConfig) {
  try {
    await ElMessageBox.confirm(
      `确定要删除服务器 "${server.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await store.deleteServer(server.id)
  } catch {
    // 用户取消
  }
}

// 切换启用状态
async function handleToggleEnabled(server: MCPServerConfig) {
  try {
    await store.updateServer(server.id, { enabled: server.enabled })
  } catch (error) {
    server.enabled = !server.enabled
  }
}

// 查看工具列表
async function handleViewTools(server: MCPServerConfig) {
  showToolsDialog.value = true
  toolsLoading.value = true
  serverTools.value = []

  try {
    serverTools.value = await store.getServerTools(server.id)
  } catch (error) {
    ElMessage.error('获取工具列表失败')
  } finally {
    toolsLoading.value = false
  }
}

// 测试连接
async function handleTest(server: MCPServerConfig) {
  showTestDialog.value = true
  testResult.value = null

  try {
    const result = await store.testServer(server.id)
    testResult.value = result
  } catch (error) {
    testResult.value = {
      success: false,
      message: '测试请求失败',
    }
  }
}

// 关闭对话框
function handleDialogClose() {
  isEdit.value = false
  editingId.value = null
  formRef.value?.resetFields()
  argsText.value = ''
  envText.value = ''
  autoApproveText.value = ''
}

// 初始化
onMounted(() => {
  store.fetchServers()
})
</script>

<style scoped>
.mcp-server-management {
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

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}
</style>
