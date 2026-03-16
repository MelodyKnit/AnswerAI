<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Activity, ArrowLeft, BrainCircuit, ShieldAlert, Sparkles, Target, TrendingUp, TriangleAlert, Users } from 'lucide-vue-next'
import { getClassAnalysis, getClassDetail, type TeacherClassAnalysis } from '@/api/teacher'

const route = useRoute()
const router = useRouter()
const classId = Number(route.params.id)

const classDetail = ref<any>(null)
const classAnalysis = ref<TeacherClassAnalysis | null>(null)
const isLoading = ref(true)
const loadingError = ref('')

const riskDistribution = computed(() => classAnalysis.value?.risk_distribution || [])
const scoreDistribution = computed(() => classAnalysis.value?.score_distribution || [])
const weakKnowledgePoints = computed(() => classAnalysis.value?.weak_knowledge_points || [])
const questionTypePerformance = computed(() => classAnalysis.value?.question_type_performance || [])
const examTrend = computed(() => classAnalysis.value?.exam_trend || [])
const focusStudents = computed(() => classAnalysis.value?.focus_students || [])
const studentRisks = computed(() => classAnalysis.value?.student_risks || [])
const aiActions = computed(() => classAnalysis.value?.ai_insight?.actions || [])
const riskBarMax = computed(() => Math.max(1, ...riskDistribution.value.map((item) => Number(item.count || 0))))
const scoreBarMax = computed(() => Math.max(1, ...scoreDistribution.value.map((item) => Number(item.count || 0))))
const weakPointMax = computed(() => Math.max(1, ...weakKnowledgePoints.value.map((item) => Number(item.count || 0))))

const percentText = (value: number) => `${Math.round(Number(value || 0))}%`
const formatScore = (value: number) => Number(value || 0).toFixed(1)
const riskLabel = (value: string) => value === 'high' ? '高危' : value === 'medium' ? '预警' : '稳定'
const riskTone = (value: string) => value === 'high' ? 'danger' : value === 'medium' ? 'warn' : 'safe'

const overview = computed(() => classAnalysis.value?.overview)
const highRiskCount = computed(() => Number(riskDistribution.value.find((item) => item.level === 'high')?.count || 0))
const mediumRiskCount = computed(() => Number(riskDistribution.value.find((item) => item.level === 'medium')?.count || 0))
const lowRiskCount = computed(() => Number(riskDistribution.value.find((item) => item.level === 'low')?.count || 0))
const topWeakPoint = computed(() => weakKnowledgePoints.value[0]?.name || '暂无明显集中薄弱点')
const topWeakType = computed(() => questionTypePerformance.value[0])
const latestTrend = computed(() => examTrend.value[examTrend.value.length - 1] || null)
const classHealthScore = computed(() => {
  if (!overview.value) return 0
  const completion = Number(overview.value.completion_rate || 0)
  const accuracy = Number(overview.value.avg_correct_rate || 0)
  const score = Number(overview.value.avg_score || 0)
  return Math.max(0, Math.min(100, Math.round(score * 0.35 + accuracy * 0.4 + completion * 0.25)))
})
const classHealthLabel = computed(() => {
  if (classHealthScore.value >= 80) return '状态稳定'
  if (classHealthScore.value >= 60) return '需要跟进'
  return '需要重点干预'
})
const classHealthHint = computed(() => {
  if (highRiskCount.value > 0) return `当前有 ${highRiskCount.value} 名高风险学生需要优先跟进`
  if (mediumRiskCount.value > 0) return `当前有 ${mediumRiskCount.value} 名预警学生需要巩固`
  return '当前班级整体风险可控'
})
const summaryBadges = computed(() => {
  const items: string[] = []
  if (overview.value?.exam_count) items.push(`${overview.value.exam_count} 场测验样本`)
  if (topWeakPoint.value) items.push(`薄弱点：${topWeakPoint.value}`)
  if (topWeakType.value) items.push(`高错题型：${topWeakType.value.label}`)
  if (latestTrend.value) items.push(`最近一次提交率 ${percentText(latestTrend.value.submission_rate)}`)
  return items.slice(0, 4)
})
const healthRingStyle = computed(() => {
  const progress = `${classHealthScore.value}%`
  return {
    '--progress': progress,
  }
})
const riskDonutStyle = computed(() => {
  const total = Math.max(1, highRiskCount.value + mediumRiskCount.value + lowRiskCount.value)
  const high = (highRiskCount.value / total) * 100
  const medium = (mediumRiskCount.value / total) * 100
  const low = 100 - high - medium
  return {
    background: `conic-gradient(#d66e63 0 ${high}%, #d8a551 ${high}% ${high + medium}%, #7ca88f ${high + medium}% ${high + medium + low}%, #edf0ee ${high + medium + low}% 100%)`,
  }
})
const scoreSegments = computed(() => {
  const total = Math.max(1, Number(overview.value?.student_count || 0))
  return scoreDistribution.value.map((item) => ({
    ...item,
    width: `${Math.max((Number(item.count || 0) / total) * 100, 6)}%`,
    percent: Math.round((Number(item.count || 0) / total) * 100),
  }))
})
const trendBars = computed(() => {
  const maxScore = Math.max(1, ...examTrend.value.map((item) => Number(item.avg_score || 0)))
  return examTrend.value.map((item) => ({
    ...item,
    scoreHeight: Math.max((Number(item.avg_score || 0) / maxScore) * 100, 12),
    submissionHeight: Math.max(Number(item.submission_rate || 0), 10),
  }))
})
const prioritySignals = computed(() => {
  const rows = [
    {
      title: '班级健康度',
      value: `${classHealthScore.value}`,
      suffix: '/100',
      description: classHealthHint.value,
      tone: classHealthScore.value >= 80 ? 'safe' : classHealthScore.value >= 60 ? 'warn' : 'danger',
    },
    {
      title: '重点薄弱点',
      value: topWeakPoint.value,
      suffix: '',
      description: '建议优先围绕该主题安排短讲评与同类题巩固',
      tone: 'warn',
    },
    {
      title: '重点题型',
      value: topWeakType.value ? `${topWeakType.value.label} ${percentText(topWeakType.value.wrong_rate * 100)}` : '暂无数据',
      suffix: '',
      description: '用于判断是知识理解问题还是题型策略问题',
      tone: 'normal',
    },
  ]
  return rows
})

const fetchData = async () => {
  if (!Number.isFinite(classId) || classId <= 0) {
    router.replace('/app/teacher/classes')
    return
  }
  try {
    isLoading.value = true
    loadingError.value = ''
    const [detailRes, analysisRes] = await Promise.all([getClassDetail(classId), getClassAnalysis(classId)])
    classDetail.value = (detailRes as any).class
    classAnalysis.value = analysisRes || null
  } catch (error: any) {
    console.error('Failed to fetch class analysis', error)
    loadingError.value = error?.message || '班级分析加载失败'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchData)

const goBack = () => {
  router.push(`/app/teacher/classes/${classId}`)
}

const goExamDetail = (examId: number) => {
  router.push(`/app/teacher/exams/${examId}`)
}

const goStudentProfile = (studentId: number) => {
  router.push(`/app/teacher/students/${studentId}`)
}
</script>

<template>
  <div class="view-class-analysis">
    <header class="analysis-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="22" />
      </button>
      <div class="header-copy">
        <p class="eyebrow">AI 班级学习分析</p>
        <h1>{{ classDetail?.name || '班级学习分析' }}</h1>
        <div v-if="classDetail" class="tags">
          <span class="tag">{{ classDetail.grade_name }}</span>
          <span class="tag">{{ classDetail.subject }}</span>
        </div>
      </div>
    </header>

    <div v-if="isLoading" class="state-shell">正在生成分析...</div>
    <div v-else-if="loadingError" class="state-shell state-error">{{ loadingError }}</div>

    <template v-else-if="classAnalysis">
      <section class="analysis-hero">
        <article class="hero-main">
          <div class="hero-topline">
            <span class="hero-kicker">AI 班级学习分析</span>
            <span class="hero-status" :class="riskTone(classHealthScore >= 80 ? 'low' : classHealthScore >= 60 ? 'medium' : 'high')">{{ classHealthLabel }}</span>
          </div>
          <h2 class="hero-title">{{ classAnalysis.ai_insight.summary }}</h2>
          <div v-if="summaryBadges.length" class="summary-badges">
            <span v-for="item in summaryBadges" :key="item" class="summary-badge">{{ item }}</span>
          </div>
        </article>

        <article class="hero-score-card">
          <div class="ring-shell" :style="healthRingStyle" :class="riskTone(classHealthScore >= 80 ? 'low' : classHealthScore >= 60 ? 'medium' : 'high')">
            <div class="ring-core">
              <strong>{{ classHealthScore }}</strong>
              <span>健康度</span>
            </div>
          </div>
          <p class="hero-score-copy">{{ classHealthHint }}</p>
        </article>
      </section>

      <section class="signal-grid">
        <article v-for="item in prioritySignals" :key="item.title" class="signal-card" :class="`tone-${item.tone}`">
          <span class="signal-title">{{ item.title }}</span>
          <div class="signal-value-row">
            <strong class="signal-value">{{ item.value }}</strong>
            <span v-if="item.suffix" class="signal-suffix">{{ item.suffix }}</span>
          </div>
          <p>{{ item.description }}</p>
        </article>
      </section>

      <section class="metric-grid compact-grid">
        <article class="metric-card">
          <div class="metric-head">
            <Users :size="14" />
            <span>班级人数</span>
          </div>
          <strong>{{ classAnalysis.overview.student_count }}</strong>
          <p>当前纳入分析的学生总数</p>
        </article>
        <article class="metric-card">
          <div class="metric-head">
            <Target :size="14" />
            <span>最近测验均分</span>
          </div>
          <strong>{{ formatScore(classAnalysis.overview.avg_score) }}</strong>
          <p>{{ classAnalysis.overview.exam_count }} 场测验样本</p>
        </article>
        <article class="metric-card">
          <div class="metric-head">
            <Activity :size="14" />
            <span>平均正确率</span>
          </div>
          <strong>{{ percentText(classAnalysis.overview.avg_correct_rate) }}</strong>
          <p>反映当前班级整体掌握度</p>
        </article>
        <article class="metric-card">
          <div class="metric-head">
            <TrendingUp :size="14" />
            <span>最近提交率</span>
          </div>
          <strong>{{ percentText(classAnalysis.overview.completion_rate) }}</strong>
          <p>用于识别到课与完成情况</p>
        </article>
      </section>

      <section class="insight-layout">
        <article class="hero-card insight-card">
          <div class="section-head">
            <div class="title-left">
              <Sparkles :size="16" />
              <h2>AI 诊断结论</h2>
            </div>
          </div>
          <p class="summary">{{ classAnalysis.ai_insight.summary }}</p>
          <ul v-if="aiActions.length" class="action-list dense-list">
            <li v-for="(item, idx) in aiActions" :key="`action-${idx}`">{{ item }}</li>
          </ul>
        </article>

        <article class="panel-card insight-side-card">
          <div class="section-head compact">
            <div class="title-left">
              <ShieldAlert :size="16" />
              <h3>风险概览</h3>
            </div>
          </div>
          <div class="risk-overview-visual">
            <div class="risk-donut" :style="riskDonutStyle">
              <div class="risk-donut-core">
                <strong>{{ studentRisks.length }}</strong>
                <span>学生样本</span>
              </div>
            </div>
            <div class="risk-legend-list">
              <div class="risk-legend-item">
                <span class="legend-dot danger"></span>
                <span>高风险</span>
                <strong>{{ highRiskCount }}</strong>
              </div>
              <div class="risk-legend-item">
                <span class="legend-dot warn"></span>
                <span>预警</span>
                <strong>{{ mediumRiskCount }}</strong>
              </div>
              <div class="risk-legend-item">
                <span class="legend-dot safe"></span>
                <span>稳定</span>
                <strong>{{ lowRiskCount }}</strong>
              </div>
            </div>
          </div>
          <div class="risk-pill-row">
            <div class="risk-pill danger">
              <span>高风险</span>
              <strong>{{ highRiskCount }}</strong>
            </div>
            <div class="risk-pill warn">
              <span>预警</span>
              <strong>{{ mediumRiskCount }}</strong>
            </div>
            <div class="risk-pill safe">
              <span>稳定</span>
              <strong>{{ lowRiskCount }}</strong>
            </div>
          </div>
          <div class="mini-divider"></div>
          <div class="mini-summary-list">
            <div class="mini-summary-item">
              <span>最突出知识点</span>
              <strong>{{ topWeakPoint }}</strong>
            </div>
            <div class="mini-summary-item">
              <span>当前高错题型</span>
              <strong>{{ topWeakType?.label || '暂无数据' }}</strong>
            </div>
            <div class="mini-summary-item">
              <span>最近趋势样本</span>
              <strong>{{ latestTrend?.title || '暂无测验记录' }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section class="viz-grid">
        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <Activity :size="16" />
              <h3>核心指标对比</h3>
            </div>
          </div>
          <div class="compare-list">
            <div class="compare-row">
              <div class="compare-label-row">
                <span>平均正确率</span>
                <strong>{{ percentText(classAnalysis.overview.avg_correct_rate) }}</strong>
              </div>
              <div class="compare-track">
                <div class="compare-fill blue" :style="{ width: percentText(classAnalysis.overview.avg_correct_rate) }"></div>
              </div>
            </div>
            <div class="compare-row">
              <div class="compare-label-row">
                <span>最近提交率</span>
                <strong>{{ percentText(classAnalysis.overview.completion_rate) }}</strong>
              </div>
              <div class="compare-track">
                <div class="compare-fill green" :style="{ width: percentText(classAnalysis.overview.completion_rate) }"></div>
              </div>
            </div>
            <div class="compare-row">
              <div class="compare-label-row">
                <span>均分进度</span>
                <strong>{{ formatScore(classAnalysis.overview.avg_score) }}</strong>
              </div>
              <div class="compare-track">
                <div class="compare-fill amber" :style="{ width: `${Math.min(Number(classAnalysis.overview.avg_score || 0), 100)}%` }"></div>
              </div>
            </div>
          </div>
        </article>

        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <Target :size="16" />
              <h3>分数段概览</h3>
            </div>
          </div>
          <div v-if="scoreSegments.length" class="segment-stack">
            <div class="segment-bar">
              <div
                v-for="item in scoreSegments"
                :key="item.range"
                class="segment-block"
                :class="`range-${item.range.replace(/[^0-9a-zA-Z\u4e00-\u9fa5]/g, '')}`"
                :style="{ width: item.width }"
              ></div>
            </div>
            <div class="segment-list">
              <div v-for="item in scoreSegments" :key="`${item.range}-legend`" class="segment-item">
                <span class="segment-dot" :class="`range-${item.range.replace(/[^0-9a-zA-Z\u4e00-\u9fa5]/g, '')}`"></span>
                <span>{{ item.range }}</span>
                <strong>{{ item.count }} 人</strong>
                <span>{{ item.percent }}%</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-copy">暂无分数段分布</div>
        </article>
      </section>

      <section class="panel-grid">
        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <TriangleAlert :size="16" />
              <h3>风险分层</h3>
            </div>
          </div>
          <div class="bar-list">
            <div v-for="item in riskDistribution" :key="item.level" class="bar-row">
              <span class="bar-label">{{ item.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :class="`risk-${item.level}`" :style="{ width: `${(Number(item.count || 0) / riskBarMax) * 100}%` }"></div>
              </div>
              <strong>{{ item.count }}人</strong>
            </div>
          </div>
        </article>

        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <TrendingUp :size="16" />
              <h3>分数段分布</h3>
            </div>
          </div>
          <div class="bar-list">
            <div v-for="item in scoreDistribution" :key="item.range" class="bar-row">
              <span class="bar-label">{{ item.range }}</span>
              <div class="bar-track">
                <div class="bar-fill score-fill" :style="{ width: `${(Number(item.count || 0) / scoreBarMax) * 100}%` }"></div>
              </div>
              <strong>{{ item.count }}人</strong>
            </div>
          </div>
        </article>

        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <BrainCircuit :size="16" />
              <h3>薄弱知识点</h3>
            </div>
          </div>
          <div v-if="weakKnowledgePoints.length" class="bar-list">
            <div v-for="item in weakKnowledgePoints" :key="item.name" class="bar-row vertical">
              <span class="bar-label truncate">{{ item.name }}</span>
              <div class="bar-track">
                <div class="bar-fill point-fill" :style="{ width: `${(Number(item.count || 0) / weakPointMax) * 100}%` }"></div>
              </div>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
          <div v-else class="empty-copy">暂无足够知识点数据</div>
        </article>

        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <BrainCircuit :size="16" />
              <h3>题型表现</h3>
            </div>
          </div>
          <div v-if="questionTypePerformance.length" class="type-list">
            <div v-for="item in questionTypePerformance" :key="item.type" class="type-item">
              <div>
                <strong>{{ item.label }}</strong>
                <p>{{ item.question_count }} 题样本</p>
              </div>
              <span class="type-rate">错率 {{ percentText(item.wrong_rate * 100) }}</span>
            </div>
          </div>
          <div v-else class="empty-copy">暂无题型表现数据</div>
        </article>
      </section>

      <section class="detail-grid">
        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <TrendingUp :size="16" />
              <h3>测验趋势</h3>
            </div>
          </div>
          <div v-if="trendBars.length" class="trend-chart-strip">
            <div v-for="item in trendBars" :key="`${item.exam_id}-bar`" class="trend-chart-col">
              <div class="trend-chart-bars">
                <div class="trend-bar score" :style="{ height: `${item.scoreHeight}%` }"></div>
                <div class="trend-bar submission" :style="{ height: `${item.submissionHeight}%` }"></div>
              </div>
              <span class="trend-chart-label">{{ item.title.slice(0, 4) }}</span>
            </div>
          </div>
          <div v-if="examTrend.length" class="trend-list">
            <button v-for="item in examTrend" :key="item.exam_id" class="trend-row" @click="goExamDetail(item.exam_id)">
              <div class="trend-main">
                <strong>{{ item.title }}</strong>
                <span>{{ item.submitted_count }}/{{ item.student_count }} 人提交</span>
              </div>
              <div class="trend-side">
                <span>均分 {{ formatScore(item.avg_score) }}</span>
                <span>提交率 {{ percentText(item.submission_rate) }}</span>
              </div>
            </button>
          </div>
          <div v-else class="empty-copy">暂无趋势数据</div>
        </article>

        <article class="panel-card">
          <div class="section-head compact">
            <div class="title-left">
              <TriangleAlert :size="16" />
              <h3>重点关注学生</h3>
            </div>
          </div>
          <div v-if="focusStudents.length" class="focus-list">
            <button v-for="item in focusStudents" :key="item.student_id" class="focus-item" @click="goStudentProfile(item.student_id)">
              <div>
                <strong>{{ item.student_name }}</strong>
                <p>{{ riskLabel(item.risk_level) }}</p>
              </div>
              <div class="trend-side">
                <span>{{ formatScore(item.score) }} 分</span>
                <span>正确率 {{ item.correct_rate }}%</span>
              </div>
            </button>
          </div>
          <div v-else class="empty-copy">暂无重点关注对象</div>
        </article>

        <article class="panel-card full-span">
          <div class="section-head compact">
            <div class="title-left">
              <Users :size="16" />
              <h3>学生风险名单</h3>
            </div>
          </div>
          <div v-if="studentRisks.length" class="risk-table">
            <button v-for="item in studentRisks" :key="item.student_id" class="risk-table-row" @click="goStudentProfile(item.student_id)">
              <div class="risk-student-main">
                <strong>{{ item.student_name }}</strong>
                <span>ID {{ item.student_id }}</span>
              </div>
              <span class="risk-tag" :class="riskTone(item.risk_level)">{{ riskLabel(item.risk_level) }}</span>
              <span class="risk-table-score">{{ formatScore(item.score) }} 分</span>
              <span class="risk-table-score">正确率 {{ item.correct_rate }}%</span>
            </button>
          </div>
          <div v-else class="empty-copy">暂无风险名单</div>
        </article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.view-class-analysis {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.icon-button {
  background: none;
  border: none;
  padding: 4px;
  color: var(--ink-soft);
}

.header-copy {
  display: grid;
  gap: 6px;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  color: #628170;
}

.header-copy h1 {
  margin: 0;
  font-size: 21px;
  color: var(--ink);
  line-height: 1.15;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--line);
  color: var(--ink);
  border-radius: 6px;
}

.state-shell,
.empty-copy {
  display: flex;
  justify-content: center;
  padding: 40px 0;
  color: var(--ink-soft);
}

.state-error {
  color: #b64d45;
}

.metric-grid,
.panel-grid,
.signal-grid,
.detail-grid,
.insight-layout,
.analysis-hero {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-card,
.hero-card,
.panel-card,
.signal-card,
.hero-main,
.hero-score-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
  padding: 14px;
}

.analysis-hero {
  grid-template-columns: minmax(0, 1.55fr) minmax(240px, 0.9fr);
}

.hero-main {
  background:
    radial-gradient(circle at top left, rgba(99, 154, 126, 0.12), transparent 35%),
    linear-gradient(165deg, #ffffff 0%, #f3f8f5 100%);
  display: grid;
  gap: 10px;
}

.hero-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.hero-kicker {
  font-size: 12px;
  color: #5c7b6f;
  letter-spacing: 0.04em;
}

.hero-status {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 600;
}

.hero-status.safe,
.risk-tag.safe,
.risk-pill.safe {
  background: #edf7f1;
  color: #3f765b;
}

.hero-status.warn,
.risk-tag.warn,
.risk-pill.warn {
  background: #fff4df;
  color: #9a6a1f;
}

.hero-status.danger,
.risk-tag.danger,
.risk-pill.danger {
  background: #fdeceb;
  color: #ac4c42;
}

.hero-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.75;
  color: #25372f;
  font-weight: 700;
}

.summary-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-badge {
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(85, 126, 108, 0.08);
  color: #486256;
  font-size: 11px;
}

.hero-score-card {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  background: linear-gradient(180deg, #fff 0%, #f7faf8 100%);
}

.ring-shell {
  width: 108px;
  height: 108px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(from 0deg, currentColor 0 var(--progress), rgba(0, 0, 0, 0.06) var(--progress) 100%);
  color: #648675;
  position: relative;
}

.ring-shell::before {
  content: '';
  position: absolute;
  inset: 9px;
  border-radius: 50%;
  background: #fff;
}

.ring-shell.safe {
  color: #5e8a71;
}

.ring-shell.warn {
  color: #d6a454;
}

.ring-shell.danger {
  color: #d66e63;
}

.ring-core {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
}

.ring-core strong {
  font-size: 26px;
  color: var(--ink);
  line-height: 1;
}

.ring-core span,
.hero-score-copy {
  font-size: 12px;
  color: var(--ink-soft);
  text-align: center;
  margin: 0;
}

.signal-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.signal-card {
  display: grid;
  gap: 6px;
  min-height: 102px;
}

.signal-card.tone-danger {
  background: linear-gradient(180deg, #fff 0%, #fff7f6 100%);
}

.signal-card.tone-warn {
  background: linear-gradient(180deg, #fff 0%, #fffaf0 100%);
}

.signal-title {
  font-size: 12px;
  color: var(--ink-soft);
}

.signal-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.signal-value {
  font-size: 18px;
  color: var(--ink);
  line-height: 1.2;
}

.signal-suffix,
.signal-card p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
}

.compact-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: grid;
  gap: 5px;
}

.metric-head {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-soft);
}

.metric-card span,
.metric-card p {
  font-size: 12px;
  color: var(--ink-soft);
  margin: 0;
}

.metric-card strong {
  font-size: 20px;
  color: var(--ink);
  line-height: 1.15;
}

.hero-card {
  background: linear-gradient(160deg, #ffffff 0%, #eef8f4 100%);
}

.insight-layout {
  grid-template-columns: minmax(0, 1.35fr) minmax(260px, 0.75fr);
}

.insight-card {
  padding-bottom: 12px;
}

.insight-side-card {
  display: grid;
  gap: 10px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.compact {
  margin-bottom: 8px;
}

.title-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.title-left h2,
.title-left h3,
.summary,
.action-list {
  margin: 0;
}

.title-left h2 {
  font-size: 16px;
}

.title-left h3 {
  font-size: 14px;
}

.summary {
  font-size: 13px;
  line-height: 1.75;
  color: #355247;
}

.action-list,
.bar-list,
.type-list,
.trend-list,
.focus-list,
.panel-stack,
.risk-pill-row,
.mini-summary-list {
  display: grid;
  gap: 10px;
}

.action-list {
  padding-left: 18px;
  margin-top: 12px;
}

.dense-list {
  gap: 8px;
}

.risk-pill-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.risk-overview-visual {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.risk-donut {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  position: relative;
}

.risk-donut::before {
  content: '';
  position: absolute;
  inset: 10px;
  border-radius: 50%;
  background: #fff;
}

.risk-donut-core {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  z-index: 1;
}

.risk-donut-core strong {
  font-size: 20px;
  color: var(--ink);
}

.risk-donut-core span {
  font-size: 11px;
  color: var(--ink-soft);
}

.risk-legend-list {
  display: grid;
  gap: 7px;
}

.risk-legend-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--ink-soft);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.legend-dot.danger {
  background: #d66e63;
}

.legend-dot.warn {
  background: #d8a551;
}

.legend-dot.safe {
  background: #7ca88f;
}

.risk-pill {
  border-radius: 12px;
  padding: 10px;
  display: grid;
  gap: 4px;
}

.risk-pill span,
.mini-summary-item span {
  font-size: 11px;
}

.risk-pill strong,
.mini-summary-item strong {
  font-size: 18px;
  color: var(--ink);
}

.mini-divider {
  height: 1px;
  background: var(--line);
}

.mini-summary-item {
  display: grid;
  gap: 4px;
}

.viz-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.compare-list,
.segment-stack,
.segment-list {
  display: grid;
  gap: 10px;
}

.compare-row {
  display: grid;
  gap: 6px;
}

.compare-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-soft);
}

.compare-track {
  height: 9px;
  background: #edf0ee;
  border-radius: 999px;
  overflow: hidden;
}

.compare-fill {
  height: 100%;
  border-radius: inherit;
}

.compare-fill.blue {
  background: linear-gradient(90deg, #8db4d7 0%, #5f8fb8 100%);
}

.compare-fill.green {
  background: linear-gradient(90deg, #95c2aa 0%, #66917b 100%);
}

.compare-fill.amber {
  background: linear-gradient(90deg, #f0c77d 0%, #d39f44 100%);
}

.segment-bar {
  display: flex;
  gap: 6px;
  height: 12px;
}

.segment-block {
  height: 100%;
  border-radius: 999px;
  min-width: 10px;
}

.segment-list {
  gap: 8px;
}

.segment-item {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--ink-soft);
}

.segment-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.range-90100 {
  background: #4d8a70;
}

.range-8089 {
  background: #6fa282;
}

.range-7079 {
  background: #9fbf7f;
}

.range-6069 {
  background: #d8b55f;
}

.range-60以下 {
  background: #d66e63;
}

.bar-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}

.bar-row.vertical {
  grid-template-columns: 110px minmax(0, 1fr) auto;
}

.bar-label {
  font-size: 13px;
  color: var(--ink-soft);
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 10px;
  background: #edf0ee;
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: #83ab94;
}

.risk-high {
  background: #d66e63;
}

.risk-medium {
  background: #d8a551;
}

.risk-low,
.point-fill {
  background: #7ca88f;
}

.score-fill {
  background: #6c94be;
}

.type-item,
.trend-row,
.focus-item {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 11px 12px;
  background: #fff;
}

.type-item,
.trend-row,
.focus-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.type-item p,
.trend-main span,
.trend-side span,
.focus-item p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
}

.trend-main,
.trend-side {
  display: grid;
  gap: 4px;
  text-align: left;
}

.trend-side {
  justify-items: end;
}

.type-rate {
  color: #96553d;
  font-weight: 600;
}

.detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.trend-chart-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(44px, 1fr));
  gap: 8px;
  align-items: end;
  min-height: 132px;
  padding: 8px 0 4px;
}

.trend-chart-col {
  display: grid;
  gap: 6px;
  justify-items: center;
}

.trend-chart-bars {
  height: 96px;
  width: 100%;
  display: flex;
  align-items: end;
  justify-content: center;
  gap: 5px;
}

.trend-bar {
  width: 12px;
  border-radius: 999px 999px 4px 4px;
}

.trend-bar.score {
  background: linear-gradient(180deg, #7da88f 0%, #5e8871 100%);
}

.trend-bar.submission {
  background: linear-gradient(180deg, #90b8d7 0%, #678fb0 100%);
}

.trend-chart-label {
  font-size: 11px;
  color: var(--ink-soft);
}

.full-span {
  grid-column: 1 / -1;
}

.risk-table {
  display: grid;
  gap: 8px;
}

.risk-table-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) auto auto auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  text-align: left;
}

.risk-student-main {
  display: grid;
  gap: 4px;
}

.risk-student-main span,
.risk-table-score {
  font-size: 12px;
  color: var(--ink-soft);
}

.risk-tag {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .metric-grid,
  .panel-grid,
  .signal-grid,
  .detail-grid,
  .insight-layout,
  .analysis-hero,
  .compact-grid,
  .viz-grid {
    grid-template-columns: 1fr;
  }

  .trend-row,
  .focus-item,
  .type-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .trend-side {
    justify-items: start;
  }

  .risk-pill-row {
    grid-template-columns: 1fr 1fr 1fr;
  }

  .risk-overview-visual {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .risk-table-row {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }

  .analysis-header {
    gap: 8px;
  }

  .hero-title {
    font-size: 15px;
  }

  .ring-shell {
    width: 96px;
    height: 96px;
  }
}
</style>