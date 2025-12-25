<template>
  <div class="login-container">
    <div class="login-box">
      <div class="logo">
        <h1>股票分析平台</h1>
        <p>专业的股票数据分析工具</p>
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
          label="邮箱"
          prop="email"
        >
          <el-input
            v-model="form.email"
            type="email"
            placeholder="请输入邮箱"
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

        <!-- 滑动验证码 -->
        <el-form-item v-if="showCaptcha">
          <SliderCaptcha
            ref="captchaRef"
            action="login"
            @success="onCaptchaSuccess"
            @error="onCaptchaError"
          />
        </el-form-item>

        <!-- 验证码提示信息 -->
        <el-alert
          v-if="captchaReason"
          :title="captchaReason"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>

        <div class="footer">
          <span>还没有账号？</span>
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
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../store'
import SliderCaptcha from '@core/components/SliderCaptcha.vue'
import { type CaptchaData } from '../api'

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
const captchaRef = ref()
const loading = ref(false)
const showCaptcha = ref(false)
const captchaReason = ref('')
const captchaData = ref<CaptchaData | null>(null)

const form = reactive({
  email: '',
  password: '',
  captcha_token: '',
  slide_x: 0,
  slide_y: 0,
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
  ],
}

// 验证码成功回调
function onCaptchaSuccess(data: CaptchaData) {
  captchaData.value = data
  form.captcha_token = data.token
  form.slide_x = data.slideX
  form.slide_y = data.slideY
}

// 验证码失败回调
function onCaptchaError() {
  captchaData.value = null
  form.captcha_token = ''
  form.slide_x = 0
  form.slide_y = 0
  // 刷新验证码
  if (captchaRef.value) {
    captchaRef.value.refreshCaptcha()
  }
}

async function handleLogin() {
  console.log('[LoginView] handleLogin triggered')
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) {
      console.log('[LoginView] Validation failed')
      return
    }

    // 检查验证码
    if (showCaptcha.value && !captchaData.value) {
      ElMessage.warning('请完成验证码验证')
      return
    }

    loading.value = true
    try {
      const success = await userStore.login(
        form.email,
        form.password,
        form.captcha_token || undefined,
        form.slide_x || undefined,
        form.slide_y || undefined
      )
      if (success) {
        ElMessage.success('登录成功')
        // 跳转到原目标页面或仪表板
        const redirect = (route.query.redirect as string) || '/dashboard'
        console.log('[LoginView] Login success, redirecting to:', redirect)
        await router.push(redirect)
      }
    } catch (error: any) {
      // 检查是否需要验证码
      if (error.response?.headers?.['x-captcha-required'] || error.response?.status === 400 && error.response?.data?.detail === "请完成图形验证码") {
        showCaptcha.value = true
        captchaReason.value = "为了您的账号安全，请完成验证"
        ElMessage.warning('请完成图形验证码')
        
        // 刷新验证码组件（如果已存在）
        if (captchaRef.value) {
           captchaRef.value.refreshCaptcha()
        }
      } else {
        // 显示普通错误消息
        const errorMessage = error?.response?.data?.detail || error?.message || '登录失败，请检查用户名和密码'
        ElMessage.error(errorMessage)
      }

      // 登录失败，刷新验证码
      if (showCaptcha.value && captchaRef.value) {
        captchaRef.value.refreshCaptcha()
        captchaData.value = null
        form.captcha_token = ''
        form.slide_x = 0
        form.slide_y = 0
      }
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
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 32px;
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

.footer {
  text-align: center;
  font-size: 14px;
  color: #606266;
}

.footer .el-link {
  margin-left: 4px;
}
</style>
