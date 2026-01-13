<template>
  <div class="login-container">
    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-blob blob-1" />
      <div class="decoration-blob blob-2" />
      <div class="decoration-blob blob-3" />
    </div>

    <!-- 左侧内容区 -->
    <div class="login-content">
      <div class="brand-section">
        <div class="brand-icon">
          <el-icon :size="48">
            <TrendCharts />
          </el-icon>
        </div>
        <h1 class="brand-title">
          股票分析平台
        </h1>
        <p class="brand-subtitle">
          专业 AI 驱动的智能投资决策系统
        </p>
        <div class="brand-features">
          <div class="feature-item">
            <el-icon><Check /></el-icon>
            <span>AI 智能分析</span>
          </div>
          <div class="feature-item">
            <el-icon><Check /></el-icon>
            <span>多维度数据</span>
          </div>
          <div class="feature-item">
            <el-icon><Check /></el-icon>
            <span>实时行情</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="login-form-section">
      <div class="login-box">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录您的账户继续使用</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          @submit.prevent
        >
          <el-form-item
            label="账号"
            prop="account"
          >
            <el-input
              v-model="form.account"
              placeholder="请输入用户名或邮箱"
              :prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item
            label="密码"
            prop="password"
          >
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter.prevent="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="submit-button"
              @click="handleLogin"
            >
              <template v-if="!loading">
                <span>登录账户</span>
                <el-icon class="button-icon">
                  <ArrowRight />
                </el-icon>
              </template>
              <template v-else>
                登录中...
              </template>
            </el-button>
          </el-form-item>

          <div class="form-footer">
            <span class="footer-text">还没有账号？</span>
            <el-link
              type="primary"
              @click="goRegister"
            >
              立即注册
            </el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Message, Lock, TrendCharts, Check, ArrowRight } from '@element-plus/icons-vue'
import { useUserStore } from '../store'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

onMounted(() => {
  console.log('[LoginView] Mounted', {
    isLoggedIn: userStore.isLoggedIn,
    hasToken: !!localStorage.getItem('access_token')
  })
})

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
})

const rules: FormRules = {
  account: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
    { min: 2, message: '用户名或邮箱长度至少2位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  console.log('[LoginView] handleLogin triggered')
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) {
      console.log('[LoginView] Validation failed')
      return
    }

    loading.value = true
    try {
      const success = await userStore.login(
        form.account,
        form.password
      )
      if (success) {
        ElMessage.success('登录成功')
        const redirect = (route.query.redirect as string) || '/dashboard'
        console.log('[LoginView] Login success, redirecting to:', redirect)
        await router.push(redirect)
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || '登录失败，请检查用户名和密码'
      ElMessage.error(errorMessage)
    } finally {
      loading.value = false
    }
  })
}

function goRegister() {
  router.push('/register')
}
</script>

<style scoped>
/* ===========================================
   登录容器 Login Container
   =========================================== */

.login-container {
  display: flex;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

/* ===========================================
   背景装饰 Background Decoration
   =========================================== */

.background-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  z-index: 0;
}

.decoration-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.6;
  animation: float 20s ease-in-out infinite;
}

.blob-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.4) 0%, rgba(118, 75, 162, 0.4) 100%);
  top: -200px;
  left: -200px;
  animation-delay: 0s;
}

.blob-2 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.3) 0%, rgba(0, 242, 254, 0.3) 100%);
  bottom: -150px;
  right: -150px;
  animation-delay: 7s;
}

.blob-3 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, rgba(67, 233, 123, 0.2) 0%, rgba(56, 249, 215, 0.2) 100%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: 14s;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -50px) scale(1.1);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.9);
  }
}

/* ===========================================
   左侧内容区 Left Content Section
   =========================================== */

.login-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  position: relative;
  z-index: 1;
}

.brand-section {
  max-width: 480px;
}

.brand-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-xl);
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: var(--space-6);
  box-shadow: var(--shadow-primary);
}

.brand-title {
  font-size: 48px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3) 0;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-8) 0;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.feature-item .el-icon {
  color: var(--color-success);
  font-size: 20px;
}

/* ===========================================
   右侧表单区 Right Form Section
   =========================================== */

.login-form-section {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  position: relative;
  z-index: 1;
}

.login-box {
  width: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: var(--radius-xxl);
  padding: var(--space-10);
  box-shadow: var(--shadow-xl);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.form-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.form-header h2 {
  font-size: var(--font-size-xxxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
}

.form-header p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* ===========================================
   表单样式 Form Styles
   =========================================== */

:deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.submit-button {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-primary);
}

.button-icon {
  margin-left: var(--space-2);
  transition: transform var(--duration-base) var(--ease-out-cubic);
}

.submit-button:hover .button-icon {
  transform: translateX(4px);
}

.form-footer {
  text-align: center;
  padding-top: var(--space-4);
}

.footer-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* ===========================================
   响应式 Responsive
   =========================================== */

@media (max-width: 1024px) {
  .login-content {
    display: none;
  }

  .login-form-section {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .login-form-section {
    padding: var(--space-6);
  }

  .login-box {
    padding: var(--space-6);
  }

  .brand-title {
    font-size: 32px;
  }

  .form-header h2 {
    font-size: var(--font-size-xl);
  }
}
</style>
