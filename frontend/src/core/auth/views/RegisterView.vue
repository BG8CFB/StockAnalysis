<template>
  <div class="register-container">
    <div class="register-box">
      <div class="logo">
        <h1>注册账号</h1>
        <p>创建您的股票分析账户</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
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
          label="密码"
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
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <!-- 滑动验证码（注册始终需要） -->
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
            style="width: 100%"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>

        <div class="footer">
          <span>已有账号？</span>
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
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Message, Lock, User } from '@element-plus/icons-vue'
import { useUserStore } from '../store'
import SliderCaptcha from '@core/components/SliderCaptcha.vue'
import type { CaptchaData } from '../api'

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

  // 清除验证错误
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

    // 检查验证码
    if (!captchaData.value) {
      ElMessage.warning('请完成验证码验证')
      return
    }

    loading.value = true
    try {
      const success = await userStore.register(
        form.email,
        form.username,
        form.password,
        form.confirm_password,
        form.captcha_token,
        form.slide_x,
        form.slide_y
      )
      if (success) {
        ElMessage.success('注册成功')
        // 注册成功后跳转到仪表板
        await router.push('/dashboard')
      }
    } catch (error: any) {
      // 注册失败，刷新验证码
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
.register-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-box {
  width: 90%;
  max-width: 400px;
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

.error-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #f56c6c;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .register-box {
    width: 95%;
    padding: 24px;
  }

  .logo h1 {
    font-size: 24px;
  }
}
</style>
