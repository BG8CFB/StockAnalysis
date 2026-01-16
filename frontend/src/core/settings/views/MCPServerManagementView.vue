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
        <!-- MCP 系统设置 - 仅管理员可见 -->
        <el-button
          v-if="canManageSystemServers"
          :icon="Setting"
          @click="showSystemSettingsDialog = true"
        >
          系统设置
        </el-button>
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
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <p>正在测试连接...</p>
      </div>
    </el-dialog>

    <!-- MCP 系统设置对话框 - 仅管理员可见 -->
    <el-dialog
      v-model="showSystemSettingsDialog"
      title="MCP 系统配置"
      width="700px"
      @close="handleSystemSettingsClose"
    >
      <el-form
        ref="settingsFormRef"
        :model="systemSettings"
        :rules="systemSettingsRules"
        label-width="160px"
        class="system-settings-form"
      >
        <!-- 连接池配置 -->
        <div class="settings-section">
          <h4 class="section-title">
            <el-icon><Connection /></el-icon>
            连接池配置
          </h4>

          <el-form-item
            label="个人并发上限"
            prop="pool_personal_max_concurrency"
          >
            <el-input-number
              v-model="systemSettings.pool_personal_max_concurrency"
              :min="1"
              :max="1000"
              :step="10"
            />
            <span class="form-item-desc">每个用户的个人 MCP 最大并发连接数</span>
          </el-form-item>

          <el-form-item
            label="公共并发上限"
            prop="pool_public_per_user_max"
          >
            <el-input-number
              v-model="systemSettings.pool_public_per_user_max"
              :min="1"
              :max="100"
              :step="1"
            />
            <span class="form-item-desc">每个用户使用公共 MCP 的最大并发连接数</span>
          </el-form-item>

          <el-form-item
            label="个人队列大小"
            prop="pool_personal_queue_size"
          >
            <el-input-number
              v-model="systemSettings.pool_personal_queue_size"
              :min="10"
              :max="1000"
              :step="10"
            />
            <span class="form-item-desc">个人 MCP 请求队列最大容量</span>
          </el-form-item>

          <el-form-item
            label="公共队列大小"
            prop="pool_public_queue_size"
          >
            <el-input-number
              v-model="systemSettings.pool_public_queue_size"
              :min="10"
              :max="500"
              :step="10"
            />
            <span class="form-item-desc">公共 MCP 请求队列最大容量</span>
          </el-form-item>
        </div>

        <!-- 连接生命周期配置 -->
        <div class="settings-section">
          <h4 class="section-title">
            <el-icon><Timer /></el-icon>
            连接生命周期
          </h4>

          <el-form-item
            label="完成超时时间"
            prop="connection_complete_timeout"
          >
            <el-input-number
              v-model="systemSettings.connection_complete_timeout"
              :min="1"
              :max="300"
              :step="1"
            />
            <span class="form-item-desc">任务完成后连接销毁等待时间（秒）</span>
          </el-form-item>

          <el-form-item
            label="失败超时时间"
            prop="connection_failed_timeout"
          >
            <el-input-number
              v-model="systemSettings.connection_failed_timeout"
              :min="1"
              :max="600"
              :step="1"
            />
            <span class="form-item-desc">任务失败后连接销毁等待时间（秒）</span>
          </el-form-item>
        </div>

        <!-- 健康检查配置 -->
        <div class="settings-section">
          <h4 class="section-title">
            <el-icon><Monitor /></el-icon>
            健康检查
          </h4>

          <el-form-item
            label="启用健康检查"
            prop="health_check_enabled"
          >
            <el-switch v-model="systemSettings.health_check_enabled" />
            <span class="form-item-desc">自动检测 MCP 服务器状态</span>
          </el-form-item>

          <el-form-item
            label="检查间隔时间"
            prop="health_check_interval"
          >
            <el-input-number
              v-model="systemSettings.health_check_interval"
              :min="10"
              :max="3600"
              :step="10"
              :disabled="!systemSettings.health_check_enabled"
            />
            <span class="form-item-desc">健康检查间隔时间（秒）</span>
          </el-form-item>

          <el-form-item
            label="检查超时时间"
            prop="health_check_timeout"
          >
            <el-input-number
              v-model="systemSettings.health_check_timeout"
              :min="5"
              :max="300"
              :step="1"
              :disabled="!systemSettings.health_check_enabled"
            />
            <span class="form-item-desc">单次健康检查超时时间（秒）</span>
          </el-form-item>
        </div>

        <!-- 最后更新时间 -->
        <div
          v-if="systemSettings.updated_at"
          class="last-updated"
        >
          <el-text
            type="info"
            size="small"
          >
            最后更新: {{ formatUpdateTime(systemSettings.updated_at) }}
          </el-text>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="handleSystemSettingsReset">
          恢复默认
        </el-button>
        <el-button
          type="primary"
          :loading="systemSettingsSaving"
          @click="handleSystemSettingsSave"
        >
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile, type UploadRawFile, type FormInstance, type FormRules } from 'element-plus'
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
  Setting,
  Timer,
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { useTradingAgentsStore } from '@/modules/trading_agents/store'
import {
  TransportModeEnum,
  MCPServerStatusEnum,
  type MCPServerConfig,
  type MCPServerConfigCreate,
  type MCPTool,
} from '@/modules/trading_agents/types'
import { getMCPSettings, updateMCPSettings, resetMCPSettings, type MCPSystemSettings } from '../api/mcp'

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
const showSystemSettingsDialog = ref(false)  // MCP 系统设置对话框

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
// MCP 系统设置相关
// =============================================================================

// MCP 系统设置表单引用
const settingsFormRef = ref<FormInstance>()

// MCP 系统设置状态
const systemSettingsSaving = ref(false)

// MCP 系统设置数据
const systemSettings = reactive<MCPSystemSettings>({
  pool_personal_max_concurrency: 100,
  pool_public_per_user_max: 10,
  pool_personal_queue_size: 200,
  pool_public_queue_size: 50,
  connection_complete_timeout: 10,
  connection_failed_timeout: 30,
  health_check_enabled: true,
  health_check_interval: 300,
  health_check_timeout: 30,
})

// MCP 系统设置验证规则
const systemSettingsRules: FormRules<MCPSystemSettings> = {
  pool_personal_max_concurrency: [
    { required: true, message: '请输入个人并发上限', trigger: 'blur' },
    { type: 'number', min: 1, max: 1000, message: '范围为 1-1000', trigger: 'blur' },
  ],
  pool_public_per_user_max: [
    { required: true, message: '请输入公共并发上限', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '范围为 1-100', trigger: 'blur' },
  ],
  pool_personal_queue_size: [
    { required: true, message: '请输入个人队列大小', trigger: 'blur' },
    { type: 'number', min: 10, max: 1000, message: '范围为 10-1000', trigger: 'blur' },
  ],
  pool_public_queue_size: [
    { required: true, message: '请输入公共队列大小', trigger: 'blur' },
    { type: 'number', min: 10, max: 500, message: '范围为 10-500', trigger: 'blur' },
  ],
  connection_complete_timeout: [
    { required: true, message: '请输入完成超时时间', trigger: 'blur' },
    { type: 'number', min: 1, max: 300, message: '范围为 1-300', trigger: 'blur' },
  ],
  connection_failed_timeout: [
    { required: true, message: '请输入失败超时时间', trigger: 'blur' },
    { type: 'number', min: 1, max: 600, message: '范围为 1-600', trigger: 'blur' },
  ],
  health_check_interval: [
    { required: true, message: '请输入检查间隔时间', trigger: 'blur' },
    { type: 'number', min: 10, max: 3600, message: '范围为 10-3600', trigger: 'blur' },
  ],
  health_check_timeout: [
    { required: true, message: '请输入检查超时时间', trigger: 'blur' },
    { type: 'number', min: 5, max: 300, message: '范围为 5-300', trigger: 'blur' },
  ],
}

// 加载 MCP 系统设置
async function loadSystemSettings() {
  try {
    const data = await getMCPSettings()
    Object.assign(systemSettings, data)
  } catch (error) {
    ElMessage.error('加载系统配置失败')
  }
}

// 保存 MCP 系统设置
async function handleSystemSettingsSave() {
  if (!settingsFormRef.value) return

  await settingsFormRef.value.validate(async (valid) => {
    if (!valid) return

    systemSettingsSaving.value = true
    try {
      const data = await updateMCPSettings(systemSettings)
      Object.assign(systemSettings, data)
      ElMessage.success('MCP 系统配置已保存，已对所有用户生效')
      showSystemSettingsDialog.value = false
    } catch (error) {
      ElMessage.error('保存系统配置失败')
    } finally {
      systemSettingsSaving.value = false
    }
  })
}

// 恢复默认 MCP 系统设置
async function handleSystemSettingsReset() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复为默认配置吗？当前配置将被清空，系统将使用 YAML 默认值。',
      '恢复默认配置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await resetMCPSettings()
    await loadSystemSettings()
    ElMessage.success('已恢复为默认配置')
  } catch {
    // 用户取消
  }
}

// 关闭 MCP 系统设置对话框
function handleSystemSettingsClose() {
  // 重新加载配置以确保数据一致
  loadSystemSettings()
}

// 格式化更新时间
function formatUpdateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

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
  // 管理员加载系统配置
  if (canManageSystemServers.value) {
    loadSystemSettings()
  }
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

/* MCP 系统设置对话框样式 */
.system-settings-form {
  max-height: 500px;
  overflow-y: auto;
  padding: 8px 0;
}

.settings-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.settings-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.section-title .el-icon {
  color: #409eff;
}

.form-item-desc {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
</style>
