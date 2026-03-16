<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronRight, Target, Clock, AlertCircle, BarChart2 } from 'lucide-vue-next'    
import { useAuthStore } from '@/stores/auth'
import http from '@/lib/http'

const authStore = useAuthStore()

const dashboardData = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await http.get('/student/dashboard/overview')
    dashboardData.value = res // Fallback in case response structure varies
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="view-dashboard" v-if="!loading">
    <!-- Greeting -->
    <header class="dashboard-header animate-fade-in">
      <h1 class="greeting">早上好，{{ authStore.user?.name || authStore.user?.username || '' }}同学</h1>
      <p class="greeting-sub">今天是你坚持学习的第 24 天。稳步前进。</p>        
    </header>

    <!-- AI Insights / Diagnostic Summary -->
    <section class="section-block animate-fade-in-up" style="animation-delay: 0.1s">
      <div class="insights-box">
        <div class="insight-header">
          <Target :size="18" class="insight-icon" />
          <span class="font-semibold text-sm">核心学情诊断</span>
        </div>
        <p class="insight-text text-sm mt-2 text-ink-soft">
          {{ dashboardData?.ai_reminders?.[0] || '系统正在收集您的学习数据，多参加测验能获得更精准的诊断。' }}
        </p>
        <RouterLink to="/app/student/study-plan" class="insight-action mt-3 inline-flex items-center text-xs font-medium text-accent">
          查看复习建议 <ChevronRight :size="14" />
        </RouterLink>
      </div>
    </section>

    <!-- Stats overview -->
    <section class="section-block stats-grid animate-fade-in-up" style="animation-delay: 0.2s">
      <div class="stat-card">
        <div class="stat-header">
          <Clock :size="16" class="stat-icon" />
          <span class="stat-label">待完成测验</span>
        </div>
        <div class="stat-value">{{ dashboardData?.upcoming_exam_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-header">
          <BarChart2 :size="16" class="stat-icon" />
          <span class="stat-label">知识点掌握度</span>
        </div>
        <div class="stat-value">68<span class="text-sm font-normal text-ink-soft ml-1">%</span></div>
      </div>
    </section>

    <!-- Action Cards -->
    <section class="section-block animate-fade-in-up" style="animation-delay: 0.3s">
      <div class="section-title">
        <h2>待办学习任务</h2>
        <RouterLink to="/app/student/exams" class="see-all">考试列表 <ChevronRight :size="14"/></RouterLink>
      </div>

      <div class="exam-list" v-if="dashboardData?.recent_exams?.length || dashboardData?.recommended_tasks?.length">
        <div v-for="exam in dashboardData.recent_exams || []" :key="`exam-${exam.id}`" class="exam-item">
          <div class="exam-info">
            <h3>{{ exam.title }}</h3>
            <div class="exam-tags">
              <span class="tag"><AlertCircle :size="10" /> 待完成考试</span>
            </div>
          </div>
          <RouterLink :to="`/app/student/exams/${exam.id}/prep`" class="button button--small">去考试</RouterLink>
        </div>
        <div v-for="task in dashboardData.recommended_tasks" :key="task.task_id" class="exam-item">
          <div class="exam-info">
            <h3>{{ task.title }}</h3>
            <div class="exam-tags">
              <span class="tag" v-if="task.priority === 1"><AlertCircle :size="10" /> 高优</span>
              <span class="tag" v-else>常规</span>
            </div>
          </div>
          <RouterLink :to="`/app/student/exams`" class="button button--small">处理</RouterLink>
        </div>
      </div>
      <div class="empty-state" v-else>
        <p>目前没有紧急的待办任务</p>
        <span>您可以去浏览之前的错题记录</span>
      </div>
    </section>
  </div>
  
  <div v-else class="loading-state">
    <div class="spinner"></div>
    <p>正在分析您的最新学情...</p>
  </div>
</template>

<style scoped>
.view-dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 24px;
}

.dashboard-header {
  margin-bottom: 4px;
}

.greeting {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}

.greeting-sub {
  font-size: 13px;
  color: var(--ink-soft);
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.section-title h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.see-all {
  font-size: 13px;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  text-decoration: none;
}

/* Minimal List Items */
.exam-list {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: var(--bg-soft);
  overflow: hidden;
}

.exam-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--line);
}

.exam-item:last-child {
  border-bottom: none;
}

.exam-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.exam-info h3 {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.exam-tags {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg);
  color: var(--ink-soft);
}

.button--small {
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 8px;
  background: var(--ink);
  color: var(--bg);
  text-decoration: none;
  font-weight: 500;
}

/* Insights */
.insights-box {
  background: linear-gradient(135deg, rgba(239, 246, 255, 1) 0%, rgba(219, 234, 254, 0.4) 100%);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(191, 219, 254, 0.5);
  box-shadow: 0 4px 20px -10px rgba(59, 130, 246, 0.1);
}

.insight-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent);
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon {
  color: var(--ink-soft);
}

.stat-label {
  font-size: 12px;
  color: var(--ink-soft);
  font-weight: 500;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  text-align: center;
  gap: 4px;
}

.empty-state p {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.empty-state span {
  font-size: 12px;
  color: var(--ink-soft);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
  color: var(--ink-soft);
  font-size: 14px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}

.animate-fade-in-up {
  opacity: 0;
  transform: translateY(10px);
  animation: fadeInUp 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>


