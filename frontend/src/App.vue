<template>
  <div id="app">
    <router-view />

    <!-- 全局加载状态 -->
    <div v-if="eventState.loadingCount > 0" class="global-loading">
      <n-spin size="large" />
    </div>

    <!-- 全局通知 -->
    <div class="global-notifications">
      <n-notification
        v-for="notification in eventState.notifications"
        :key="notification.id"
        :type="notification.type"
        :title="notification.title"
        :duration="notification.duration || 4000"
        @close="removeNotification(notification.id)"
      >
        {{ notification.message }}
      </n-notification>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { NSpin, NNotification } from 'naive-ui'
import { eventState, eventBus, EventTypes } from '@/core/events/bus'

onMounted(() => {
  // 监听通知事件
  eventBus.on(EventTypes.NOTIFICATION_SHOW, (event) => {
    const { type, title, message, duration } = event.data
    addNotification({
      id: Date.now().toString(),
      type: type || 'info',
      title,
      message,
      duration
    })
  })

  // 监听通知隐藏事件
  eventBus.on(EventTypes.NOTIFICATION_HIDE, (event) => {
    const { id } = event.data
    if (id) {
      removeNotification(id)
    } else {
      // 如果没有指定ID，清除所有通知
      eventState.notifications.length = 0
    }
  })
})

function addNotification(notification: any) {
  eventState.notifications.push(notification)
}

function removeNotification(id: string) {
  const index = eventState.notifications.findIndex(n => n.id === id)
  if (index > -1) {
    eventState.notifications.splice(index, 1)
  }
}
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
}

.global-loading {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 20px;
  border-radius: 8px;
}

.global-notifications {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9998;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>