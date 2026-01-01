<template>
  <div class="register-container">
    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-blob blob-1" />
      <div class="decoration-blob blob-2" />
      <div class="decoration-blob blob-3" />
    </div>

    <!-- 左侧内容区 -->
    <div class="register-content">
      <div class="brand-section">
        <div class="brand-icon">
          <el-icon :size="48">
            <UserFilled />
          </el-icon>
        </div>
        <h1 class="brand-title">
          加入我们
        </h1>
        <p class="brand-subtitle">
          开启您的智能投资之旅
        </p>
        <div class="brand-benefits">
          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="benefit-content">
              <h3>AI 驱动</h3>
              <p>先进的智能分析算法</p>
            </div>
          </div>
          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="benefit-content">
              <h3>实时数据</h3>
              <p>全面的行情数据支持</p>
            </div>
          </div>
          <div class="benefit-card">
            <div class="benefit-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <div class="benefit-content">
              <h3>安全可靠</h3>
              <p>企业级数据安全保障</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="register-form-section">
      <div class="register-box">
        <div class="form-header">
          <h2>创建账户</h2>
          <p>填写信息开始您的投资之旅</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
        >
          <el-form-item
            label="邮箱地址"
            prop="email"
          >
            <el-input
              v-model="form.email"
              type="email"
              placeholder="your@email.com"
              :prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item
            label="显示名称"
            prop="username"
          >
            <el-input
              v-model="form.username"
              placeholder="请输入显示名称"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item
            label="密码"
            prop="password"
          >
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少8位字符"
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
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <!-- 滑动验证码 -->
          <el-form-item prop="captcha">
            <SliderCaptcha
              ref="captchaRef"
              action="register"
              @success="onCaptchaSuccess"
              @error="onCaptchaError"
            />
            <div
              v-if="captchaError"
              class="error-tip"
            >
              {{ captchaError }}
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!captchaData"
              class="submit-button"
              @click="handleRegister"
            >
              <template v-if="!loading">
                <span>创建账户</span>
                <el-icon class="button-icon">
                  <ArrowRight />
                </el-icon>
              </template>
              <template v-else>
                注册中...
              </template>
            </el-button>
          </el-form-item>

          <div class="form-footer">
            <span class="footer-text">已有账号？</span>
            <el-link
              type="primary"
              @click="goLogin"
            >
              立即登录
            </el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import {
  Message,
  Lock,
  User,
  UserFilled,
  ArrowRight,
  DataAnalysis,
  TrendCharts
} from '@element-plus/icons-vue'
import { useUserStore } from '../store'
import SliderCaptcha, { type CaptchaData } from '@core/components/SliderCaptcha.vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const captchaRef = ref()
const loading = ref(false)
const captchaData = ref<CaptchaData | null>(null)
const captchaError = ref('')

const form = reactive({
  email: '',
  username: '',
  password: '',
  confirm_password: '',
  captcha_token: '',
  slide_x: 0,
  slide_y: 0,
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
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_]+$/,
      message: '只能包含字母、数字和下划线',
      trigger: 'blur'
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
  captcha: [
    {
      validator: (_rule, _value, callback) => {
        if (!captchaData.value) {
          callback(new Error('请完成验证码验证'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
}

// 验证码成功回调
function onCaptchaSuccess(data: CaptchaData) {
  captchaData.value = data
  captchaError.value = ''
  form.captcha_token = data.token
  form.slide_x = data.slideX
  form.slide_y = data.slideY

  if (formRef.value) {
    formRef.value.clearValidate('captcha')
  }
}

// 验证码失败回调
function onCaptchaError() {
  captchaData.value = null
  form.captcha_token = ''
  form.slide_x = 0
  form.slide_y = 0
  captchaError.value = '验证失败，请重试'
}

async function handleRegister() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    if (!captchaData.value) {
      ElMessage.warning('请完成验证码验证')
      return
    }

    loading.value = true
    try {
      const result = await userStore.register(
        form.email,
        form.username,
        form.password,
        form.confirm_password,
        form.captcha_token,
        form.slide_x,
        form.slide_y
      )

      // 处理注册结果
      if (result === true) {
        // 注册成功并自动登录
        ElMessage.success('注册成功')
        await router.push('/dashboard')
      } else if (result?.needsApproval) {
        // 注册成功但需要审核
        ElMessage.success('注册成功，请等待管理员审核')
        await router.push('/login')
      }
    } catch (error: any) {
      if (captchaRef.value) {
        captchaRef.value.refreshCaptcha()
      }
      captchaData.value = null
      form.captcha_token = ''
      form.slide_x = 0
      form.slide_y = 0
    } finally {
      loading.value = false
    }
  })
}

function goLogin() {
  router.push('/login')
}
</script>

<style scoped>
/* ===========================================
   注册容器 Register Container
   =========================================== */

.register-container {
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
  background: linear-gradient(135deg, rgba(67, 233, 123, 0.4) 0%, rgba(56, 249, 215, 0.4) 100%);
  top: -200px;
  left: -200px;
  animation-delay: 0s;
}

.blob-2 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
  bottom: -150px;
  right: -150px;
  animation-delay: 7s;
}

.blob-3 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, rgba(250, 173, 20, 0.2) 0%, rgba(245, 34, 45, 0.2) 100%);
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

.register-content {
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
  background: var(--gradient-success);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: var(--space-6);
  box-shadow: var(--shadow-success);
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

.brand-benefits {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.benefit-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all var(--duration-base) var(--ease-out-cubic);
}

.benefit-card:hover {
  transform: translateX(8px);
  box-shadow: var(--shadow-base);
}

.benefit-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-base);
  background: var(--color-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}

.benefit-content h3 {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 2px 0;
}

.benefit-content p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

/* ===========================================
   右侧表单区 Right Form Section
   =========================================== */

.register-form-section {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  position: relative;
  z-index: 1;
}

.register-box {
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

.error-tip {
  margin-top: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-danger);
}

.submit-button {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-success);
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
  .register-content {
    display: none;
  }

  .register-form-section {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .register-form-section {
    padding: var(--space-6);
  }

  .register-box {
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
