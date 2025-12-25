<template>
  <div class="init-container">
    <div class="init-box">
      <div class="logo">
        <h1>股票分析平台</h1>
        <p>系统初始化设置</p>
      </div>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 24px"
      >
        <template #title>
          首次启动需要创建超级管理员账户
        </template>
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
      >
        <el-form-item
          label="管理员邮箱"
          prop="email"
        >
          <el-input
            v-model="form.email"
            type="email"
            placeholder="请输入管理员邮箱"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item
          label="显示名称"
          prop="username"
        >
          <el-input
            v-model="form.username"
            placeholder="请输入显示名称（2-50字符）"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item
          label="管理员密码"
          prop="password"
        >
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（至少8位）"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item
          label="确认密码"
          prop="confirm_password"
        >
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleInitialize"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="handleInitialize"
          >
            创建管理员账户
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Message, Lock, User } from '@element-plus/icons-vue'
import { useSystemStore } from '../store'
import { useUserStore } from '@core/auth/store'

const router = useRouter()
const systemStore = useSystemStore()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  email: '',
  username: '',
  password: '',
  confirm_password: '',
})

const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  username: [
    { required: true, message: '请输入显示名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

async function handleInitialize() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const response = await systemStore.initialize({
        email: form.email,
        username: form.username,
        password: form.password,
        confirm_password: form.confirm_password,
      })

      // 保存 token 和用户信息
      userStore.token = response.access_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      // 获取用户信息
      await userStore.fetchUserInfo()

      ElMessage.success('系统初始化成功')
      await router.push('/dashboard')
    } catch (error: any) {
      // 错误已在 http 拦截器中处理
      if (error.response?.data?.detail) {
        ElMessage.error(error.response.data.detail)
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.init-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.init-box {
  width: 90%;
  max-width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 24px;
}

.logo h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
}

.logo p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .init-box {
    width: 95%;
    padding: 24px;
  }

  .logo h1 {
    font-size: 24px;
  }
}
</style>
