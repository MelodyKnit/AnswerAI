<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { Users, FileText, CheckCircle, Clock, Database, Edit, ListTodo } from 'lucide-vue-next'
import { getExams, getTeacherDashboardOverview } from '@/api/teacher'

const authStore = useAuthStore()
const router = useRouter()

const stats = ref([
  { label: '今日应考', value: '-', icon: Users },
  { label: '待批阅', value: '-', icon: FileText },
  { label: '平均分', value: '-', icon: CheckCircle },
  { label: '学习时长(均)', value: '-', icon: Clock },
])

const quickActions = [
  { label: '题库管理', icon: Database, route: '/app/teacher/questions', color: '#3b82f6' },
  { label: '考试管理', icon: Edit, route: '/app/teacher/exams', color: '#10b981' },
  { label: '阅卷任务', icon: ListTodo, route: '/app/teacher/review', color: '#f59e0b' },
  { label: '学情分析', icon: CheckCircle, route: '/app/teacher/analytics', color: '#8b5cf6' }
]

const recentExams = ref<any[]>([])

const navigate = (path: string) => {
  router.push(path)
}

const fetchData = async () => {
  try {
    const [overviewRes, examsRes] = await Promise.all([
      getTeacherDashboardOverview(),
      getExams({ page: 1, page_size: 5 }),
    ])

    const overview = overviewRes as any
    recentExams.value = (examsRes as any).items || []

    const trend = Array.isArray(overview.avg_score_trend) ? overview.avg_score_trend : []
    const avgScore = trend.length > 0
      ? (trend.reduce((sum: number, item: any) => sum + Number(item.avg_score || 0), 0) / trend.length).toFixed(1)
      : '-'

    stats.value = [
      { label: '考试总数', value: String(overview.exam_count ?? 0), icon: Users },
      { label: '待批阅', value: String(overview.pending_review_count ?? 0), icon: FileText },
      { label: '风险学生', value: String(overview.risk_student_count ?? 0), icon: CheckCircle },
      { label: '平均分', value: avgScore, icon: Clock },
    ]
  } catch(e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="view-dashboard">
    <header class="dashboard-header">
      <h1 class="greeting">工作台</h1>
      <p class="greeting-sub">您好，{{ authStore.user?.name || '老师' }}！这里是今日的最新学情概览。</p>
    </header>

    <section class="quick-tools">
      <div 
        v-for="action in quickActions" 
        :key="action.label" 
        class="tool-card clickable"
        @click="navigate(action.route)"
      >
        <div class="icon-wrapper" :style="{ backgroundColor: action.color + '1A', color: action.color }">
          <component :is="action.icon" :size="24" />
        </div>
        <span class="tool-label">{{ action.label }}</span>
      </div>
    </section>

    <section class="metrics-grid">
      <div v-for="stat in stats" :key="stat.label" class="metric-card">
        <div class="metric-top">
          <component :is="stat.icon" :size="18" class="metric-icon" />
          <span class="metric-label">{{ stat.label }}</span>
        </div>
        <div class="metric-value">{{ stat.value }}</div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">
        <h2>最近测验与待办</h2>
      </div>
      <div class="list-container">
        <div v-for="exam in recentExams" :key="exam.id" class="list-item">      
          <div class="item-main">
            <h3>{{ exam.title }}</h3>
            <div class="item-meta">
              <span class="meta-tag">{{ exam.subject }}</span>
              <span class="meta-text">时长: {{ exam.duration_minutes }}分钟</span>
            </div>
          </div>
          <div class="item-action">
            <span class="status-indicator" :class="{ 'status--active': exam.status !== 'finished' }">{{ exam.status }}</span>                                                   
            <button class="button button--small" v-if="exam.status !== 'finished'" @click="navigate('/app/teacher/review')">去批阅</button>
            <button class="button button--ghost button--small" v-else>看报告</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.view-dashboard { display: flex; flex-direction: column; gap: 32px; }
.dashboard-header { margin-bottom: 8px; }
.greeting { font-size: 24px; font-weight: 600; color: var(--ink); letter-spacing: -0.02em; margin-bottom: 4px; }
.greeting-sub { font-size: 14px; color: var(--ink-soft); }
.quick-tools { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.tool-card { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.icon-wrapper { width: 48px; height: 48px; border-radius: 16px; display: flex; align-items: center; justify-content: center; }
.tool-label { font-size: 12px; color: var(--ink); font-weight: 500; }
.metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
@media (min-width: 768px) { .metrics-grid { grid-template-columns: repeat(4, 1fr); } }
.metric-card { padding: 16px; border: 1px solid var(--line); background: #fff; border-radius: var(--radius-md); display: flex; flex-direction: column; gap: 12px; }
.metric-top { display: flex; align-items: center; gap: 8px; }
.metric-icon { color: var(--ink-soft); }
.metric-label { font-size: 13px; color: var(--ink-soft); }
.metric-value { font-size: 24px; font-weight: 600; color: var(--ink); letter-spacing: -0.02em; }
.section-block { display: flex; flex-direction: column; gap: 16px; }
.section-title h2 { font-size: 16px; font-weight: 600; color: var(--ink); }
.list-container { display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: var(--radius-md); background: #fff; }
.list-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid var(--line); gap: 16px; }
.list-item:last-child { border-bottom: none; }
.item-main { display: flex; flex-direction: column; gap: 6px; }
.item-main h3 { font-size: 15px; font-weight: 500; color: var(--ink); }
.item-meta { display: flex; align-items: center; gap: 12px; }
.meta-tag { font-size: 12px; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--ink-soft); }
.meta-text { font-size: 13px; color: var(--ink-soft); }
.item-action { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.status-indicator { font-size: 12px; color: var(--ink-soft); }
.status--active { color: var(--accent); font-weight: 500; }
.button--small { padding: 4px 12px; font-size: 13px; min-width: 68px; }
</style>




