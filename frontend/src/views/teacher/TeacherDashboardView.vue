<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { Users, FileText, CheckCircle, Clock, Database, Edit, ListTodo, RotateCcw } from 'lucide-vue-next'
import { getExams, getTeacherDashboardOverview } from '@/api/teacher'

const authStore = useAuthStore()
const router = useRouter()

const stats = ref([
  { label: '今日应考', value: '-', icon: Users, route: '', tone: 'neutral' },
  { label: '待批阅', value: '-', icon: FileText, route: '', tone: 'neutral' },
  { label: '平均分', value: '-', icon: CheckCircle, route: '', tone: 'neutral' },
  { label: '学习时长(均)', value: '-', icon: Clock, route: '', tone: 'neutral' },
])

const quickActions = [
  { label: '题库管理', icon: Database, route: '/app/teacher/questions', color: '#3b82f6' },
  { label: '考试管理', icon: Edit, route: '/app/teacher/exams', color: '#10b981' },
  { label: '阅卷任务', icon: ListTodo, route: '/app/teacher/review', color: '#f59e0b' },
  { label: '重考审批', icon: RotateCcw, route: '/app/teacher/retake-requests', color: '#0f766e' },
  { label: '学情分析', icon: CheckCircle, route: '/app/teacher/analytics', color: '#8b5cf6' }
]

const recentExams = ref<any[]>([])
const riskStudents = ref<any[]>([])

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
    riskStudents.value = Array.isArray(overview.risk_students) ? overview.risk_students : []

    const trend = Array.isArray(overview.avg_score_trend) ? overview.avg_score_trend : []
    const avgScore = trend.length > 0
      ? (trend.reduce((sum: number, item: any) => sum + Number(item.avg_score || 0), 0) / trend.length).toFixed(1)
      : '-'
    const hasNonZeroAverage = trend.some((item: any) => Number(item?.avg_score || 0) > 0)

    stats.value = [
      { label: '考试总数', value: String(overview.exam_count ?? 0), icon: Users, route: '/app/teacher/exams', tone: 'blue' },
      { label: '待批阅', value: String(overview.pending_review_count ?? 0), icon: FileText, route: '/app/teacher/review', tone: 'amber' },
      { label: '风险学生', value: String(overview.risk_student_count ?? 0), icon: CheckCircle, route: '/app/teacher/analytics', tone: 'red' },
      { label: '平均分', value: avgScore, icon: Clock, route: '', tone: hasNonZeroAverage ? 'teal' : 'slate' },
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
      <component
        v-for="stat in stats"
        :key="stat.label"
        :is="stat.route ? 'button' : 'div'"
        class="metric-card"
        :class="[
          `tone-${stat.tone || 'neutral'}`,
          stat.route ? 'metric-card--interactive' : 'metric-card--plain',
        ]"
        :type="stat.route ? 'button' : undefined"
        @click="stat.route ? navigate(stat.route) : undefined"
      >
        <div class="metric-top">
          <component :is="stat.icon" :size="18" class="metric-icon" />
          <span class="metric-label">{{ stat.label }}</span>
        </div>
        <div class="metric-value">{{ stat.value }}</div>
        <span v-if="stat.route" class="metric-link-tip">点击查看</span>
      </component>
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

    <section class="section-block">
      <div class="section-title title-with-action">
        <h2>风险学生洞察</h2>
        <button class="button button--small button--ghost" @click="navigate('/app/teacher/analytics')">查看班级分析</button>
      </div>

      <div v-if="riskStudents.length" class="risk-list">
        <article v-for="student in riskStudents" :key="`risk-${student.student_id}-${student.exam_id}`" class="risk-card">
          <div class="risk-head">
            <div>
              <h3>{{ student.student_name }}</h3>
              <p>
                {{ student.class_name || '未分配班级' }}
                <span v-if="student.exam_title"> · 最近考试《{{ student.exam_title }}》</span>
              </p>
            </div>
            <span class="risk-pill" :class="student.risk_level === 'high' ? 'high' : student.risk_level === 'medium' ? 'mid' : 'low'">
              {{ student.risk_level === 'high' ? '高风险' : student.risk_level === 'medium' ? '中风险' : '关注中' }}
            </span>
          </div>

          <div class="risk-metrics">
            <span>最近得分 {{ Number(student.latest_score || 0).toFixed(1) }}</span>
            <span>正确率 {{ Math.round(Number(student.correct_rate || 0) * 100) }}%</span>
          </div>

          <div class="risk-tags" v-if="student.weak_abilities?.length">
            <span v-for="ability in student.weak_abilities" :key="`${student.student_id}-${ability}`" class="ability-tag">{{ ability }}</span>
          </div>

          <p v-if="student.weak_knowledge_points?.length" class="risk-text">
            薄弱知识点：{{ student.weak_knowledge_points.join('、') }}
          </p>

          <ul class="risk-suggestions" v-if="student.coaching_suggestions?.length">
            <li v-for="(tip, idx) in student.coaching_suggestions" :key="`${student.student_id}-tip-${idx}`">{{ tip }}</li>
          </ul>
        </article>
      </div>

      <div v-else class="empty-risk">
        当前未识别到明显风险学生，建议继续跟踪下一次测验数据。
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
.metric-card {
  padding: 16px;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.metric-card--interactive {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.metric-card--interactive:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.metric-card--interactive:active {
  transform: translateY(0);
}

.metric-card--interactive:focus-visible {
  outline: 2px solid #0f766e;
  outline-offset: 2px;
}

.metric-top { display: flex; align-items: center; gap: 8px; }
.metric-icon { color: var(--ink-soft); }
.metric-label { font-size: 13px; color: var(--ink-soft); }
.metric-value { font-size: 24px; font-weight: 600; color: var(--ink); letter-spacing: -0.02em; }
.metric-link-tip { font-size: 11px; color: #64748b; }

.tone-blue .metric-icon,
.tone-blue .metric-label,
.tone-blue .metric-link-tip { color: #1d4ed8; }
.tone-blue .metric-value { color: #1e40af; }
.tone-blue.metric-card--interactive:hover { border-color: #bfdbfe; }

.tone-amber .metric-icon,
.tone-amber .metric-label,
.tone-amber .metric-link-tip { color: #b45309; }
.tone-amber .metric-value { color: #92400e; }
.tone-amber.metric-card--interactive:hover { border-color: #fcd34d; }

.tone-red .metric-icon,
.tone-red .metric-label,
.tone-red .metric-link-tip { color: #b91c1c; }
.tone-red .metric-value { color: #991b1b; }
.tone-red.metric-card--interactive:hover { border-color: #fca5a5; }

.tone-slate .metric-icon,
.tone-slate .metric-label { color: #475569; }
.tone-slate .metric-value { color: #1f2937; }

.tone-teal .metric-icon,
.tone-teal .metric-label { color: #0f766e; }
.tone-teal .metric-value { color: #0f766e; }
.section-block { display: flex; flex-direction: column; gap: 16px; }
.section-title h2 { font-size: 16px; font-weight: 600; color: var(--ink); }
.title-with-action { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
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

.risk-list { display: grid; gap: 10px; }

.risk-card {
  border: 1px solid #dfe8f3;
  border-radius: 14px;
  background: #fff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.risk-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }

.risk-head h3 { margin: 0; font-size: 15px; color: #0f172a; }

.risk-head p { margin: 4px 0 0; font-size: 12px; color: #64748b; }

.risk-pill {
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-weight: 600;
}

.risk-pill.high { color: #b91c1c; background: #fef2f2; border-color: #fecaca; }
.risk-pill.mid { color: #b45309; background: #fffbeb; border-color: #fde68a; }
.risk-pill.low { color: #0369a1; background: #f0f9ff; border-color: #bae6fd; }

.risk-metrics { display: flex; gap: 14px; font-size: 12px; color: #475569; }

.risk-tags { display: flex; flex-wrap: wrap; gap: 6px; }

.ability-tag {
  font-size: 11px;
  color: #0f766e;
  border: 1px solid #bde8df;
  background: #f0fdfa;
  border-radius: 999px;
  padding: 3px 8px;
}

.risk-text { margin: 0; font-size: 12px; color: #475569; }

.risk-suggestions {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  color: #334155;
  font-size: 12px;
  line-height: 1.5;
}

.empty-risk {
  border: 1px dashed #d7e1ee;
  border-radius: 12px;
  background: #f8fbff;
  color: #64748b;
  font-size: 13px;
  text-align: center;
  padding: 14px;
}
</style>




