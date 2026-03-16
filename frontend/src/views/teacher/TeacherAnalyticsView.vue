<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Brain, Lightbulb, Sparkles, TriangleAlert, Users } from 'lucide-vue-next'
import { getExamInsights, getExams, getTeacherDashboardOverview } from '@/api/teacher'

const router = useRouter()

const isLoading = ref(true)
const loadingError = ref('')

const examSnapshots = ref<Array<{
  id: number
  title: string
  subject: string
  completionRate: number
  avgScore: number
  wrongRate: number
  targetCount: number
  submittedCount: number
  topWrongQuestions: Array<any>
  aiSummary: { easy_mistakes: string[], teaching_suggestions: string[] }
}>>([])

const overview = ref<any>(null)

const riskExamCount = computed(() => examSnapshots.value.filter((item) => item.wrongRate >= 0.45).length)
const lowCompletionExamCount = computed(() => examSnapshots.value.filter((item) => item.completionRate < 0.6).length)
const avgCompletion = computed(() => {
  if (!examSnapshots.value.length) return 0
  const sum = examSnapshots.value.reduce((acc, item) => acc + item.completionRate, 0)
  return Math.round((sum / examSnapshots.value.length) * 100)
})
const avgWrongRate = computed(() => {
  if (!examSnapshots.value.length) return 0
  const sum = examSnapshots.value.reduce((acc, item) => acc + item.wrongRate, 0)
  return Math.round((sum / examSnapshots.value.length) * 100)
})

const aiFocusTopics = computed(() => {
  const counts = new Map<string, number>()
  for (const exam of examSnapshots.value) {
    for (const item of exam.topWrongQuestions.slice(0, 5)) {
      const stem = String(item?.stem || '')
      const matches = stem.match(/[\u4e00-\u9fa5]{2,8}/g) || []
      const picked = matches.find((m) => m.length >= 2)
      if (!picked) continue
      counts.set(picked, (counts.get(picked) || 0) + 1)
    }
  }
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, count]) => ({ name, count }))
})

const aiTeachingActions = computed(() => {
  const actions: string[] = []
  if (lowCompletionExamCount.value > 0) {
    actions.push(`有 ${lowCompletionExamCount.value} 场测验提交率偏低，建议先排查到课率与作答流程，再安排补测。`)
  }
  if (riskExamCount.value > 0) {
    actions.push(`有 ${riskExamCount.value} 场测验整体错误率偏高，建议进行 15 分钟错因讲评并布置同构题二次练习。`)
  }
  if (aiFocusTopics.value.length > 0) {
    actions.push(`高频薄弱主题：${aiFocusTopics.value.slice(0, 3).map((x) => x.name).join('、')}，建议按主题分组辅导。`)
  }

  const suggestionPool = examSnapshots.value
    .flatMap((item) => item.aiSummary.teaching_suggestions || [])
    .filter(Boolean)
    .slice(0, 3)

  for (const suggestion of suggestionPool) {
    actions.push(String(suggestion))
  }

  if (actions.length === 0) {
    actions.push('当前数据较稳定，建议维持每周一次小测 + 针对错题的短讲评闭环。')
  }

  return actions.slice(0, 6)
})

const learnerGrouping = computed(() => {
  const total = Number(overview.value?.risk_student_count || 0)
  const highRisk = Math.max(0, Math.round(total * 0.35))
  const mediumRisk = Math.max(0, total - highRisk)
  return {
    highRisk,
    mediumRisk,
    normal: Math.max(0, Number(overview.value?.exam_count || 0) - total),
  }
})

const smartSummary = computed(() => {
  const parts: string[] = []
  parts.push(`近期待分析测验 ${examSnapshots.value.length} 场，平均提交率 ${avgCompletion.value}%`) 
  parts.push(`整体错误率约 ${avgWrongRate.value}%`) 
  if (aiFocusTopics.value.length > 0) {
    parts.push(`薄弱主题集中在 ${aiFocusTopics.value.slice(0, 2).map((x) => x.name).join('、')}`)
  }
  return parts.join('；')
})

const goExamDetail = (id: number) => {
  router.push(`/app/teacher/exams/${id}`)
}

const fetchAnalytics = async () => {
  try {
    isLoading.value = true
    loadingError.value = ''

    const [dashboardRes, examsRes] = await Promise.all([
      getTeacherDashboardOverview(),
      getExams({ page: 1, page_size: 8 }),
    ])

    overview.value = dashboardRes
    const exams = ((examsRes as any)?.items || []) as any[]

    const insightRows = await Promise.all(
      exams.map(async (exam) => {
        try {
          const insight = await getExamInsights(Number(exam.id))
          const progress = (insight as any)?.progress || {}
          const learning = (insight as any)?.learning || {}
          const aiSummary = (insight as any)?.ai_summary || {}
          return {
            id: Number(exam.id),
            title: String(exam.title || '未命名测验'),
            subject: String(exam.subject || '未分类'),
            completionRate: Number(progress.completion_rate || 0),
            avgScore: Number(learning.avg_score || 0),
            wrongRate: Number(learning.overall_wrong_rate || 0),
            targetCount: Number(progress.target_count || 0),
            submittedCount: Number(progress.submitted_count || 0),
            topWrongQuestions: Array.isArray((insight as any)?.top_wrong_questions) ? (insight as any).top_wrong_questions : [],
            aiSummary: {
              easy_mistakes: Array.isArray(aiSummary.easy_mistakes) ? aiSummary.easy_mistakes : [],
              teaching_suggestions: Array.isArray(aiSummary.teaching_suggestions) ? aiSummary.teaching_suggestions : [],
            },
          }
        } catch {
          return {
            id: Number(exam.id),
            title: String(exam.title || '未命名测验'),
            subject: String(exam.subject || '未分类'),
            completionRate: 0,
            avgScore: 0,
            wrongRate: 0,
            targetCount: 0,
            submittedCount: 0,
            topWrongQuestions: [],
            aiSummary: { easy_mistakes: [], teaching_suggestions: [] },
          }
        }
      }),
    )

    examSnapshots.value = insightRows
  } catch (error: any) {
    console.error('Failed to load teacher analytics', error)
    loadingError.value = error?.message || '学情分析加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchAnalytics()
})
</script>

<template>
  <div class="view-teacher-analytics">
    <header class="page-header">
      <h1>学情分析</h1>
      <p>AI 自动汇总测验表现，生成可执行的辅导建议，帮助您快速发现班级薄弱点。</p>
    </header>

    <div v-if="isLoading" class="state-shell">正在生成学情洞察...</div>
    <div v-else-if="loadingError" class="state-shell state-error">{{ loadingError }}</div>

    <template v-else>
      <section class="overview-grid">
        <article class="metric-card">
          <div class="metric-head">
            <Users :size="16" />
            <span>平均提交率</span>
          </div>
          <p class="metric-value">{{ avgCompletion }}%</p>
        </article>
        <article class="metric-card">
          <div class="metric-head">
            <TriangleAlert :size="16" />
            <span>高风险测验</span>
          </div>
          <p class="metric-value">{{ riskExamCount }} 场</p>
        </article>
        <article class="metric-card">
          <div class="metric-head">
            <Sparkles :size="16" />
            <span>整体错误率</span>
          </div>
          <p class="metric-value">{{ avgWrongRate }}%</p>
        </article>
      </section>

      <section class="ai-summary-card">
        <div class="card-title-row">
          <div class="title-left">
            <Brain :size="16" />
            <h2>AI 班级学习诊断</h2>
          </div>
        </div>
        <p class="summary-text">{{ smartSummary }}</p>
        <div class="topic-list" v-if="aiFocusTopics.length">
          <span v-for="topic in aiFocusTopics" :key="topic.name" class="topic-chip">
            {{ topic.name }} · {{ topic.count }}次
          </span>
        </div>
      </section>

      <section class="split-grid">
        <article class="panel-card">
          <div class="card-title-row">
            <div class="title-left">
              <Lightbulb :size="16" />
              <h2>AI 辅导动作建议</h2>
            </div>
          </div>
          <ul class="action-list">
            <li v-for="(item, idx) in aiTeachingActions" :key="`ai-action-${idx}`">{{ item }}</li>
          </ul>
        </article>

        <article class="panel-card">
          <div class="card-title-row">
            <div class="title-left">
              <Users :size="16" />
              <h2>智能分层辅导建议</h2>
            </div>
          </div>
          <div class="group-grid">
            <div class="group-item high">
              <span>重点辅导组</span>
              <strong>{{ learnerGrouping.highRisk }}</strong>
            </div>
            <div class="group-item mid">
              <span>跟进巩固组</span>
              <strong>{{ learnerGrouping.mediumRisk }}</strong>
            </div>
            <div class="group-item normal">
              <span>常规推进组</span>
              <strong>{{ learnerGrouping.normal }}</strong>
            </div>
          </div>
          <p class="group-tip">建议每周至少 1 次针对重点组的 20 分钟错题面谈，跟进组进行同类题演练。</p>
        </article>
      </section>

      <section class="panel-card">
        <div class="card-title-row">
          <h2>测验维度对比</h2>
        </div>
        <div class="exam-list">
          <button v-for="exam in examSnapshots" :key="exam.id" class="exam-row" @click="goExamDetail(exam.id)">
            <div class="exam-main">
              <p class="exam-title">{{ exam.title }}</p>
              <p class="exam-meta">{{ exam.subject }} · {{ exam.submittedCount }}/{{ exam.targetCount }} 人提交</p>
            </div>
            <div class="exam-side">
              <span>均分 {{ exam.avgScore.toFixed(1) }}</span>
              <span>错率 {{ Math.round(exam.wrongRate * 100) }}%</span>
            </div>
            <ArrowRight :size="16" class="row-arrow" />
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.view-teacher-analytics {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.page-header p {
  margin: 6px 0 0;
  color: var(--ink-soft);
  font-size: 14px;
}

.state-shell {
  min-height: 220px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-soft);
}

.state-error {
  color: #b91c1c;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}

.metric-head {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 12px;
}

.metric-value {
  margin: 10px 0 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.ai-summary-card,
.panel-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  padding: 12px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.title-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.title-left h2,
.card-title-row h2 {
  margin: 0;
  font-size: 16px;
}

.summary-text {
  margin: 0;
  color: #334155;
  line-height: 1.6;
}

.topic-list {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-chip {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.split-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  display: flex;
  flex-direction: column;
  gap: 8px;
  line-height: 1.5;
}

.group-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.group-item {
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-item span {
  font-size: 12px;
  color: #475569;
}

.group-item strong {
  font-size: 20px;
  color: #0f172a;
}

.group-item.high { background: rgba(220, 38, 38, 0.1); }
.group-item.mid { background: rgba(245, 158, 11, 0.12); }
.group-item.normal { background: rgba(15, 118, 110, 0.12); }

.group-tip {
  margin: 10px 0 0;
  color: #556278;
  font-size: 13px;
  line-height: 1.5;
}

.exam-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exam-row {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: center;
  text-align: left;
}

.exam-main {
  min-width: 0;
}

.exam-title {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exam-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.exam-side {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #334155;
}

.row-arrow {
  color: #94a3b8;
}

@media (max-width: 900px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .split-grid {
    grid-template-columns: 1fr;
  }

  .group-grid {
    grid-template-columns: 1fr;
  }
}
</style>
