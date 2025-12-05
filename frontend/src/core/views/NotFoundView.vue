<template>
  <div class="not-found">
    <div class="content">
      <h1>404</h1>
      <h2>页面未找到</h2>
      <p>抱歉，您访问的页面不存在。</p>
      <n-button @click="goHome" type="primary">
        返回首页
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  text-align: center;
}

.content h1 {
  font-size: 6rem;
  color: #d03050;
  margin-bottom: 1rem;
}

.content h2 {
  font-size: 2rem;
  color: #666;
  margin-bottom: 1rem;
}

.content p {
  color: #999;
  margin-bottom: 2rem;
}
</style>