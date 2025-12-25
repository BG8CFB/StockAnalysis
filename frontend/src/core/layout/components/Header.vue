<template>
  <el-header class="header">
    <div class="header-left">
      <!-- 移动端菜单按钮 -->
      <el-button
        class="mobile-menu-btn"
        text
        @click="$emit('toggle-sidebar')"
      >
        <el-icon :size="20">
          <Menu />
        </el-icon>
      </el-button>

      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">
          首页
        </el-breadcrumb-item>
        <el-breadcrumb-item v-if="currentRouteName">
          {{ currentRouteName }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="header-right">
      <!-- 角色标签 -->
      <el-tag
        v-if="userStore.userInfo"
        :type="roleType"
        size="small"
        class="role-tag"
      >
        {{ roleLabel }}
      </el-tag>

      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar
            :size="32"
            :icon="UserFilled"
          />
          <span class="username">{{ displayName }}</span>
          <el-icon class="arrow"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <div class="user-detail">
                <div class="user-email">
                  {{ userStore.userInfo?.email }}
                </div>
                <el-tag
                  :type="roleType"
                  size="small"
                >
                  {{ roleLabel }}
                </el-tag>
              </div>
            </el-dropdown-item>
            <el-dropdown-item
              divided
              command="settings"
            >
              <el-icon><Setting /></el-icon>
              设置
            </el-dropdown-item>
            <el-dropdown-item
              command="logout"
              style="color: #f56c6c"
            >
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Menu,
  UserFilled,
  Setting,
  SwitchButton,
  ArrowDown,
} from '@element-plus/icons-vue'
import { useUserStore } from '@core/auth/store'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
}>()

const currentRouteName = computed(() => route.meta.title as string)

const displayName = computed(() => {
  return userStore.userInfo?.username || userStore.email || '用户'
})

const roleLabel = computed(() => {
  const role = userStore.userInfo?.role
  const labels: Record<string, string> = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '管理员',
    'USER': '用户',
  }
  return labels[role || ''] || '访客'
})

const roleType = computed(() => {
  const role = userStore.userInfo?.role
  const types: Record<string, any> = {
    'SUPER_ADMIN': 'danger',
    'ADMIN': 'warning',
    'USER': 'info',
  }
  return types[role || ''] || 'info'
})

async function handleCommand(command: string) {
  switch (command) {
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.mobile-menu-btn {
  display: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.role-tag {
  display: none;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #606266;
}

.arrow {
  font-size: 12px;
  color: #909399;
}

.user-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 200px;
}

.user-email {
  font-size: 14px;
  color: #303133;
}

/* 平板和桌面端 */
@media (min-width: 769px) {
  .role-tag {
    display: inline-flex;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .header {
    padding: 0 16px;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }

  .username {
    display: none;
  }

  .user-detail {
    min-width: 180px;
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .header {
    padding: 0 12px;
  }

  .header-left :deep(.el-breadcrumb) {
    font-size: 13px;
  }
}
</style>
