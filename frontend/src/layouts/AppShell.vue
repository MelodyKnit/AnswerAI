<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { Bell, ArrowLeft, GraduationCap, LayoutDashboard, History, Settings } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

// Determine if we are in student or teacher mode
const isTeacher = computed(() => route.meta.section === 'teacher')

// Dynamic Topbar logic
const canGoBack = computed(() => window.history.state.back != null && route.path !== '/app/student/dashboard' && route.path !== '/app/teacher/dashboard')
const pageTitle = computed(() => route.meta.title || 'AI Answer')

const handleBack = () => {
  if (canGoBack.value) {
    router.back()
  }
}

// Minimal Navigation
const navItems = computed(() => {
  if (isTeacher.value) {
    return [
      { label: '工作台', icon: LayoutDashboard, to: '/app/teacher/dashboard' },
      { label: '班级', icon: GraduationCap, to: '/app/teacher/classes' },
      { label: '设置', icon: Settings, to: '/app/teacher/settings' }
    ]
  }
  return [
    { label: '学习中心', icon: LayoutDashboard, to: '/app/student/dashboard' },
    { label: '复习', icon: History, to: '/app/student/history' },
    { label: '我的', icon: Settings, to: '/app/student/profile' }
  ]
})
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-left">
        <button v-if="canGoBack" class="icon-btn" @click="handleBack">
          <ArrowLeft :size="20" />
        </button>
        <span v-else class="brand-text">AI Answer</span>
      </div>
      
      <div class="header-title">
        {{ pageTitle }}
      </div>

      <div class="header-right">
        <button class="icon-btn" aria-label="Notifications">
          <Bell :size="20" />
        </button>
      </div>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <nav class="app-nav" v-if="!route.meta.hideNav">
      <RouterLink 
        v-for="item in navItems" 
        :key="item.to" 
        :to="item.to"
        class="nav-item"
        active-class="nav-item--active"
      >
        <component :is="item.icon" :size="22" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--bg);
}

.app-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 16px;
  height: 56px;
  background: rgba(250, 250, 250, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-left {
  display: flex;
  justify-content: flex-start;
}

.header-right {
  display: flex;
  justify-content: flex-end;
}

.brand-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--ink);
  letter-spacing: -0.01em;
}

.header-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink);
  text-align: center;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.icon-btn:hover {
  background: rgba(25, 20, 17, 0.04);
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.app-nav {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  background: rgba(250, 250, 250, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-top: 1px solid var(--line);
  position: sticky;
  bottom: 0;
  z-index: 50;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--ink-soft);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 8px;
  transition: color 0.2s;
}

.nav-item span {
  font-size: 11px;
  font-weight: 500;
}

.nav-item--active {
  color: var(--accent);
}

@media (min-width: 768px) {
  .app-main {
    padding: 40px 32px;
  }
}
</style>