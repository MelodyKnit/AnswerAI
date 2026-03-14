<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { LogOut, User, Bell, Shield, ChevronRight } from 'lucide-vue-next'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = () => {
  authStore.logout()
  router.push('/app/auth')
}
</script>

<template>
  <div class="view-settings">
    <header class="page-header">
      <h1 class="page-title">设置</h1>
    </header>

    <div class="user-profile">
      <div class="avatar">
        {{ authStore.user?.name?.charAt(0) || '师' }}
      </div>
      <div class="user-info">
        <h2>{{ authStore.user?.name || '未设置姓名' }}</h2>
        <p>{{ authStore.user?.email || '未绑定邮箱' }}</p>
      </div>
    </div>

    <div class="settings-group">
      <div class="setting-item clickable">
        <div class="item-left">
          <User :size="18" class="icon" />
          <span>个人资料</span>
        </div>
        <ChevronRight :size="16" class="icon-right" />
      </div>
      <div class="setting-item clickable">
        <div class="item-left">
          <Bell :size="18" class="icon" />
          <span>消息通知</span>
        </div>
        <ChevronRight :size="16" class="icon-right" />
      </div>
      <div class="setting-item clickable">
        <div class="item-left">
          <Shield :size="18" class="icon" />
          <span>账号与安全</span>
        </div>
        <ChevronRight :size="16" class="icon-right" />
      </div>
    </div>

    <button class="button button--secondary logout-btn" @click="handleLogout">
      <LogOut :size="18" />
      退出登录
    </button>
  </div>
</template>

<style scoped>
.view-settings {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  padding-bottom: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
}

.user-info h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}

.user-info p {
  font-size: 14px;
  color: var(--ink-soft);
}

.settings-group {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  transition: background-color 0.2s;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-item:hover {
  background-color: var(--bg);
}

.item-left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: var(--ink);
}

.icon {
  color: var(--ink-soft);
}

.icon-right {
  color: var(--ink-soft);
  opacity: 0.5;
}

.logout-btn {
  margin-top: 16px;
  color: #ef4444; /* red text for logout */
  border-color: #fca5a5;
  background-color: #fef2f2;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.logout-btn:hover {
  background-color: #fee2e2;
}
</style>


