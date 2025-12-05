<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>注册账户</h1>
        <p>加入 TradingAgents-CN</p>
      </div>

      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        size="large"
        class="register-form"
      >
        <n-form-item path="email" label="邮箱">
          <n-input
            v-model:value="formData.email"
            placeholder="请输入邮箱"
            type="email"
            :disabled="loading"
          >
            <template #prefix>
              <n-icon><MailOutlined /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="username" label="用户名">
          <n-input
            v-model:value="formData.username"
            placeholder="请输入用户名"
            :disabled="loading"
          >
            <template #prefix>
              <n-icon><PersonOutlined /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="full_name" label="姓名（可选）">
          <n-input
            v-model:value="formData.full_name"
            placeholder="请输入真实姓名"
            :disabled="loading"
          >
            <template #prefix>
              <n-icon><UserOutlined /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="formData.password"
            placeholder="请输入密码"
            type="password"
            show-password-on="click"
            :disabled="loading"
          >
            <template #prefix>
              <n-icon><LockOutlined /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="confirmPassword" label="确认密码">
          <n-input
            v-model:value="formData.confirmPassword"
            placeholder="请再次输入密码"
            type="password"
            show-password-on="click"
            :disabled="loading"
          >
            <template #prefix>
              <n-icon><LockOutlined /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item>
          <div class="register-actions">
            <n-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleRegister"
              block
            >
              注册
            </n-button>
          </div>
        </n-form-item>

        <div class="register-footer">
          <span>已有账户？</span>
          <n-button text type="primary" @click="$router.push('/login')">
            立即登录
          </n-button>
        </div>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import {
  NForm,
  NFormItem,
  NInput,
  NButton,
  NIcon,
  type FormInst,
  type FormRules
} from 'naive-ui'
import {
  MailOutlined,
  PersonOutlined,
  UserOutlined,
  LockOutlined
} from '@vicons/ionicons5'
import { useUserStore } from '../store'

const router = useRouter()
const userStore = useUserStore()

// 表单引用
const formRef = ref<FormInst | null>(null)

// 表单数据
const formData = reactive({
  email: '',
  username: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

// 密码验证函数
const validatePasswordStartWith = (rule: any, value: string) => {
  return !!formData.password && formData.password.startsWith(value) || value === ''
}

const validatePasswordSame = (rule: any, value: string) => {
  return value === formData.password
}

// 表单验证规则
const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在3-50个字符之间', trigger: 'blur' }
  ],
  full_name: [
    { max: 100, message: '姓名长度不能超过100个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: validatePasswordStartWith,
      message: '两次密码输入不一致',
      trigger: 'input'
    },
    {
      validator: validatePasswordSame,
      message: '两次密码输入不一致',
      trigger: ['blur', 'password-input']
    }
  ]
}

// 计算属性
const loading = computed(() => userStore.loading)

// 注册处理
async function handleRegister() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    const result = await userStore.register({
      email: formData.email,
      username: formData.username,
      full_name: formData.full_name,
      password: formData.password
    })

    if (result.success) {
      router.push('/login')
    }
  } catch (error) {
    console.error('Register validation failed:', error)
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.register-header {
  text-align: center;
  margin-bottom: 40px;
}

.register-header h1 {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.register-header p {
  color: #666;
  font-size: 14px;
}

.register-form {
  width: 100%;
}

.register-actions {
  width: 100%;
  margin-top: 20px;
}

.register-footer {
  text-align: center;
  margin-top: 20px;
  color: #666;
  font-size: 14px;
}

.register-footer a {
  margin-left: 8px;
}
</style>