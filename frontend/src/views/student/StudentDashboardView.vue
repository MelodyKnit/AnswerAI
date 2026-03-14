<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronRight, Target, TrendingUp, BookOpen } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import http from '@/lib/http'

const authStore = useAuthStore()

const dashboardData = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await http.get('/student/dashboard/overview')
    dashboardData.value = res.data.data
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
    <header class="dashboard-header">
      <h1 class="greeting">早上好，{{ authStore.user?.full_name || '同学' }}</h1>
      <p class="greeting-sub">今天是你坚持学习的第 24 天。稳步前进。</p>
    </header>

    <!-- Urgent Action Cards -->
    <section class="section-block" v-if="dashboardData?.recommended_tasks?.length">
      <div class="section-title">
        <h2>待完成的考试任务</h2>
        <RouterLink to="/app/student/exams" class="see-all">全部 <ChevronRight :size="14"/></RouterLink>
      </div>

      <div class="exam-list">
        <div v-for="task in dashboardData.recommended_tasks" :key="task.task_id" class="exam-item">
          <div class="exam-info">
            <h3>{{ task.title }}</h3>
            <div class="exam-tags">
              <span class="tag">优先: {{ task.priority }}</span>
            </div>
          </div>
          <RouterLink :to="`/app/student/exams`" class="button button--small">
            进入
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- AI Insights -->
    <section class="section-block" v-if="dashboardData?.ai_reminders?.length">
      <div class="section-title">
        <h2>学情洞察</h2>
      </div>
      <div class="insights-box">
        <div v-for="(reminder, index) in dashboardData.ai_reminders" :key="index" class="insight-row">
          <Target :size="18" class="insight-icon" />
          <p>{{ reminder }}</p>
          <button class="text-button">去复习</button>
        </div>
      </div>
    </section>

    <!-- Stats summary -->
    <section class="section-block stats-grid">
      <div class="stat-card">
        <TrendingUp :size="20" class="stat-icon" />
        <div class="stat-value">{{ dashboardData?.upcoming_exam_count || 0 }}</div>
        <div class="stat-label">待完成考试数</div>
      </div>
      <div class="stat-card" v-if="dashboardData?.ability_profile_summary">
        <BookOpen :size="20" class="stat-icon" />
        <div class="stat-value">{{ Object.keys(dashboardData.ability_profile_summary).length }}</div>
        <div class="stat-label">能力分析项</div>
      </div>
    </section>
  </div>
  <div v-else class="view-dashboard" style="align-items: center; justify-content: center; min-height: 50vh;">
    加载中...
  </div>
</template>

<style scoped>
.view-dashboard {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.dashboard-header {
  margin-bottom: 8px;
}

.greeting {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}

.greeting-sub {
  font-size: 14px;
  color: var(--ink-soft);
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
}

/* Minimal List Items */
.exam-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
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
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.exam-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--ink-soft);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.exam-tags {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg);
  color: var(--ink-soft);
}

.button--small {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: var(--radius-sm);
}

/* Insights */
.insights-box {
  background: var(--accent-soft);
  border-radius: var(--radius-md);
  padding: 16px;
}

.insight-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: start;
}

.insight-icon {
  color: var(--accent);
  margin-top: 2px;
}

.insight-row p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--ink);
}

.text-button {
  background: none;
  border: none;
  font-size: 13px;
  color: var(--accent);
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  margin-top: 2px;
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
  border-radius: var(--radius-md);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-icon {
  color: var(--ink-soft);
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.stat-label {
  font-size: 13px;
  color: var(--ink-soft);
}
</style>