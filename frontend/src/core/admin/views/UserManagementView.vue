<template>
  <div class="user-management">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>用户管理</h2>
          <el-button
            type="primary"
            :icon="Refresh"
            :loading="loading"
            @click="fetchData"
          >
            刷新
          </el-button>
        </div>
      </template>

      <!-- 搜索筛选栏 -->
      <el-form
        :inline="true"
        :model="query"
        class="search-form"
      >
        <el-form-item label="搜索">
          <el-input
            v-model="query.search"
            placeholder="邮箱或用户名"
            clearable
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
          >
            <el-option
              label="待审核"
              value="pending"
            />
            <el-option
              label="已激活"
              value="active"
            />
            <el-option
              label="已禁用"
              value="disabled"
            />
            <el-option
              label="已拒绝"
              value="rejected"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="query.role"
            placeholder="全部"
            clearable
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option
              label="用户"
              value="USER"
            />
            <el-option
              label="管理员"
              value="ADMIN"
            />
            <el-option
              label="超级管理员"
              value="SUPER_ADMIN"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="激活状态">
          <el-select
            v-model="query.is_active"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
          >
            <el-option
              label="已激活"
              :value="true"
            />
            <el-option
              label="未激活"
              :value="false"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 用户列表 -->
      <el-table
        v-loading="loading"
        :data="users"
        stripe
        style="width: 100%"
      >
        <el-table-column
          prop="email"
          label="邮箱"
          width="220"
        />
        <el-table-column
          prop="username"
          label="用户名"
          width="150"
        />
        <el-table-column
          prop="role"
          label="角色"
          width="120"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.role === 'SUPER_ADMIN'"
              type="danger"
            >
              超级管理员
            </el-tag>
            <el-tag
              v-else-if="row.role === 'ADMIN'"
              type="warning"
            >
              管理员
            </el-tag>
            <el-tag
              v-else
              type="info"
            >
              用户
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="status"
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.status === 'pending'"
              type="warning"
            >
              待审核
            </el-tag>
            <el-tag
              v-else-if="row.status === 'active'"
              type="success"
            >
              已激活
            </el-tag>
            <el-tag
              v-else-if="row.status === 'disabled'"
              type="info"
            >
              已禁用
            </el-tag>
            <el-tag
              v-else-if="row.status === 'rejected'"
              type="danger"
            >
              已拒绝
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="is_active"
          label="激活"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.is_active ? 'success' : 'info'"
              size="small"
            >
              {{ row.is_active ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          label="注册时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="last_login"
          label="最后登录"
          width="180"
        >
          <template #default="{ row }">
            {{ row.last_login ? formatDateTime(row.last_login) : '从未登录' }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          fixed="right"
          width="280"
        >
          <template #default="{ row }">
            <!-- 待审核用户操作 -->
            <template v-if="row.status === 'pending'">
              <el-button
                type="success"
                size="small"
                @click="handleApprove(row)"
              >
                通过
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="handleReject(row)"
              >
                拒绝
              </el-button>
            </template>
            <!-- 已激活用户操作 -->
            <template v-else-if="row.status === 'active'">
              <el-button
                type="warning"
                size="small"
                @click="handleDisable(row)"
              >
                禁用
              </el-button>
              <el-button
                type="primary"
                size="small"
                @click="handleResetPassword(row)"
              >
                重置密码
              </el-button>
              <el-dropdown @command="(cmd) => handleUserCommand(cmd, row)">
                <el-button
                  size="small"
                  :icon="More"
                  circle
                />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="role">
                      修改角色
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="delete"
                      divided
                    >
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            <!-- 已禁用用户操作 -->
            <template v-else-if="row.status === 'disabled'">
              <el-button
                type="success"
                size="small"
                @click="handleEnable(row)"
              >
                启用
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </template>
            <!-- 已拒绝用户 -->
            <template v-else-if="row.status === 'rejected'">
              <el-button
                type="danger"
                size="small"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 拒绝用户对话框 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝用户"
      width="500px"
    >
      <el-form
        :model="rejectForm"
        label-width="80px"
      >
        <el-form-item label="拒绝原因">
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入拒绝原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="danger"
          @click="confirmReject"
        >
          确认拒绝
        </el-button>
      </template>
    </el-dialog>

    <!-- 禁用用户对话框 -->
    <el-dialog
      v-model="disableDialogVisible"
      title="禁用用户"
      width="500px"
    >
      <el-form
        :model="disableForm"
        label-width="80px"
      >
        <el-form-item label="禁用原因">
          <el-input
            v-model="disableForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入禁用原因（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="disableDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="warning"
          @click="confirmDisable"
        >
          确认禁用
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改角色对话框 -->
    <el-dialog
      v-model="roleDialogVisible"
      title="修改用户角色"
      width="400px"
    >
      <el-form
        :model="roleForm"
        label-width="80px"
      >
        <el-form-item label="当前角色">
          <el-tag>{{ getRoleLabel(roleForm.currentRole) }}</el-tag>
        </el-form-item>
        <el-form-item label="新角色">
          <el-select
            v-model="roleForm.newRole"
            placeholder="选择角色"
            style="width: 140px"
          >
            <el-option
              label="用户"
              value="USER"
            />
            <el-option
              label="管理员"
              value="ADMIN"
            />
            <el-option
              label="超级管理员"
              value="SUPER_ADMIN"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmChangeRole"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, More } from '@element-plus/icons-vue'
import { useAdminStore } from '@core/admin'
import type { User, UserListQuery } from '@core/user'

const adminStore = useAdminStore()

// 查询参数
const query = reactive<UserListQuery>({
  skip: 0,
  limit: 20,
  search: '',
  status: undefined,
  role: undefined,
  is_active: undefined,
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 用户列表
const users = computed(() => adminStore.users)
const total = computed(() => adminStore.total)
const loading = ref(false)

// 对话框状态
const rejectDialogVisible = ref(false)
const disableDialogVisible = ref(false)
const roleDialogVisible = ref(false)

// 表单数据
const rejectForm = reactive({
  userId: '',
  reason: '',
})

const disableForm = reactive({
  userId: '',
  reason: '',
})

const roleForm = reactive({
  userId: '',
  currentRole: '',
  newRole: '',
})

// 获取数据
async function fetchData() {
  loading.value = true
  try {
    query.skip = (currentPage.value - 1) * pageSize.value
    query.limit = pageSize.value
    await adminStore.fetchUsers(query)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  currentPage.value = 1
  fetchData()
}

// 分页变化
function handlePageChange(page: number) {
  currentPage.value = page
  fetchData()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  fetchData()
}

// 通过用户审核
async function handleApprove(user: User) {
  try {
    await ElMessageBox.confirm(
      `确认通过用户 ${user.username} 的审核申请？`,
      '确认操作',
      { type: 'warning' }
    )
    await adminStore.approveUser(user.id)
    ElMessage.success('用户审核通过')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 拒绝用户
function handleReject(user: User) {
  rejectForm.userId = user.id
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }
  try {
    await adminStore.rejectUser(rejectForm.userId, rejectForm.reason)
    ElMessage.success('用户已拒绝')
    rejectDialogVisible.value = false
    fetchData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// 禁用用户
function handleDisable(user: User) {
  disableForm.userId = user.id
  disableForm.reason = ''
  disableDialogVisible.value = true
}

async function confirmDisable() {
  try {
    await adminStore.disableUser(disableForm.userId, disableForm.reason || undefined)
    ElMessage.success('用户已禁用')
    disableDialogVisible.value = false
    fetchData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// 启用用户
async function handleEnable(user: User) {
  try {
    await ElMessageBox.confirm(
      `确认启用用户 ${user.username}？`,
      '确认操作',
      { type: 'warning' }
    )
    await adminStore.enableUser(user.id)
    ElMessage.success('用户已启用')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 重置密码
async function handleResetPassword(user: User) {
  try {
    await ElMessageBox.confirm(
      `确认重置用户 ${user.username} 的密码？重置链接将发送到用户邮箱。`,
      '确认操作',
      { type: 'warning' }
    )
    const result = await adminStore.adminResetPassword(user.id)
    ElMessage.success('密码重置链接已生成')
    if (result.token) {
      console.log('重置 Token:', result.token)
      ElMessageBox.alert(
        `开发环境：Token 已输出到控制台\nReset URL: /reset-password?token=${result.token}`,
        '密码重置'
      )
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 删除用户
async function handleDelete(user: User) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户 ${user.username}？此操作不可恢复！`,
      '确认删除',
      { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    await adminStore.deleteUser(user.id)
    ElMessage.success('用户已删除')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 修改角色
function handleUserCommand(command: string, user: User) {
  if (command === 'delete') {
    handleDelete(user)
  } else if (command === 'role') {
    roleForm.userId = user.id
    roleForm.currentRole = user.role
    roleForm.newRole = ''
    roleDialogVisible.value = true
  } else if (command === 'edit') {
    ElMessage.info('编辑功能待实现')
  }
}

async function confirmChangeRole() {
  if (!roleForm.newRole) {
    ElMessage.warning('请选择新角色')
    return
  }
  if (roleForm.newRole === roleForm.currentRole) {
    ElMessage.warning('新角色与当前角色相同')
    return
  }
  try {
    await adminStore.changeUserRole(roleForm.userId, roleForm.newRole)
    ElMessage.success('角色已修改')
    roleDialogVisible.value = false
    fetchData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// 格式化日期时间
function formatDateTime(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 获取角色标签
function getRoleLabel(role: string) {
  const labels: Record<string, string> = {
    SUPER_ADMIN: '超级管理员',
    ADMIN: '管理员',
    USER: '用户',
    GUEST: '访客',
  }
  return labels[role] || role
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.search-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* ============================================
   响应式设计 - 移动端
   ============================================ */
@media (max-width: 768px) {
  .user-management {
    padding: 12px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .card-header h2 {
    font-size: 16px;
  }

  .search-form {
    margin-bottom: 16px;
  }

  .search-form :deep(.el-form-item) {
    margin-bottom: 12px;
    margin-right: 0;
    width: 100%;
  }

  .search-form :deep(.el-form-item__content) {
    width: 100%;
  }

  .search-form :deep(.el-input),
  .search-form :deep(.el-select) {
    width: 100% !important;
  }

  .pagination {
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
