<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { LogOut, User as UserIcon, Book, Building, ChevronRight, GraduationCap, Settings2 } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import http from '@/lib/http'
import { useRouter } from 'vue-router'
import UserFeedbackButton from '@/components/common/UserFeedbackButton.vue'

const authStore = useAuthStore()
const router = useRouter()

const classes = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    if (!authStore.user && authStore.token) {
      await authStore.fetchUser()
    }
    const res: any = await http.get('/student/classes')
    classes.value = res?.classes || res.data?.classes || []
  } catch (error) {
    console.error('获取班级数据失败:', error)
  } finally {
    loading.value = false
  }
})

const handleLogout = () => {
  authStore.logout()
  router.push('/auth')
}

const goProfileSettings = () => {
  router.push('/app/student/settings/profile')
}
</script>

<template>
  <div class="view-profile animate-fade-in">
    <header class="profile-head">
      <h1>我的档案</h1>
      <p>查看班级信息与维护个人资料。</p>
    </header>

    <section class="profile-card">
      <div class="avatar-circle">
        <span>{{ (authStore.user?.username || '用户').charAt(0).toUpperCase() }}</span>
      </div>
      <div class="user-info">
        <p class="user-kicker">学生档案</p>
        <h1 class="user-name">{{ authStore.user?.name || authStore.user?.username || '未命名学生' }}</h1>
        <p class="user-id">学号: {{ authStore.user?.id || '--' }}</p>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">
        <h2>我的班级</h2>
        <span class="count-badge" v-if="classes.length">{{ classes.length }}</span>
      </div>

      <div class="classes-list" v-if="loading">
        <div class="loading-state h-32">加载中...</div>
      </div>
      <div class="classes-list" v-else-if="classes.length">
        <div v-for="cls in classes" :key="cls.class_id" class="class-item">
          <div class="class-icon">
            <GraduationCap :size="24" class="text-accent" />
          </div>
          <div class="class-info">
            <h3 class="class-name">{{ cls.name }}</h3>
            <div class="class-meta">
              <span class="meta-tag"><Book :size="12" /> {{ cls.subject }}</span>
              <span class="meta-tag"><UserIcon :size="12" /> {{ cls.teacher_name }} 老师</span>
              <span class="meta-tag"><Building :size="12" /> {{ cls.grade_name }}</span>
            </div>
          </div>
          <div class="action-arrow">
            <ChevronRight :size="18" />
          </div>
        </div>
      </div>
      <div class="empty-state" v-else>
        <GraduationCap :size="30" class="text-ink-soft opacity-40" />
        <p>您尚未加入任何班级</p>
        <span class="empty-sub">请向任课教师获取班级邀请码</span>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">
        <h2>系统设置</h2>
      </div>
      <div class="feedback-row">
        <UserFeedbackButton context-label="学生-我的档案" />
      </div>
      <div class="settings-list">
        <div class="settings-item" @click="goProfileSettings">
          <Settings2 :size="18" />
          <span>编辑个人档案信息</span>
          <ChevronRight :size="16" class="item-arrow" />
        </div>
        <div class="settings-item text-destructive" @click="handleLogout">
          <LogOut :size="18" />
          <span>退出登录</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.view-profile {
  --profile-bg: #f5f7f6;
  --profile-ink: #1f2a24;
  --profile-soft: #607068;
  --profile-line: #d8e0da;
  --profile-brand: #0f766e;
  --profile-brand-soft: #e5f4f1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100vh - 56px - 72px);
  width: calc(100% + 32px);
  margin: -24px -16px -24px;
  padding: 34px 16px 38px;
  background:
    radial-gradient(circle at 88% -12%, rgba(15, 118, 110, 0.14), transparent 34%),
    linear-gradient(180deg, #f9fbfa 0%, var(--profile-bg) 100%);
}

.profile-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.profile-head h1 {
  margin: 0;
  font-size: 30px;
  letter-spacing: -0.02em;
  color: var(--profile-ink);
}

.profile-head p {
  margin: 0;
  font-size: 13px;
  color: var(--profile-soft);
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: rgba(255, 255, 255, 0.88);
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--profile-line);
  box-shadow: 0 8px 20px rgba(18, 38, 28, 0.05);
}

.item-arrow {
  margin-left: auto;
  color: var(--profile-soft);
}

.avatar-circle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(140deg, #138279, var(--profile-brand));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  box-shadow: 0 6px 14px rgba(15, 118, 110, 0.25);
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-kicker {
  margin: 0;
  font-size: 11px;
  color: var(--profile-soft);
}

.user-name {
  margin: 0;
  font-size: 28px;
  line-height: 1.05;
  letter-spacing: -0.02em;
  font-weight: 600;
  color: var(--profile-ink);
}

.user-id {
  margin: 0;
  font-size: 13px;
  color: var(--profile-soft);
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px;
}

.section-title h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--profile-ink);
}

.count-badge {
  background: var(--profile-brand-soft);
  color: var(--profile-brand);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
}

.classes-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.class-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--profile-line);
  transition: all 0.2s;
  cursor: pointer;
}

.class-item:active {
  transform: scale(0.98);
  background: var(--bg-soft);
}

.class-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--profile-brand-soft);
  display: flex;
  align-items: center;
  justify-content: center;
}

.class-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.class-name {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--profile-ink);
}

.class-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--profile-soft);
  background: #f6f8f7;
  padding: 2px 6px;
  border-radius: 4px;
}

.action-arrow {
  color: var(--profile-soft);
}

.settings-list {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--profile-line);
  overflow: hidden;
}

.feedback-row {
  display: flex;
}

.settings-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  transition: background 0.2s;
}

.settings-item:active {
  background: var(--bg-soft);
}

.text-destructive {
  color: #ef4444;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 26px 16px;
  background: #fff;
  border: 1px solid var(--profile-line);
  border-radius: 12px;
  text-align: center;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--profile-ink);
}

.empty-sub {
  font-size: 12px;
  color: var(--profile-soft);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (min-width: 768px) {
  .view-profile {
    width: calc(100% + 64px);
    margin: -40px -32px -40px;
    padding: 56px 32px 52px;
    min-height: calc(100vh - 56px - 72px);
  }
}

@media (max-width: 640px) {
  .profile-card {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .profile-head h1 {
    font-size: 26px;
  }
}
</style>