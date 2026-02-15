<template>
  <router-view />
</template>

<script setup lang="ts">
import { useUserStore } from '@core/auth/store'

const userStore = useUserStore()

// 应用启动时，如果有 token，自动加载用户信息
// 不阻塞页面渲染，用户可以立即看到页面
if (userStore.isLoggedIn) {
  userStore.ensureUserInfoLoaded().catch((error) => {
    console.error('[App] Failed to load user info on startup:', error)
  })
}
</script>

<style>
/* 全局样式在 main.css 中定义 */
</style>
