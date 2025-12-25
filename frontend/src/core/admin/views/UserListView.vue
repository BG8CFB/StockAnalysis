<template>
  <div class="user-list-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>用户管理</h3>
          <el-button
            type="primary"
            :icon="Plus"
            @click="showCreateDialog = true"
          >
            新建用户
          </el-button>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <el-form
        :inline="true"
        :model="queryParams"
        class="search-form"
      >
        <el-form-item label="搜索">
          <el-input
            v-model="queryParams.search"
            placeholder="邮箱或用户名"
            clearable
            style="width: 200px"
            @change="handleQuery"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="queryParams.role"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleQuery"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="超级管理员"
              value="SUPER_ADMIN"
            />
            <el-option
              label="管理员"
              value="ADMIN"
            />
            <el-option
              label="用户"
              value="USER"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="queryParams.is_active"
            placeholder="全部"
            clearable
            style="width: 100px"
            @change="handleQuery"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="激活"
              :value="true"
            />
            <el-option
              label="禁用"
              :value="false"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :icon="Search"
            @click="handleQuery"
          >
            查询
          </el-button>
          <el-button
            :icon="Refresh"
            @click="handleReset"
          >
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 用户列表 -->
      <el-table
        v-loading="loading"
        :data="userList"
        stripe
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column
          prop="email"
          label="邮箱"
          min-width="180"
        />
        <el-table-column
          prop="username"
          label="用户名"
          min-width="120"
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
              size="small"
            >
              超级管理员
            </el-tag>
            <el-tag
              v-else-if="row.role === 'ADMIN'"
              type="warning"
              size="small"
            >
              管理员
            </el-tag>
            <el-tag
              v-else
              type="info"
              size="small"
            >
              用户
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="is_active"
          label="状态"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.is_active ? 'success' : 'danger'"
              size="small"
            >
              {{ row.is_active ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          label="创建时间"
          width="160"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="last_login_at"
          label="最后登录"
          width="160"
        >
          <template #default="{ row }">
            {{ row.last_login_at ? formatDate(row.last_login_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-dropdown
              v-if="isSuperAdmin"
              @command="(cmd) => handleRoleCommand(cmd, row)"
            >
              <el-button
                link
                type="primary"
                size="small"
              >
                角色 <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="USER">
                    设为用户
                  </el-dropdown-item>
                  <el-dropdown-item command="ADMIN">
                    设为管理员
                  </el-dropdown-item>
                  <el-dropdown-item command="SUPER_ADMIN">
                    设为超级管理员
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-if="row.id !== currentUserId"
              link
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '激活' }}
            </el-button>
            <el-button
              v-if="row.id !== currentUserId"
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.limit"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @size-change="handleQuery"
        @current-change="handleQuery"
      />
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingUser ? '编辑用户' : '新建用户'"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="userForm"
        :rules="userFormRules"
        label-width="80px"
      >
        <el-form-item
          label="邮箱"
          prop="email"
        >
          <el-input
            v-model="userForm.email"
            :disabled="!!editingUser"
          />
        </el-form-item>
        <el-form-item
          label="用户名"
          prop="username"
        >
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item
          v-if="!editingUser"
          label="密码"
          prop="password"
        >
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item
          label="角色"
          prop="role"
        >
          <el-select
            v-model="userForm.role"
            style="width: 100%"
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
              v-if="isSuperAdmin"
              label="超级管理员"
              value="SUPER_ADMIN"
            />
          </el-select>
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
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Search, Refresh, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'
import { adminApi, type UserListResponse } from '../api'
import dayjs from 'dayjs'

const userStore = useUserStore()

// 计算属性
const isSuperAdmin = computed(() => userStore.userInfo?.role === 'SUPER_ADMIN')
const isAdmin = computed(() => userStore.userInfo?.role === 'ADMIN' || isSuperAdmin.value)
const currentUserId = computed(() => userStore.userInfo?.id ?? '')

// 状态
const loading = ref(false)
const userList = ref<UserListResponse[]>([])
const total = ref(0)
const showCreateDialog = ref(false)
const editingUser = ref<UserListResponse | null>(null)
const submitting = ref(false)

// 查询参数
const queryParams = ref({
  page: 1,
  limit: 20,
  search: '',
  role: '',
  is_active: '',
})

// 用户表单
const userForm = ref({
  email: '',
  username: '',
  password: '',
  role: 'USER',
})

const formRef = ref<FormInstance>()

const userFormRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}

// 格式化日期
function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

// 查询用户列表
async function fetchUsers() {
  if (!isAdmin.value) return

  loading.value = true
  try {
    const response: any = await adminApi.getUsers({
      skip: (queryParams.value.page - 1) * queryParams.value.limit,
      limit: queryParams.value.limit,
      search: queryParams.value.search || undefined,
      role: queryParams.value.role || undefined,
      is_active: queryParams.value.is_active === '' ? undefined : queryParams.value.is_active === 'true',
    })
    userList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

// 查询
function handleQuery() {
  queryParams.value.page = 1
  fetchUsers()
}

// 重置
function handleReset() {
  queryParams.value = {
    page: 1,
    limit: 20,
    search: '',
    role: '',
    is_active: '',
  }
  fetchUsers()
}

// 编辑
function handleEdit(user: UserListResponse) {
  editingUser.value = user
  userForm.value = {
    email: user.email,
    username: user.username,
    password: '',
    role: user.role,
  }
  showCreateDialog.value = true
}

// 修改角色
async function handleRoleCommand(command: string, user: UserListResponse) {
  try {
    await ElMessageBox.confirm(
      `确定要将用户 ${user.username} 的角色修改为 ${getRoleLabel(command)} 吗？`,
      '确认修改',
      { type: 'warning' }
    )
    await adminApi.changeUserRole(user.id, command)
    ElMessage.success('角色修改成功')
    fetchUsers()
  } catch {
    // 用户取消或操作失败
  }
}

// 切换状态
async function handleToggleStatus(user: UserListResponse) {
  const action = user.is_active ? '禁用' : '激活'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户 ${user.username} 吗？`,
      `确认${action}`,
      { type: 'warning' }
    )
    await adminApi.updateUser(user.id, { is_active: !user.is_active })
    ElMessage.success(`${action}成功`)
    fetchUsers()
  } catch {
    // 用户取消或操作失败
  }
}

// 删除
async function handleDelete(user: UserListResponse) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 ${user.username} 吗？此操作不可恢复！`,
      '确认删除',
      { type: 'error', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await adminApi.deleteUser(user.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch {
    // 用户取消或操作失败
  }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (editingUser.value) {
        // 编辑
        await adminApi.updateUser(editingUser.value.id, {
          email: userForm.value.email,
          username: userForm.value.username,
        })
        ElMessage.success('更新成功')
      } else {
        // 新建
        await adminApi.createUser({
          email: userForm.value.email,
          username: userForm.value.username,
          password: userForm.value.password,
          role: userForm.value.role as any,
        })
        ElMessage.success('创建成功')
      }
      showCreateDialog.value = false
      fetchUsers()
    } catch (error) {
      // 错误已在 http 拦截器中处理
    } finally {
      submitting.value = false
    }
  })
}

function getRoleLabel(role: string) {
  const labels: Record<string, string> = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '管理员',
    'USER': '用户',
  }
  return labels[role] || role
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-list-view {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.search-form {
  margin-bottom: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .search-form {
    display: block;
  }

  .search-form :deep(.el-form-item) {
    margin-right: 0;
    margin-bottom: 12px;
    width: 100%;
  }

  .search-form :deep(.el-input),
  .search-form :deep(.el-select) {
    width: 100% !important;
  }

  :deep(.el-table) {
    font-size: 13px;
  }

  :deep(.el-pagination) {
    justify-content: center !important;
  }

  :deep(.el-pagination__sizes),
  :deep(.el-pagination__jump) {
    display: none;
  }
}
</style>
