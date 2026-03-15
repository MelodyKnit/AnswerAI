<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  BrainCircuit,
  CheckCircle,
  Clock3,
  Pause,
  Play,
  Square,
  Target,
  TrendingUp,
  Users,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { finishExam, getExamDetail, getExamInsights, pauseExam, publishExam } from '@/api/teacher'

use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)

const exam = ref<any>(null)
const insights = ref<any>(null)
const isLoading = ref(true)

const statusText = computed(() => {
  if (!exam.value) return ''
  if (exam.value.status === 'draft') return '草稿'
  if (exam.value.status === 'published') return '进行中'
  return '已结束'
})

const submittedCount = computed(() => Number(insights.value?.progress?.submitted_count || 0))
const targetCount = computed(() => Number(insights.value?.progress?.target_count || 0))

const progressText = computed(() => `${submittedCount.value}/${targetCount.value}`)

const progressPercent = computed(() => {
  const ratio = Number(insights.value?.progress?.completion_rate || 0)
  return Math.max(0, Math.min(100, Math.round(ratio * 100)))
})

const avgDuration = computed(() => Math.round(Number(insights.value?.learning?.avg_duration_minutes || 0)))
const avgScore = computed(() => Math.round(Number(insights.value?.learning?.avg_score || 0) * 10) / 10)
const overallWrongRate = computed(() => {
  const rate = Number(insights.value?.learning?.overall_wrong_rate || 0)
  return Math.max(0, Math.min(100, Math.round(rate * 100)))
})

const topWrongQuestions = computed(() => (insights.value?.top_wrong_questions || []) as Array<any>)
const aiEasyMistakes = computed(() => (insights.value?.ai_summary?.easy_mistakes || []) as string[])
const aiSuggestions = computed(() => (insights.value?.ai_summary?.teaching_suggestions || []) as string[])

const completionPieOption = computed(() => {
  const submitted = submittedCount.value
  const pending = Math.max(0, targetCount.value - submitted)
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: '#556278', fontSize: 12 } },
    series: [
      {
        type: 'pie',
        radius: ['52%', '74%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        label: { show: false },
        data: [
          { value: submitted, name: '已提交', itemStyle: { color: '#0f766e' } },
          { value: pending, name: '未提交', itemStyle: { color: '#d4dbe5' } },
        ],
      },
    ],
  }
})

const wrongRateBarOption = computed(() => {
  const items = topWrongQuestions.value.slice(0, 6)
  const labels = items.map((_, idx) => `Q${idx + 1}`)
  const values = items.map((q) => Math.round(Number(q.wrong_rate || 0) * 100))
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v: number) => `${v}%`,
    },
    grid: { left: 30, right: 16, top: 14, bottom: 26 },
    xAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d4dbe5' } },
      axisLabel: { color: '#556278' },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#556278' },
      splitLine: { lineStyle: { color: '#ecf0f5' } },
    },
    series: [
      {
        type: 'bar',
        barWidth: 18,
        itemStyle: { color: '#ef4444', borderRadius: [8, 8, 0, 0] },
        data: values,
      },
    ],
  }
})

const trendLineOption = computed(() => {
  const items = topWrongQuestions.value.slice(0, 6)
  const labels = items.map((_, idx) => `高错题${idx + 1}`)
  const values = items.map((q) => Math.round(Number(q.wrong_rate || 0) * 100))
  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: number) => `${v}%`,
    },
    grid: { left: 24, right: 16, top: 14, bottom: 24 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: { lineStyle: { color: '#d4dbe5' } },
      axisLabel: { color: '#556278' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#556278' },
      splitLine: { lineStyle: { color: '#ecf0f5' } },
    },
    series: [
      {
        type: 'line',
        data: values,
        smooth: true,
        symbolSize: 8,
        lineStyle: { width: 3, color: '#1d4ed8' },
        itemStyle: { color: '#1d4ed8' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(29, 78, 216, 0.28)' },
              { offset: 1, color: 'rgba(29, 78, 216, 0.04)' },
            ],
          },
        },
      },
    ],
  }
})

const fetchExam = async () => {
  try {
    isLoading.value = true
    const [detailRes, insightRes] = await Promise.all([getExamDetail(examId), getExamInsights(examId)])
    exam.value = (detailRes as any).exam
    exam.value.question_items = (detailRes as any).question_items || []
    insights.value = insightRes
  } catch (error) {
    console.error('Failed to fetch exam', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchExam()
})

const goBack = () => router.back()

const handlePublish = async () => {
  await publishExam(examId)
  await fetchExam()
}

const handlePause = async () => {
  await pauseExam(examId)
  await fetchExam()
}

const handleFinish = async () => {
  await finishExam(examId)
  await fetchExam()
}
</script>

<template>
  <div class="exam-detail-dashboard">
    <header class="page-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="20" />
      </button>
      <div v-if="exam" class="status-pill" :class="`status--${exam.status}`">{{ statusText }}</div>
    </header>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <template v-else-if="exam">
      <section class="hero-card">
        <div class="hero-main">
          <h1 class="exam-title">{{ exam.title }}</h1>
          <p v-if="exam.instructions" class="exam-desc">{{ exam.instructions }}</p>
          <div class="meta-tags">
            <span class="meta-tag">{{ exam.subject || '不限范围' }}</span>
            <span class="meta-tag">{{ exam.duration_minutes }} 分钟</span>
            <span class="meta-tag">{{ exam.total_score }} 分</span>
          </div>
        </div>
        <div class="hero-progress">
          <p class="hero-label">班级完成</p>
          <p class="hero-value">{{ progressText }}</p>
          <p class="hero-percent">{{ progressPercent }}%</p>
        </div>
      </section>

      <section class="kpi-grid">
        <article class="kpi-card">
          <div class="kpi-head">
            <Clock3 :size="16" class="kpi-icon clock" />
            <span>平均做题时长</span>
          </div>
          <p class="kpi-value">{{ avgDuration }} 分钟</p>
        </article>
        <article class="kpi-card">
          <div class="kpi-head">
            <Target :size="16" class="kpi-icon target" />
            <span>平均得分</span>
          </div>
          <p class="kpi-value">{{ avgScore }} 分</p>
        </article>
        <article class="kpi-card">
          <div class="kpi-head">
            <AlertTriangle :size="16" class="kpi-icon alert" />
            <span>整体出错率</span>
          </div>
          <p class="kpi-value">{{ overallWrongRate }}%</p>
        </article>
        <article class="kpi-card">
          <div class="kpi-head">
            <Users :size="16" class="kpi-icon users" />
            <span>参与人数</span>
          </div>
          <p class="kpi-value">{{ progressText }}</p>
        </article>
      </section>

      <section class="charts-grid">
        <article class="chart-card">
          <div class="chart-title-row">
            <h2>提交分布</h2>
            <span class="chip chip-green">饼图</span>
          </div>
          <VChart class="chart" :option="completionPieOption" autoresize />
        </article>

        <article class="chart-card">
          <div class="chart-title-row">
            <h2>高错题错误率排行</h2>
            <span class="chip chip-red">柱形图</span>
          </div>
          <VChart class="chart" :option="wrongRateBarOption" autoresize />
        </article>

        <article class="chart-card chart-card-wide">
          <div class="chart-title-row">
            <h2>高错题趋势强度</h2>
            <span class="chip chip-blue">折线图</span>
          </div>
          <VChart class="chart chart-line" :option="trendLineOption" autoresize />
        </article>
      </section>

      <section class="section-split">
        <article class="panel">
          <div class="panel-title-row">
            <h2>高错题分析</h2>
            <TrendingUp :size="16" class="panel-icon" />
          </div>
          <div v-if="topWrongQuestions.length" class="wrong-list">
            <div v-for="(item, idx) in topWrongQuestions" :key="item.question_id" class="wrong-item">
              <div class="wrong-top">
                <span class="wrong-rank">#{{ idx + 1 }}</span>
                <span class="wrong-rate">{{ Math.round((item.wrong_rate || 0) * 100) }}%</span>
              </div>
              <p class="wrong-stem">{{ item.stem }}</p>
              <p class="wrong-meta">{{ item.answer_count }} 人作答，平均 {{ Math.round((item.avg_spent_seconds || 0) / 60) }} 分钟</p>
            </div>
          </div>
          <div v-else class="empty-state">暂无可分析的错题数据</div>
        </article>

        <article class="panel">
          <div class="panel-title-row">
            <h2>AI 学情解读</h2>
            <BrainCircuit :size="16" class="panel-icon" />
          </div>
          <div class="ai-columns">
            <div class="ai-box">
              <h3>易错点</h3>
              <ul>
                <li v-for="(item, idx) in aiEasyMistakes" :key="`mistake-${idx}`">{{ item }}</li>
              </ul>
            </div>
            <div class="ai-box">
              <h3>教学建议</h3>
              <ul>
                <li v-for="(item, idx) in aiSuggestions" :key="`suggestion-${idx}`">{{ item }}</li>
              </ul>
            </div>
          </div>
        </article>
      </section>

      <section class="action-toolbar">
        <button class="action-btn action-primary" v-if="exam.status === 'draft'" @click="handlePublish">
          <Play :size="16" />
          发布考试
        </button>
        <button class="action-btn action-warn" v-if="exam.status === 'published'" @click="handlePause">
          <Pause :size="16" />
          暂停考试
        </button>
        <button class="action-btn action-danger" v-if="exam.status === 'published'" @click="handleFinish">
          <Square :size="16" />
          结束考试
        </button>
        <button class="action-btn" v-if="exam.status === 'finished'">
          <CheckCircle :size="16" />
          进入阅卷
        </button>
      </section>

      <section class="questions-panel">
        <div class="panel-title-row">
          <h2>试题列表</h2>
          <span class="q-count">共 {{ exam.question_items ? exam.question_items.length : 0 }} 题</span>
        </div>
        <div class="questions-list" v-if="exam.question_items && exam.question_items.length > 0">
          <div class="q-item" v-for="(q, idx) in exam.question_items" :key="q.question_id">
            <span class="q-index">{{ Number(idx) + 1 }}</span>
            <p class="q-stem">{{ q.question?.stem || '题干加载失败' }}</p>
            <span class="q-score">{{ q.score || 0 }}分</span>
          </div>
        </div>
        <div class="empty-state" v-else>试卷目前还是空的</div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.exam-detail-dashboard {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background:
    radial-gradient(circle at 85% -20%, rgba(29, 78, 216, 0.14), transparent 35%),
    radial-gradient(circle at 0% 30%, rgba(15, 118, 110, 0.1), transparent 38%);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.icon-button {
  border: none;
  background: transparent;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  margin-left: -6px;
}

.status-pill {
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  background: #fff;
}

.status--published {
  color: #0f766e;
  border-color: #0f766e;
  background: rgba(15, 118, 110, 0.1);
}

.status--finished {
  color: #334155;
  background: rgba(148, 163, 184, 0.12);
}

.loading-state,
.empty-state {
  text-align: center;
  color: var(--ink-soft);
  padding: 20px 0;
}

.hero-card {
  border: 1px solid #dfe6ef;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(150deg, #ffffff, #f8fbff);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}

.hero-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exam-title {
  margin: 0;
  font-size: 31px;
  line-height: 1.08;
  letter-spacing: -0.03em;
}

.exam-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: #556278;
}

.meta-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #edf2f8;
  color: #334155;
}

.hero-progress {
  min-width: 84px;
  padding: 8px 10px;
  border-radius: 12px;
  background: #f3f8fb;
  text-align: right;
}

.hero-label {
  margin: 0;
  font-size: 11px;
  color: #64748b;
}

.hero-value {
  margin: 4px 0 0;
  font-size: 25px;
  font-weight: 700;
  line-height: 1;
  color: #0f172a;
}

.hero-percent {
  margin: 3px 0 0;
  font-size: 12px;
  color: #0f766e;
  font-weight: 600;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.kpi-card {
  background: #fff;
  border: 1px solid #e4eaf2;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kpi-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #64748b;
}

.kpi-value {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.kpi-icon.clock { color: #1d4ed8; }
.kpi-icon.target { color: #16a34a; }
.kpi-icon.alert { color: #dc2626; }
.kpi-icon.users { color: #0f766e; }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.chart-card {
  background: #fff;
  border: 1px solid #e4eaf2;
  border-radius: 14px;
  padding: 10px;
  min-height: 238px;
  display: flex;
  flex-direction: column;
}

.chart-card-wide {
  grid-column: span 2;
}

.chart-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.chart-title-row h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.chip {
  font-size: 10px;
  border-radius: 999px;
  padding: 3px 7px;
  font-weight: 600;
}

.chip-green {
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
}

.chip-red {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.chip-blue {
  background: rgba(29, 78, 216, 0.12);
  color: #1d4ed8;
}

.chart {
  width: 100%;
  height: 190px;
}

.chart-line {
  height: 210px;
}

.section-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.panel,
.questions-panel {
  border: 1px solid #e4eaf2;
  border-radius: 14px;
  background: #fff;
  padding: 12px;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-title-row h2 {
  margin: 0;
  font-size: 16px;
}

.panel-icon {
  color: #64748b;
}

.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wrong-item {
  border: 1px solid #edf1f6;
  border-radius: 10px;
  padding: 8px;
  background: #fbfdff;
}

.wrong-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.wrong-rank {
  color: #b91c1c;
  font-weight: 700;
}

.wrong-rate {
  color: #ef4444;
  font-weight: 600;
}

.wrong-stem {
  margin: 0;
  font-size: 13px;
  color: #0f172a;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.wrong-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.ai-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.ai-box {
  border: 1px solid #edf1f6;
  border-radius: 10px;
  padding: 8px;
  background: #fbfdff;
}

.ai-box h3 {
  margin: 0 0 6px;
  font-size: 13px;
}

.ai-box ul {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: #556278;
}

.action-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.action-btn {
  border: 1px solid #d5deea;
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.action-primary {
  border-color: #0f766e;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.08);
}

.action-warn {
  border-color: #d97706;
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
}

.action-danger {
  border-color: #dc2626;
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.12);
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.q-count {
  font-size: 12px;
  color: #64748b;
}

.q-item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: 8px;
  border: 1px solid #edf1f6;
  border-radius: 10px;
  background: #fbfdff;
  padding: 9px;
  align-items: start;
}

.q-index {
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 50%;
  font-size: 11px;
  background: #e8eef7;
  color: #334155;
}

.q-stem {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: #0f172a;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.q-score {
  font-size: 12px;
  color: #475569;
  white-space: nowrap;
}

@media (max-width: 1024px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .section-split {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-progress {
    text-align: left;
    min-width: 0;
  }

  .exam-title {
    font-size: 26px;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .chart-card-wide {
    grid-column: auto;
  }

  .ai-columns {
    grid-template-columns: 1fr;
  }
}
</style>
