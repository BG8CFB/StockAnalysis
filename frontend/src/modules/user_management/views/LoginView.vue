<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>TradingAgents-CN</h1>
        <p>股票分析智能体系统</p>
      </div>

      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        size="large"
        class="login-form"
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

        <n-form-item>
          <div class="login-actions">
            <n-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              block
            >
              登录
            </n-button>
          </div>
        </n-form-item>

        <div class="login-footer">
          <span>还没有账户？</span>
          <n-button text type="primary" @click="$router.push('/register')">
            立即注册
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
import { MailOutlined, LockOutlined } from '@vicons/ionicons5'
import { useUserStore } from '../store'

const router = useRouter()
const userStore = useUserStore()

// 表单引用
const formRef = ref<FormInst | null>(null)

// 表单数据
const formData = reactive({
  email: '',
  password: ''
})

// 表单验证规则
const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 计算属性
const loading = computed(() => userStore.loading)

// 登录处理
async function handleLogin() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    const result = await userStore.login({
      email: formData.email,
      password: formData.password
    })

    if (result.success) {
      router.push('/dashboard')
    }
  } catch (error) {
    console.error('Login validation failed:', error)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.login-header p {
  color: #666;
  font-size: 14px;
}

.login-form {
  width: 100%;
}

.login-actions {
  width: 100%;
  margin-top: 20px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  color: #666;
  font-size: 14px;
}

.login-footer a {
  margin-left: 8px;
}
</style>