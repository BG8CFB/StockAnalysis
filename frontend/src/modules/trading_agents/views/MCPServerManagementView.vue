<template>
  <div class="mcp-server-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2>MCP 服务器管理</h2>
        <p class="page-description">
          配置 Model Context Protocol (MCP) 服务器以扩展 AI 智能体能力
        </p>
      </div>
      <div class="header-actions">
        <el-button @click="showImportFileDialog = true">
          <el-icon><Upload /></el-icon>
          导入MCP配置
        </el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="showJsonAddDialog = true"
        >
          手动添加
        </el-button>
      </div>
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

    <!-- 批量导入MCP配置对话框 (文件上传) -->
    <el-dialog
      v-model="showImportFileDialog"
      title="导入MCP配置"
      width="600px"
    >
      <div class="import-file-dialog">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        >
          上传 JSON 配置文件进行批量导入。支持 Claude Desktop 配置格式。
        </el-alert>

        <!-- 文件上传区域 -->
        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".json"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-icon class="el-icon--upload">
            <UploadFilled />
          </el-icon>
          <div class="el-upload__text">
            拖拽 JSON 文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传 .json 文件，支持 Claude Desktop 配置格式
            </div>
          </template>
        </el-upload>

        <!-- 解析结果 -->
        <div
          v-if="parsedImportConfig"
          class="parse-result"
        >
          <el-divider content-position="left">
            解析结果
          </el-divider>
          <el-tag type="success">
            检测到 {{ Object.keys(parsedImportConfig).length }} 个服务器
          </el-tag>
          <div class="server-list-preview">
            <div
              v-for="(config, name) in parsedImportConfig"
              :key="name"
              class="server-preview-item"
            >
              <el-icon><Monitor /></el-icon>
              <span class="server-name">{{ name }}</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ config.command || config.url || '未知' }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 错误提示 -->
        <el-alert
          v-if="importParseError"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 16px"
        >
          {{ importParseError }}
        </el-alert>
      </div>

      <template #footer>
        <el-button @click="showImportFileDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="importing"
          :disabled="!parsedImportConfig"
          @click="handleBatchImport"
        >
          导入配置
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动添加MCP服务器对话框 (JSON粘贴) -->
    <el-dialog
      v-model="showJsonAddDialog"
      title="手动添加MCP服务器"
      width="700px"
      @close="handleJsonAddClose"
    >
      <div class="json-add-dialog">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        >
          <template #title>
            粘贴单个 MCP 服务器的 JSON 配置
          </template>
          <template #default>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #606266;">
              此操作会累加到现有服务器列表中。同名服务器不会重复添加。
            </p>
          </template>
        </el-alert>

        <!-- 示例按钮 -->
        <div class="example-buttons">
          <el-button
            size="small"
            @click="loadSingleExample"
          >
            <el-icon><Document /></el-icon>
            加载示例配置
          </el-button>
          <el-button
            size="small"
            link
            type="primary"
            @click="openDocs"
          >
            <el-icon><Link /></el-icon>
            查看官方文档
          </el-button>
        </div>

        <!-- JSON 输入区域 -->
        <div class="editor-container">
          <el-input
            v-model="singleServerJson"
            type="textarea"
            :rows="12"
            placeholder="粘贴单个服务器的 JSON 配置，例如:
{
  &quot;command&quot;: &quot;npx&quot;,
  &quot;args&quot;: [&quot;-y&quot;, &quot;@modelcontextprotocol/server-filesystem&quot;, &quot;/path/to/files&quot;]
}"
            :autosize="{ minRows: 12, maxRows: 20 }"
          />
        </div>

        <!-- 解析结果 -->
        <div
          v-if="parsedSingleServer"
          class="parse-result"
        >
          <el-divider content-position="left">
            解析结果
          </el-divider>
          <el-descriptions
            :column="2"
            border
            size="small"
          >
            <el-descriptions-item label="服务器名称">
              {{ parsedSingleServer.name || '(自动生成)' }}
            </el-descriptions-item>
            <el-descriptions-item label="传输模式">
              {{ parsedSingleServer.transport?.toUpperCase() || 'STDIO' }}
            </el-descriptions-item>
            <el-descriptions-item
              label="命令/URL"
              :span="2"
            >
              {{ parsedSingleServer.command || parsedSingleServer.url || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 重复检测 -->
          <el-alert
            v-if="isDuplicateServer"
            type="warning"
            :closable="false"
            show-icon
            style="margin-top: 12px"
          >
            该服务器名称已存在，将跳过添加
          </el-alert>
        </div>

        <!-- 错误提示 -->
        <el-alert
          v-if="singleParseError"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 16px"
        >
          {{ singleParseError }}
        </el-alert>
      </div>

      <template #footer>
        <el-button @click="showJsonAddDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="addingSingle"
          :disabled="!parsedSingleServer || isDuplicateServer"
          @click="handleSingleAdd"
        >
          添加服务器
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动添加/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEdit ? '编辑服务器' : '手动添加服务器'"
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
              placeholder="例如: npx -y @modelcontextprotocol/server-filesystem"
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
            <el-select
              v-model="formData.auth_type"
              style="width: 160px"
            >
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
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile, type UploadRawFile } from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  Connection,
  Tools,
  Upload,
  UploadFilled,
  Document,
  Link,
  Monitor,
} from '@element-plus/icons-vue'
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
const showImportFileDialog = ref(false)  // 批量导入文件对话框
const showJsonAddDialog = ref(false)     // 单个添加JSON对话框
const showCreateDialog = ref(false)      // 表单创建/编辑对话框
const showToolsDialog = ref(false)
const showTestDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)

// 批量导入相关
const parsedImportConfig = ref<Record<string, any> | null>(null)
const importParseError = ref('')
const importing = ref(false)
const uploadRef = ref()

// 单个添加相关
const singleServerJson = ref('')
const parsedSingleServer = ref<any>(null)
const singleParseError = ref('')
const addingSingle = ref(false)

// 重复检测
const existingServerNames = computed(() => {
  return new Set([
    ...store.userServers.map(s => s.name),
    ...store.systemServers.map(s => s.name),
  ])
})

const isDuplicateServer = computed(() => {
  if (!parsedSingleServer?.value?.name) return false
  return existingServerNames.value.has(parsedSingleServer.value.name)
})

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

// =============================================================================
// 批量导入（文件上传）相关方法
// =============================================================================

// 处理文件选择
async function handleFileChange(file: UploadFile) {
  parsedImportConfig.value = null
  importParseError.value = ''

  if (!file.raw) return

  try {
    const text = await readFileContent(file.raw)
    const parsed = JSON.parse(text)

    // 支持 claude_desktop_config.json 格式或直接的对象格式
    const servers = parsed.mcpServers || parsed

    if (typeof servers === 'object' && servers !== null && !Array.isArray(servers)) {
      parsedImportConfig.value = servers
      importParseError.value = ''
    } else {
      importParseError.value = '无效的配置格式：需要 mcpServers 对象或服务器配置对象'
    }
  } catch (e: any) {
    importParseError.value = `JSON 解析错误: ${e.message}`
  }
}

// 处理文件移除
function handleFileRemove() {
  parsedImportConfig.value = null
  importParseError.value = ''
}

// 读取文件内容
function readFileContent(file: UploadRawFile): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result as string)
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}

// 批量导入
async function handleBatchImport() {
  if (!parsedImportConfig.value) {
    ElMessage.error('没有有效的配置可导入')
    return
  }

  importing.value = true
  let successCount = 0
  let failCount = 0
  let skipCount = 0

  try {
    for (const [name, config] of Object.entries(parsedImportConfig.value)) {
      // 检查是否重复
      if (existingServerNames.value.has(name)) {
        skipCount++
        continue
      }

      try {
        const serverConfig: MCPServerConfigCreate = {
          name,
          transport: config.url
            ? (config.transport === 'sse' ? TransportModeEnum.SSE : TransportModeEnum.HTTP)
            : TransportModeEnum.STDIO,
          command: config.command || '',
          args: config.args || [],
          env: config.env || {},
          url: config.url || '',
          enabled: true,
          is_system: false,
        }
        await store.createServer(serverConfig)
        successCount++
      } catch (error) {
        console.error(`导入服务器 ${name} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0 || skipCount > 0) {
      let msg = `成功导入 ${successCount} 个服务器`
      if (skipCount > 0) msg += `，跳过 ${skipCount} 个重复服务器`
      if (failCount > 0) msg += `，${failCount} 个失败`
      ElMessage.success(msg)
      showImportFileDialog.value = false
      store.fetchServers()
    } else {
      ElMessage.error('导入失败，请检查配置格式')
    }
  } finally {
    importing.value = false
  }
}

// =============================================================================
// 单个添加（JSON粘贴）相关方法
// =============================================================================

// 监听单个服务器 JSON 输入
watch(singleServerJson, (newVal) => {
  if (!newVal.trim()) {
    parsedSingleServer.value = null
    singleParseError.value = ''
    return
  }

  try {
    const parsed = JSON.parse(newVal)
    // 验证是否是有效的服务器配置
    if (typeof parsed === 'object' && parsed !== null) {
      // 如果是嵌套格式（如 mcpServers.servername），提取第一个服务器
      if (parsed.mcpServers) {
        const firstServer = Object.values(parsed.mcpServers)[0] as any
        if (firstServer) {
          parsedSingleServer.value = {
            name: Object.keys(parsed.mcpServers)[0],
            ...firstServer,
          }
          singleParseError.value = ''
          return
        }
      }

      // 直接是服务器配置
      parsedSingleServer.value = parsed
      singleParseError.value = ''
    } else {
      parsedSingleServer.value = null
      singleParseError.value = '无效的服务器配置格式'
    }
  } catch (e: any) {
    parsedSingleServer.value = null
    singleParseError.value = `JSON 解析错误: ${e.message}`
  }
})

// 加载单个服务器示例
function loadSingleExample() {
  singleServerJson.value = JSON.stringify(
    {
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/allowed/directory'],
      env: {},
    },
    null,
    2
  )
}

// 打开文档
function openDocs() {
  window.open('https://modelcontextprotocol.io/docs/tools/', '_blank')
}

// 单个添加服务器
async function handleSingleAdd() {
  if (!parsedSingleServer.value) {
    ElMessage.error('没有有效的配置可添加')
    return
  }

  if (isDuplicateServer.value) {
    ElMessage.error('该服务器名称已存在')
    return
  }

  addingSingle.value = true

  try {
    const serverConfig: MCPServerConfigCreate = {
      name: parsedSingleServer.value.name || `mcp_${Date.now()}`,
      transport: parsedSingleServer.value.url
        ? (parsedSingleServer.value.transport === 'sse' ? TransportModeEnum.SSE : TransportModeEnum.HTTP)
        : TransportModeEnum.STDIO,
      command: parsedSingleServer.value.command || '',
      args: parsedSingleServer.value.args || [],
      env: parsedSingleServer.value.env || {},
      url: parsedSingleServer.value.url || '',
      enabled: true,
      is_system: false,
    }

    await store.createServer(serverConfig)
    ElMessage.success('服务器添加成功')
    showJsonAddDialog.value = false
    store.fetchServers()
  } catch (error) {
    ElMessage.error('添加服务器失败')
  } finally {
    addingSingle.value = false
  }
}

// 关闭单个添加对话框
function handleJsonAddClose() {
  singleServerJson.value = ''
  parsedSingleServer.value = null
  singleParseError.value = ''
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
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}

.page-description {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 文件上传对话框样式 */
.import-file-dialog {
  padding: 8px 0;
}

.upload-area {
  margin-bottom: 20px;
}

.upload-area :deep(.el-upload-dragger) {
  padding: 40px 20px;
}

.upload-area .el-icon--upload {
  font-size: 67px;
  color: #409eff;
  margin-bottom: 16px;
}

/* JSON添加对话框样式 */
.json-add-dialog {
  padding: 8px 0;
}

.example-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.editor-container {
  margin-bottom: 16px;
}

.parse-result {
  margin-top: 20px;
}

.server-list-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.server-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #fff;
  border-radius: 4px;
}

.server-name {
  flex: 1;
  font-weight: 500;
  color: #303133;
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
