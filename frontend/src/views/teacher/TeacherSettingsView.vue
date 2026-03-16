<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { RouterView, useRoute } from 'vue-router'
import { Bell, ChevronRight, LogOut, Shield, User } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isSettingsHome = computed(() => route.path === '/app/teacher/settings')

const goToProfile = () => router.push('/app/teacher/settings/profile')
const goToNotification = () => router.push('/app/teacher/settings/notifications')
const goToSecurity = () => router.push('/app/teacher/settings/security')

const handleLogout = () => {
  const confirmed = window.confirm('确认退出登录吗？')
  if (!confirmed) return
  authStore.logout()
  router.push('/app/auth')
}
</script>

<template>
  <div class="settings-shell">
    <div v-if="isSettingsHome" class="settings-home">
    <header class="page-header">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">点击进入对应页面进行详细设置。</p>
    </header>

    <section class="profile-card">
      <div class="avatar">{{ authStore.user?.name?.charAt(0)?.toUpperCase() || '师' }}</div>
      <div class="profile-meta">
        <h2>{{ authStore.user?.name || '未设置姓名' }}</h2>
        <p>{{ authStore.user?.email || '未绑定邮箱' }}</p>
      </div>
    </section>

    <section class="menu-list">
      <button class="menu-item" @click="goToProfile">
        <span class="left">
          <User :size="18" />
          个人资料
        </span>
        <ChevronRight :size="16" />
      </button>

      <button class="menu-item" @click="goToNotification">
        <span class="left">
          <Bell :size="18" />
          消息通知
        </span>
        <ChevronRight :size="16" />
      </button>

      <button class="menu-item" @click="goToSecurity">
        <span class="left">
          <Shield :size="18" />
          账号与安全
        </span>
        <ChevronRight :size="16" />
      </button>
    </section>

    <button class="logout-btn" @click="handleLogout">
      <LogOut :size="16" />
      退出登录
    </button>
    </div>

    <RouterView v-else />
  </div>
</template>

<style scoped>
.settings-shell {
  display: flex;
  flex-direction: column;
}

.settings-home {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.page-subtitle {
  margin: 0;
  color: #556278;
  font-size: 13px;
}

.profile-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: linear-gradient(145deg, #ffffff, #f7fbff);
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(145deg, #0f766e, #0d9488);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 20px;
}

.profile-meta h2 {
  margin: 0;
  font-size: 20px;
}

.profile-meta p {
  margin: 4px 0 0;
  color: #556278;
  font-size: 13px;
}

.menu-list {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}

.menu-item {
  width: 100%;
  border: none;
  border-bottom: 1px solid #edf2f8;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  color: #0f172a;
  font-size: 15px;
}

.menu-item:last-child {
  border-bottom: none;
}

.left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.logout-btn {
  margin-top: 6px;
  border: 1px solid #fecaca;
  background: #fff5f5;
  color: #dc2626;
  border-radius: 12px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
}
</style>
