<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Users, GraduationCap, ChevronRight } from 'lucide-vue-next'
import { getClasses } from '@/api/teacher'

const router = useRouter()
const classes = ref<any[]>([])
const isLoading = ref(true)

const fetchClasses = async () => {
  try {
    isLoading.value = true
    const res = await getClasses()
    classes.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to fetch classes', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchClasses()
})

const goDetail = (id: number) => {
  router.push(`/app/teacher/classes/${id}`)
}
</script>

<template>
  <div class="view-classes">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">我的班级</h1>
        <button class="button button--small" @click="router.push('/app/teacher/classes/create')">
          <Plus :size="16" />
          <span>创建班级</span>
        </button>
      </div>
      <p class="page-desc">管理您的教学班级，查看学情和学生名单。</p>
    </header>

    <div v-if="isLoading" class="loading-state">
      加载中...
    </div>
    
    <div v-else-if="classes.length === 0" class="empty-state">
      <div class="empty-icon">
        <GraduationCap :size="48" />
      </div>
      <p>暂无班级</p>
      <button class="button" @click="router.push('/app/teacher/classes/create')">创建我的首个班级</button>
    </div>

    <div v-else class="class-list">
      <div 
        v-for="cls in classes" 
        :key="cls.id" 
        class="class-card clickable"
        @click="goDetail(cls.id)"
      >
        <div class="card-header">
          <h2 class="class-name">{{ cls.name }}</h2>
          <span class="invite-code">邀请码: {{ cls.invite_code }}</span>
        </div>
        <div class="card-body">
          <div class="info-item">
            <Users :size="16" class="icon" />
            <span>{{ cls.student_count }} 人</span>
          </div>
          <div class="info-item">
            <span>{{ cls.grade_name }} • {{ cls.subject }}</span>
          </div>
        </div>
        <div class="card-footer">
          <span class="view-detail">管理班级</span>
          <ChevronRight :size="16" class="icon" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-classes {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.page-desc {
  font-size: 14px;
  color: var(--ink-soft);
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  color: var(--ink-soft);
  gap: 16px;
}

.class-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.class-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.2s ease;
}

.class-card:hover {
  border-color: var(--ink-light);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.class-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}

.invite-code {
  font-size: 12px;
  background: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--line);
  color: var(--ink-soft);
}

.card-body {
  display: flex;
  gap: 24px;
  color: var(--ink-soft);
  font-size: 14px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon {
  opacity: 0.7;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  font-size: 14px;
  color: var(--accent);
}

.view-detail {
  font-weight: 500;
}
</style>


