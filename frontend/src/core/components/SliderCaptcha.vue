<!--
滑动拼图验证码组件
简化版实现，适合项目使用
-->
<template>
  <div class="slider-captcha">
    <div
      v-if="token"
      class="captcha-container"
    >
      <div class="captcha-canvas-wrapper">
        <canvas
          ref="canvasRef"
          :width="canvasWidth"
          :height="canvasHeight"
          class="captcha-canvas"
        />
        <canvas
          ref="blockRef"
          :width="canvasWidth"
          :height="canvasHeight"
          class="captcha-block"
        />
      </div>

      <div class="slider-control">
        <div
          ref="trackRef"
          class="slider-track"
        >
          <div
            ref="buttonRef"
            class="slider-button"
            :class="{ dragging: isDragging }"
            :style="{ left: sliderLeft + 'px' }"
            @mousedown="startDrag"
            @touchstart="startDrag"
          >
            <el-icon :size="20">
              <component :is="isDragging ? 'ArrowRight' : 'ArrowDoubleRight'" />
            </el-icon>
          </div>
          <div
            v-if="!isDragging && !isVerified"
            class="slider-text"
          >
            向右滑动完成验证
          </div>
          <div
            v-else-if="isVerified"
            class="slider-text success"
          >
            <el-icon color="#67c23a">
              <Check />
            </el-icon>
            验证成功
          </div>
          <div
            v-else-if="hasError"
            class="slider-text error"
          >
            <el-icon color="#f56c6c">
              <Close />
            </el-icon>
            验证失败，请重试
          </div>
        </div>
      </div>

      <div class="captcha-footer">
        <el-button
          link
          type="primary"
          size="small"
          :loading="loading"
          @click="refreshCaptcha"
        >
          <el-icon><Refresh /></el-icon>
          换一张
        </el-button>
      </div>
    </div>

    <el-button
      v-else
      :loading="loading"
      @click="initCaptcha"
    >
      点击加载验证码
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, ArrowDoubleRight, Check, Close, Refresh } from '@element-plus/icons-vue'
import { httpPost, httpGet } from '@core/api/http'

interface CaptchaData {
  token: string
  puzzle_position: { x: number; y: number }
}

interface Emits {
  (e: 'success', data: { token: string; slideX: number; slideY: number }): void
  (e: 'error'): void
}

const props = defineProps<{
  action?: 'login' | 'register' | 'reset_password'
}>()

const emit = defineEmits<Emits>()

// 状态
const loading = ref(false)
const token = ref<string>('')
const puzzlePosition = ref<{ x: number; y: number }>({ x: 0, y: 0 })
const isDragging = ref(false)
const isVerified = ref(false)
const hasError = ref(false)
const sliderLeft = ref(0)

// Canvas 配置
const canvasWidth = 300
const canvasHeight = 150

// Refs
const canvasRef = ref<HTMLCanvasElement>()
const blockRef = ref<HTMLCanvasElement>()
const buttonRef = ref<HTMLDivElement>()
const trackRef = ref<HTMLDivElement>()

// 拖动相关
let startX = 0
let currentX = 0
const trackWidth = 300
const maxOffset = 250

// 初始化验证码
const initCaptcha = async () => {
  loading.value = true
  hasError.value = false
  isVerified.value = false
  sliderLeft.value = 0

  try {
    const res = await httpGet<{ token: string; puzzle_position: { x: number; y: number } }>(
      `/users/captcha/generate?action=${props.action || 'login'}`
    )
    token.value = res.token
    puzzlePosition.value = res.puzzle_position

    await nextTick()
    drawCaptcha()
  } catch (error: any) {
    ElMessage.error(error.message || '加载验证码失败')
  } finally {
    loading.value = false
  }
}

// 刷新验证码
const refreshCaptcha = () => {
  initCaptcha()
}

// 绘制验证码
const drawCaptcha = () => {
  const canvas = canvasRef.value
  const block = blockRef.value
  if (!canvas || !block) return

  const ctx = canvas.getContext('2d')
  const blockCtx = block.getContext('2d')
  if (!ctx || !blockCtx) return

  // 清空画布
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)
  blockCtx.clearRect(0, 0, canvasWidth, canvasHeight)

  // 绘制背景（使用渐变色）
  const gradient = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight)
  gradient.addColorStop(0, '#667eea')
  gradient.addColorStop(1, '#764ba2')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  // 添加一些装饰图案
  ctx.fillStyle = 'rgba(255, 255, 255, 0.1)'
  for (let i = 0; i < 5; i++) {
    const x = Math.random() * canvasWidth
    const y = Math.random() * canvasHeight
    const radius = Math.random() * 30 + 10
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
  }

  // 绘制拼图缺口（目标位置）
  const { x: puzzleX, y: puzzleY } = puzzlePosition.value
  const blockSize = 50

  // 绘制缺口
  ctx.fillStyle = 'rgba(0, 0, 0, 0.3)'
  ctx.beginPath()
  ctx.roundRect(puzzleX, puzzleY, blockSize, blockSize, 5)
  ctx.fill()

  // 在 block canvas 上绘制拼图块
  blockCtx.fillStyle = '#f0f0f0'
  blockCtx.strokeStyle = '#409eff'
  blockCtx.lineWidth = 2
  blockCtx.beginPath()
  blockCtx.roundRect(0, puzzleY, blockSize, blockSize, 5)
  blockCtx.fill()
  blockCtx.stroke()

  // 添加拼图块纹理
  blockCtx.fillStyle = '#409eff'
  blockCtx.font = '20px Arial'
  blockCtx.fillText('◆', blockSize / 2 - 10, puzzleY + blockSize / 2 + 7)
}

// 开始拖动
const startDrag = (e: MouseEvent | TouchEvent) => {
  if (isVerified.value) return

  isDragging.value = true
  hasError.value = false

  if (e instanceof MouseEvent) {
    startX = e.clientX
  } else {
    startX = e.touches[0].clientX
  }

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

// 拖动中
const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return

  let clientX: number
  if (e instanceof MouseEvent) {
    clientX = e.clientX
  } else {
    clientX = e.touches[0].clientX
  }

  currentX = clientX - startX
  currentX = Math.max(0, Math.min(currentX, maxOffset))
  sliderLeft.value = currentX

  // 更新拼图块位置
  const block = blockRef.value
  if (block) {
    block.style.transform = `translateX(${currentX}px)`
  }
}

// 停止拖动
const stopDrag = () => {
  if (!isDragging.value) return

  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)

  // 验证
  verifyCaptcha()
}

// 验证
const verifyCaptcha = () => {
  const targetX = puzzlePosition.value.x
  const tolerance = 5 // 允许误差

  if (Math.abs(currentX - targetX) <= tolerance) {
    isVerified.value = true
    hasError.value = false

    // 发送成功事件
    emit('success', {
      token: token.value,
      slideX: currentX,
      slideY: puzzlePosition.value.y,
    })
  } else {
    hasError.value = true
    emit('error')

    // 重置
    setTimeout(() => {
      sliderLeft.value = 0
      const block = blockRef.value
      if (block) {
        block.style.transform = 'translateX(0)'
      }
      hasError.value = false
    }, 1000)
  }
}

// 暴露方法
defineExpose({
  initCaptcha,
  refreshCaptcha,
})

onMounted(() => {
  initCaptcha()
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
})
</script>

<style scoped>
.slider-captcha {
  width: 100%;
  max-width: 350px;
  margin: 0 auto;
}

.captcha-container {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.captcha-canvas-wrapper {
  position: relative;
  width: 300px;
  height: 150px;
  margin: 0 auto;
  border-radius: 4px;
  overflow: hidden;
}

.captcha-canvas,
.captcha-block {
  position: absolute;
  top: 0;
  left: 0;
}

.captcha-block {
  cursor: pointer;
  transition: transform 0.1s;
}

.slider-control {
  margin-top: 16px;
}

.slider-track {
  position: relative;
  width: 100%;
  height: 40px;
  background: #e8e8e8;
  border-radius: 20px;
  overflow: hidden;
}

.slider-button {
  position: absolute;
  left: 0;
  top: 0;
  width: 40px;
  height: 40px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: background 0.3s;
  user-select: none;
}

.slider-button:hover {
  background: #66b1ff;
}

.slider-button.dragging {
  background: #3a8ee6;
}

.slider-text {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
  pointer-events: none;
}

.slider-text.success {
  color: #67c23a;
}

.slider-text.error {
  color: #f56c6c;
}

.captcha-footer {
  margin-top: 12px;
  text-align: center;
}
</style>
