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
        <!-- 导入配置 - 所有用户可用 -->
        <el-button
          :icon="Upload"
          @click="openImportDialog"
        >
          导入配置
        </el-button>
        <!-- 添加个人服务 - 所有用户可用 -->
        <el-button
          type="primary"
          :icon="Plus"
          @click="openAddServerDialog(false)"
        >
          添加个人服务
        </el-button>
        <!-- 添加公共服务 - 管理员和超管可见 -->
        <el-button
          v-if="canManageSystemServers"
          type="warning"
          :icon="Plus"
          @click="openAddServerDialog(true)"
        >
          添加公共服务
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
              width="160"
            />
            <el-table-column
              prop="transport"
              label="传输模式"
              width="90"
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
              width="90"
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
              width="70"
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
              width="280"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  size="small"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Tools"
                  size="small"
                  @click="handleViewTools(row)"
                >
                  工具
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Edit"
                  size="small"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  size="small"
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
          label="公共服务"
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
              width="160"
            />
            <el-table-column
              prop="transport"
              label="传输模式"
              width="90"
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
              width="90"
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
              width="70"
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
              width="280"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :icon="Connection"
                  size="small"
                  @click="handleTest(row)"
                >
                  测试
                </el-button>
                <el-button
                  link
                  type="primary"
                  :icon="Tools"
                  size="small"
                  @click="handleViewTools(row)"
                >
                  工具
                </el-button>
                <!-- 编辑按钮 - 管理员和超管可见 -->
                <el-button
                  v-if="canManageSystemServers"
                  link
                  type="primary"
                  :icon="Edit"
                  size="small"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <!-- 删除按钮 - 管理员和超管可见 -->
                <el-button
                  v-if="canManageSystemServers"
                  link
                  type="danger"
                  :icon="Delete"
                  size="small"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入 MCP 配置"
      width="700px"
    >
      <div class="import-dialog">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        >
          上传 JSON 配置文件进行批量导入。支持 Claude Desktop 配置格式。
        </el-alert>

        <!-- 服务类型选择 - 管理员和超管可见 -->
        <div
          v-if="canManageSystemServers"
          class="import-type-selector"
        >
          <div class="selector-label">
            <el-icon><InfoFilled /></el-icon>
            <span>导入为：</span>
          </div>
          <el-radio-group v-model="importAsSystem">
            <el-radio :label="false">
              <strong>个人服务</strong>
              <span class="radio-desc">（仅自己可用）</span>
            </el-radio>
            <el-radio :label="true">
              <strong>公共服务</strong>
              <span class="radio-desc">（所有用户可用）</span>
            </el-radio>
          </el-radio-group>
        </div>

        <!-- 普通用户提示 -->
        <el-alert
          v-else
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        >
          <strong>注意：</strong>您当前导入的配置将添加为个人服务（仅自己可用）。
          如需导入公共服务，请联系管理员。
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
          <div class="import-summary">
            <el-tag type="success">
              检测到 {{ Object.keys(parsedImportConfig).length }} 个服务器
            </el-tag>
            <el-tag
              v-if="canManageSystemServers"
              :type="importAsSystem ? 'warning' : 'primary'"
              style="margin-left: 8px"
            >
              将导入为{{ importAsSystem ? '公共服务' : '个人服务' }}
            </el-tag>
          </div>
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
        <el-button @click="showImportDialog = false">
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

    <!-- 添加/编辑服务器对话框 (统一JSON编辑器) -->
    <el-dialog
      v-model="showJsonEditDialog"
      :title="jsonEditTitle"
      width="800px"
      @close="handleJsonEditClose"
    >
      <div class="json-edit-dialog">
        <!-- 提示信息 -->
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          <template #title>
            {{ jsonEditDescription }}
          </template>
        </el-alert>

        <!-- 示例按钮 -->
        <div class="example-buttons">
          <el-button
            size="small"
            @click="loadExample"
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
          <!-- 格式化按钮 -->
          <el-button
            size="small"
            @click="formatJson"
          >
            <el-icon><MagicStick /></el-icon>
            格式化 JSON
          </el-button>
        </div>

        <!-- JSON 编辑器 -->
        <div class="editor-container">
          <el-input
            ref="jsonEditorRef"
            v-model="serverJson"
            type="textarea"
            :rows="18"
            placeholder="粘贴 MCP 服务器的 JSON 配置，例如:
{
  &quot;command&quot;: &quot;npx&quot;,
  &quot;args&quot;: [&quot;-y&quot;, &quot;@modelcontextprotocol/server-filesystem&quot;, &quot;/path/to/files&quot;]
}"
          />
        </div>

        <!-- 解析结果 -->
        <div
          v-if="parsedServer"
          class="parse-result"
        >
          <el-divider content-position="left">
            配置预览
          </el-divider>
          <el-descriptions
            :column="2"
            border
            size="small"
          >
            <el-descriptions-item label="服务器名称">
              {{ parsedServer.name || '(自动生成)' }}
            </el-descriptions-item>
            <el-descriptions-item label="传输模式">
              {{ parsedServer.transport?.toUpperCase() || 'STDIO' }}
            </el-descriptions-item>
            <el-descriptions-item
              label="命令/URL"
              :span="2"
            >
              {{ parsedServer.command || parsedServer.url || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="服务类型">
              <el-tag
                :type="isCreatingPublicServer ? 'warning' : 'primary'"
                size="small"
              >
                {{ isCreatingPublicServer ? '公共服务' : '个人服务' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="操作">
              <el-tag
                :type="isEditMode ? 'success' : 'info'"
                size="small"
              >
                {{ isEditMode ? '更新现有配置' : '创建新服务' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <!-- 重复检测 -->
          <el-alert
            v-if="isDuplicateServer && !isEditMode"
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
          v-if="jsonParseError"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 16px"
        >
          {{ jsonParseError }}
        </el-alert>
      </div>

      <template #footer>
        <el-button @click="showJsonEditDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!parsedServer || (isDuplicateServer && !isEditMode)"
          @click="handleJsonEditSubmit"
        >
          {{ isEditMode ? '保存修改' : '添加服务器' }}
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
        <el-icon class="is-loading"><Loading /></el-icon>
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
  MagicStick,
  Loading,
  InfoFilled,
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '../store'
import {
  TransportModeEnum,
  MCPServerStatusEnum,
  type MCPServerConfig,
  type MCPServerConfigCreate,
  type MCPTool,
} from '../types'

const userStore = useUserStore()
const store = useTradingAgentsStore()

// 是否为管理员或超管（可以管理系统服务）
const canManageSystemServers = computed(() =>
  userStore.userInfo?.role === 'ADMIN' || userStore.userInfo?.role === 'SUPER_ADMIN'
)

// 是否为超管（保留，用于其他特殊权限）
const isSuperAdmin = computed(() => userStore.userInfo?.role === 'SUPER_ADMIN')

// 当前标签页
const activeTab = ref('user')

// 对话框状态
const showImportDialog = ref(false)      // 导入配置对话框
const showJsonEditDialog = ref(false)    // JSON编辑对话框(添加/编辑统一)
const showToolsDialog = ref(false)
const showTestDialog = ref(false)

// JSON编辑器状态
const isEditMode = ref(false)            // 是否为编辑模式
const isCreatingPublicServer = ref(false) // 是否正在创建公共服务
const editingId = ref<string | null>(null)
const serverJson = ref('')
const parsedServer = ref<any>(null)
const jsonParseError = ref('')

// 导入相关
const parsedImportConfig = ref<Record<string, any> | null>(null)
const importParseError = ref('')
const importing = ref(false)
const uploadRef = ref()
const importAsSystem = ref(false) // 导入为公共服务（仅超管可设置）

// 提交状态
const submitting = ref(false)
const toolsLoading = ref(false)

// 工具列表
const serverTools = ref<MCPTool[]>([])

// 测试结果
const testResult = ref<{ success: boolean; message: string; latency_ms?: number } | null>(null)

// 编辑器引用
const jsonEditorRef = ref()

// 对话框标题和描述
const jsonEditTitle = computed(() => {
  if (isEditMode.value) {
    return '编辑 MCP 服务器'
  }
  return isCreatingPublicServer.value ? '添加公共服务' : '添加个人服务'
})

const jsonEditDescription = computed(() => {
  if (isEditMode.value) {
    return '修改配置后点击保存，所有字段都会更新'
  }
  return '粘贴 MCP 服务器的 JSON 配置，点击添加后将自动导入系统'
})

// 重复检测
const existingServerNames = computed(() => {
  return new Set([
    ...store.userServers.map(s => s.name),
    ...store.systemServers.map(s => s.name),
  ])
})

const isDuplicateServer = computed(() => {
  if (!parsedServer.value?.name) return false
  // 编辑模式下，如果是同一个服务器不算重复
  if (isEditMode.value && editingId.value) {
    const currentServer = [...store.userServers, ...store.systemServers]
      .find(s => s.id === editingId.value)
    if (currentServer && currentServer.name === parsedServer.value.name) {
      return false
    }
  }
  return existingServerNames.value.has(parsedServer.value.name)
})

// =============================================================================
// 导入配置相关方法
// =============================================================================

// 打开导入对话框
function openImportDialog() {
  // 重置状态
  importAsSystem.value = false // 默认导入为个人服务
  parsedImportConfig.value = null
  importParseError.value = ''
  showImportDialog.value = true
}

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
          headers: config.headers || {},
          enabled: true,
          is_system: importAsSystem.value, // 根据用户选择导入为公共服务或个人服务
        }
        await store.createServer(serverConfig)
        successCount++
      } catch (error) {
        console.error(`导入服务器 ${name} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0 || skipCount > 0) {
      let msg = `成功导入 ${successCount} 个${importAsSystem.value ? '公共服务' : '个人服务'}`
      if (skipCount > 0) msg += `，跳过 ${skipCount} 个重复服务器`
      if (failCount > 0) msg += `，${failCount} 个失败`
      ElMessage.success(msg)
      showImportDialog.value = false
      store.fetchServers()
    } else {
      ElMessage.error('导入失败，请检查配置格式')
    }
  } finally {
    importing.value = false
  }
}

// =============================================================================
// JSON编辑器相关方法（添加/编辑统一）
// =============================================================================

// 打开添加服务器对话框
function openAddServerDialog(isPublic: boolean) {
  isEditMode.value = false
  isCreatingPublicServer.value = isPublic
  editingId.value = null
  serverJson.value = ''
  parsedServer.value = null
  jsonParseError.value = ''
  showJsonEditDialog.value = true
}

// 监听JSON输入，实时解析
watch(serverJson, (newVal) => {
  if (!newVal.trim()) {
    parsedServer.value = null
    jsonParseError.value = ''
    return
  }

  try {
    const parsed = JSON.parse(newVal)
    if (typeof parsed === 'object' && parsed !== null) {
      // 如果是嵌套格式（如 mcpServers.servername），提取第一个服务器
      if (parsed.mcpServers) {
        const firstServer = Object.values(parsed.mcpServers)[0] as any
        if (firstServer) {
          parsedServer.value = {
            name: Object.keys(parsed.mcpServers)[0],
            ...firstServer,
          }
          jsonParseError.value = ''
          return
        }
      }

      // 直接是服务器配置
      parsedServer.value = parsed
      jsonParseError.value = ''
    } else {
      parsedServer.value = null
      jsonParseError.value = '无效的服务器配置格式'
    }
  } catch (e: any) {
    parsedServer.value = null
    jsonParseError.value = `JSON 解析错误: ${e.message}`
  }
})

// 加载示例配置
function loadExample() {
  serverJson.value = JSON.stringify(
    {
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/allowed/directory'],
      env: {},
    },
    null,
    2
  )
}

// 格式化JSON
function formatJson() {
  if (!serverJson.value.trim()) {
    ElMessage.warning('请先输入JSON配置')
    return
  }

  try {
    const parsed = JSON.parse(serverJson.value)
    serverJson.value = JSON.stringify(parsed, null, 2)
    ElMessage.success('JSON格式化成功')
  } catch (e: any) {
    ElMessage.error(`JSON格式错误: ${e.message}`)
  }
}

// 打开文档
function openDocs() {
  window.open('https://modelcontextprotocol.io/docs/tools/', '_blank')
}

// 提交JSON编辑
async function handleJsonEditSubmit() {
  if (!parsedServer.value) {
    ElMessage.error('没有有效的配置可保存')
    return
  }

  if (isDuplicateServer.value && !isEditMode.value) {
    ElMessage.error('该服务器名称已存在')
    return
  }

  submitting.value = true

  try {
    const serverConfig: MCPServerConfigCreate = {
      name: parsedServer.value.name || `mcp_${Date.now()}`,
      transport: parsedServer.value.url
        ? (parsedServer.value.transport === 'sse' ? TransportModeEnum.SSE : TransportModeEnum.HTTP)
        : TransportModeEnum.STDIO,
      command: parsedServer.value.command || '',
      args: parsedServer.value.args || [],
      env: parsedServer.value.env || {},
      url: parsedServer.value.url || '',
      headers: parsedServer.value.headers || {},
      enabled: parsedServer.value.enabled !== undefined ? parsedServer.value.enabled : true,
      is_system: isCreatingPublicServer.value,
    }

    if (isEditMode.value && editingId.value) {
      // 编辑模式
      await store.updateServer(editingId.value, serverConfig)
      ElMessage.success('服务器配置已更新')
    } else {
      // 添加模式
      await store.createServer(serverConfig)
      ElMessage.success('服务器添加成功')
    }

    showJsonEditDialog.value = false
    store.fetchServers()
  } catch (error) {
    ElMessage.error(isEditMode.value ? '更新服务器失败' : '添加服务器失败')
  } finally {
    submitting.value = false
  }
}

// 关闭JSON编辑对话框
function handleJsonEditClose() {
  serverJson.value = ''
  parsedServer.value = null
  jsonParseError.value = ''
  isEditMode.value = false
  editingId.value = null
}

// =============================================================================
// 服务器操作相关方法
// =============================================================================

// 编辑服务器
function handleEdit(server: MCPServerConfig) {
  isEditMode.value = true
  isCreatingPublicServer.value = server.is_system
  editingId.value = server.id

  // 构建完整配置对象
  const fullConfig: any = {
    name: server.name,
    transport: server.transport,
    enabled: server.enabled,
  }

  // 根据传输模式添加字段
  if (server.transport === TransportModeEnum.STDIO) {
    if (server.command) fullConfig.command = server.command
    if (server.args && server.args.length > 0) fullConfig.args = server.args
    if (server.env && Object.keys(server.env).length > 0) fullConfig.env = server.env
  } else {
    if (server.url) fullConfig.url = server.url
    if (server.headers && Object.keys(server.headers).length > 0) fullConfig.headers = server.headers
    if (server.auth_type && server.auth_type !== 'none') {
      fullConfig.auth_type = server.auth_type
      if (server.auth_token) fullConfig.auth_token = server.auth_token
    }
  }

  serverJson.value = JSON.stringify(fullConfig, null, 2)
  parsedServer.value = fullConfig
  jsonParseError.value = ''

  showJsonEditDialog.value = true
}

// 删除服务器
async function handleDelete(server: MCPServerConfig) {
  try {
    await ElMessageBox.confirm(
      `确定要删除${server.is_system ? '公共服务' : '个人服务'} "${server.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await store.deleteServer(server.id, server.is_system)
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
    ElMessage.error('更新启用状态失败')
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

// =============================================================================
// 辅助方法
// =============================================================================

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

/* 导入对话框样式 */
.import-dialog,
.json-edit-dialog {
  padding: 8px 0;
}

.import-type-selector {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.selector-label .el-icon {
  color: #409eff;
}

.import-type-selector :deep(.el-radio-group) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.import-type-selector :deep(.el-radio) {
  margin-right: 0;
  padding: 12px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fff;
  transition: all 0.3s;
}

.import-type-selector :deep(.el-radio:hover) {
  border-color: #409eff;
  background: #ecf5ff;
}

.import-type-selector :deep(.el-radio.is-checked) {
  border-color: #409eff;
  background: #ecf5ff;
}

.radio-desc {
  margin-left: 8px;
  font-size: 13px;
  color: #909399;
  font-weight: normal;
}

.import-summary {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
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

/* JSON编辑对话框样式 */
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

.test-result,
.test-loading {
  text-align: center;
  padding: 20px;
}

.test-loading .el-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}
</style>
