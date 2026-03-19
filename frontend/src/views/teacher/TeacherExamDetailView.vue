<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  BrainCircuit,
  CalendarRange,
  CheckCircle,
  Clock3,
  Pause,
  Play,
  Save,
  Settings2,
  Square,
  Target,
  TrendingUp,
  Users,
  X,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { finishExam, getClasses, getExamDetail, getExamInsights, pauseExam, publishExam, updateExam } from '@/api/teacher'

use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)

const exam = ref<any>(null)
const insights = ref<any>(null)
const isLoading = ref(true)
const actionLoading = ref(false)
const actionError = ref('')
const classBindingLoading = ref(false)
const scheduleLoading = ref(false)
const scheduleError = ref('')
const scheduleMessage = ref('')
const allClasses = ref<Array<{ id: number, name: string }>>([])
const selectedClassIds = ref<number[]>([])
const showSettingsPanel = ref(false)
const scheduleForm = ref({
  start_time: '',
  end_time: '',
})
type MetricModalKey = 'duration' | 'score' | 'wrongRate' | 'participants'
const metricModalVisible = ref(false)
const activeMetric = ref<MetricModalKey>('score')

const boundClassCount = computed(() => {
  return Array.isArray(exam.value?.class_ids) ? exam.value.class_ids.length : 0
})

const canPublishExam = computed(() => {
  if (!exam.value) return false
  if (exam.value.status !== 'draft') return false
  if (boundClassCount.value <= 0) return false
  if (Number(exam.value?.question_count || 0) <= 0) return false
  return true
})

const publishBlockedReason = computed(() => {
  if (!exam.value || exam.value.status !== 'draft') return ''
  if (boundClassCount.value <= 0) return '请先为考试绑定至少一个班级后再发布。'
  if (Number(exam.value?.question_count || 0) <= 0) return '请先添加至少一道试题后再发布。'
  return ''
})

const parseServerTime = (value: string) => {
  if (!value) return Number.NaN
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`).getTime()
}

const formatDateTimeLocal = (value: string) => {
  const timestamp = parseServerTime(value)
  if (Number.isNaN(timestamp)) return ''
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  const hours = `${date.getHours()}`.padStart(2, '0')
  const minutes = `${date.getMinutes()}`.padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

const toIsoFromLocal = (value: string) => {
  const date = new Date(value)
  return date.toISOString()
}

const effectiveStatus = computed(() => {
  if (!exam.value) return 'draft'
  const status = String(exam.value.status || '')
  if (status === 'draft' || status === 'finished') return status
  if (status === 'published') {
    const end = parseServerTime(String(exam.value.end_time || ''))
    if (!Number.isNaN(end) && Date.now() > end) return 'expired'
    return 'published'
  }
  return 'draft'
})

const statusText = computed(() => {
  if (!exam.value) return ''
  if (effectiveStatus.value === 'draft') return '草稿'
  if (effectiveStatus.value === 'published') return '进行中'
  if (effectiveStatus.value === 'expired') return '已超时(待结束)'
  return '已结束'
})

const examKnowledgePointsText = computed(() => {
  if (!exam.value) return '未分类知识点'
  return String(exam.value?.subject || '未分类知识点')
})

const canEditSchedule = computed(() => Boolean(exam.value) && effectiveStatus.value !== 'finished')

const canEditStartTime = computed(() => Boolean(exam.value) && exam.value.status === 'draft')

const scheduleRangeText = computed(() => {
  if (!scheduleForm.value.start_time || !scheduleForm.value.end_time) return '请设置考试开放时间范围'
  const start = new Date(scheduleForm.value.start_time)
  const end = new Date(scheduleForm.value.end_time)
  const diffMinutes = Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000))
  if (diffMinutes < 60) return `当前开放 ${diffMinutes} 分钟`
  if (diffMinutes < 24 * 60) return `当前开放 ${Math.round(diffMinutes / 60)} 小时`
  return `当前开放 ${Math.round((diffMinutes / 60 / 24) * 10) / 10} 天`
})

const scheduleValidationError = computed(() => {
  if (!scheduleForm.value.start_time || !scheduleForm.value.end_time) return '请完整设置开始时间和结束时间'
  const start = new Date(scheduleForm.value.start_time)
  const end = new Date(scheduleForm.value.end_time)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '时间格式无效，请重新选择'
  if (end.getTime() <= start.getTime()) return '结束时间必须晚于开始时间'
  if (exam.value?.status !== 'draft' && scheduleForm.value.start_time !== formatDateTimeLocal(String(exam.value?.start_time || ''))) {
    return '已发布考试只允许调整结束时间，不允许修改开始时间'
  }
  return ''
})

const isScheduleDirty = computed(() => {
  if (!exam.value) return false
  return (
    scheduleForm.value.start_time !== formatDateTimeLocal(String(exam.value.start_time || ''))
    || scheduleForm.value.end_time !== formatDateTimeLocal(String(exam.value.end_time || ''))
  )
})

const submittedCount = computed(() => Number(insights.value?.progress?.submitted_count || 0))
const startedCount = computed(() => Number(insights.value?.progress?.started_count ?? submittedCount.value))
const targetCount = computed(() => Number(insights.value?.progress?.target_count || 0))

const progressText = computed(() => `${submittedCount.value}/${targetCount.value}`)
const participantText = computed(() => `${startedCount.value}/${targetCount.value}`)

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
const metricDistributions = computed(() => (insights.value?.metric_distributions || {}) as Record<string, Array<{ range: string, count: number }>>)
const durationDistribution = computed(() => metricDistributions.value.duration_minutes || [])
const scoreDistribution = computed(() => metricDistributions.value.score || [])
const wrongRateDistribution = computed(() => metricDistributions.value.wrong_rate || [])
const startedStudents = computed(() => (insights.value?.participants?.started || []) as Array<any>)
const notStartedStudents = computed(() => (insights.value?.participants?.not_started || []) as Array<any>)

const metricModalTitle = computed(() => {
  if (activeMetric.value === 'duration') return '平均做题时长分布'
  if (activeMetric.value === 'score') return '平均得分分布'
  if (activeMetric.value === 'wrongRate') return '整体出错率分布'
  return '参与学生明细'
})

const openMetricModal = (metric: MetricModalKey) => {
  activeMetric.value = metric
  metricModalVisible.value = true
}

const closeMetricModal = () => {
  metricModalVisible.value = false
}

const buildDistributionBarOption = (items: Array<{ range: string, count: number }>, color: string) => {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: Array<{ axisValue: string, value: number }>) => {
        const first = params?.[0]
        if (!first) return ''
        return `${first.axisValue}<br/>人数 ${first.value}`
      },
    },
    grid: { left: 28, right: 16, top: 12, bottom: 28 },
    xAxis: {
      type: 'category',
      data: items.map((item) => item.range),
      axisLine: { lineStyle: { color: '#d4dbe5' } },
      axisLabel: { color: '#556278', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#556278' },
      splitLine: { lineStyle: { color: '#ecf0f5' } },
    },
    series: [
      {
        type: 'bar',
        data: items.map((item) => Number(item.count || 0)),
        itemStyle: { color, borderRadius: [8, 8, 0, 0] },
        barMaxWidth: 30,
      },
    ],
  }
}

const durationDistOption = computed(() => buildDistributionBarOption(durationDistribution.value, '#1d4ed8'))
const scoreDistOption = computed(() => buildDistributionBarOption(scoreDistribution.value, '#16a34a'))

const wrongRateDistOption = computed(() => {
  const items = wrongRateDistribution.value
  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: { name: string, value: number }) => `${params.name}<br/>人数 ${params.value}`,
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      textStyle: { color: '#556278', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '42%'],
        label: { show: false },
        data: items.map((item, idx) => ({
          name: item.range,
          value: Number(item.count || 0),
          itemStyle: {
            color: ['#0f766e', '#14b8a6', '#f59e0b', '#fb7185', '#ef4444'][idx % 5],
          },
        })),
      },
    ],
  }
})

const activeMetricOption = computed(() => {
  if (activeMetric.value === 'duration') return durationDistOption.value
  if (activeMetric.value === 'score') return scoreDistOption.value
  return wrongRateDistOption.value
})

const metricHasChartData = computed(() => {
  if (activeMetric.value === 'duration') return durationDistribution.value.length > 0
  if (activeMetric.value === 'score') return scoreDistribution.value.length > 0
  if (activeMetric.value === 'wrongRate') return wrongRateDistribution.value.length > 0
  return false
})

const getParticipantStatusClass = (status: string) => {
  if (status === 'reviewed') return 'reviewed'
  if (status === 'submitted' || status === 'completed') return 'submitted'
  return 'progress'
}

const getQuestionAxisLabel = (item: any, index: number) => {
  const orderNo = Number(item?.order_no)
  if (Number.isFinite(orderNo) && orderNo > 0) {
    return `第${orderNo}题`
  }
  return `第${index + 1}题`
}

const getQuestionShortStem = (stem: string) => {
  const text = String(stem || '').replace(/\s+/g, ' ').trim()
  if (!text) return '题干暂不可用'
  return text.length > 22 ? `${text.slice(0, 22)}...` : text
}

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
  const labels = items.map((item, idx) => getQuestionAxisLabel(item, idx))
  const values = items.map((q) => Math.round(Number(q.wrong_rate || 0) * 100))
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any[]) => {
        const first = params?.[0]
        const idx = Number(first?.dataIndex ?? -1)
        const q = idx >= 0 ? items[idx] : null
        const title = idx >= 0 ? getQuestionAxisLabel(q, idx) : '题目'
        const stem = q ? getQuestionShortStem(String(q.stem || '')) : ''
        const value = Number(first?.value ?? 0)
        return `${title}<br/>${stem}<br/>错误率 ${value}%`
      },
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
  const labels = items.map((item, idx) => getQuestionAxisLabel(item, idx))
  const values = items.map((q) => Math.round(Number(q.wrong_rate || 0) * 100))
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const first = params?.[0]
        const idx = Number(first?.dataIndex ?? -1)
        const q = idx >= 0 ? items[idx] : null
        const title = idx >= 0 ? getQuestionAxisLabel(q, idx) : '题目'
        const stem = q ? getQuestionShortStem(String(q.stem || '')) : ''
        const value = Number(first?.value ?? 0)
        return `${title}<br/>${stem}<br/>错误率 ${value}%`
      },
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
    exam.value.class_ids = (detailRes as any).classes?.map((item: any) => item.id) || []
    selectedClassIds.value = [...exam.value.class_ids]
    scheduleForm.value = {
      start_time: formatDateTimeLocal(String(exam.value.start_time || '')),
      end_time: formatDateTimeLocal(String(exam.value.end_time || '')),
    }
    insights.value = insightRes
  } catch (error) {
    console.error('Failed to fetch exam', error)
  } finally {
    isLoading.value = false
  }
}

const fetchClasses = async () => {
  try {
    const res = await getClasses({ page: 1, page_size: 100 })
    allClasses.value = ((res as any)?.items || []).map((item: any) => ({ id: Number(item.id), name: String(item.name || '未命名班级') }))
  } catch (error) {
    console.error('Failed to fetch classes', error)
    actionError.value = '班级列表加载失败，请稍后重试'
  }
}

onMounted(() => {
  fetchExam()
  fetchClasses()
})

const goBack = () => router.back()

const goEditDraft = () => {
  if (!exam.value || String(exam.value.status || '') !== 'draft') return
  router.push(`/app/teacher/exams/create?exam_id=${exam.value.id}`)
}

const openSettingsPanel = () => {
  showSettingsPanel.value = true
}

const closeSettingsPanel = () => {
  showSettingsPanel.value = false
}

const handlePublish = async () => {
  if (!canPublishExam.value) {
    actionError.value = publishBlockedReason.value || '当前条件不满足，无法发布考试'
    return
  }
  if (actionLoading.value) return
  actionLoading.value = true
  actionError.value = ''
  try {
    await publishExam(examId)
    await fetchExam()
  } catch (error: any) {
    actionError.value = error?.message || '发布考试失败，请稍后重试'
  } finally {
    actionLoading.value = false
  }
}

const handlePause = async () => {
  if (actionLoading.value) return
  actionLoading.value = true
  actionError.value = ''
  try {
    await pauseExam(examId)
    await fetchExam()
  } catch (error: any) {
    actionError.value = error?.message || '暂停考试失败，请稍后重试'
  } finally {
    actionLoading.value = false
  }
}

const handleFinish = async () => {
  if (actionLoading.value) return
  actionLoading.value = true
  actionError.value = ''
  try {
    await finishExam(examId)
    await fetchExam()
  } catch (error: any) {
    actionError.value = error?.message || '结束考试失败，请稍后重试'
  } finally {
    actionLoading.value = false
  }
}

const handleSaveClassBinding = async () => {
  if (!exam.value || classBindingLoading.value) return
  classBindingLoading.value = true
  actionError.value = ''
  try {
    await updateExam({ exam_id: examId, class_ids: selectedClassIds.value })
    await fetchExam()
  } catch (error: any) {
    actionError.value = error?.message || '保存班级绑定失败，请稍后重试'
  } finally {
    classBindingLoading.value = false
  }
}

const handleSaveSchedule = async () => {
  if (!exam.value || scheduleLoading.value || !canEditSchedule.value) return
  if (scheduleValidationError.value) {
    scheduleError.value = scheduleValidationError.value
    scheduleMessage.value = ''
    return
  }

  scheduleLoading.value = true
  scheduleError.value = ''
  scheduleMessage.value = ''
  try {
    await updateExam({
      exam_id: examId,
      start_time: toIsoFromLocal(scheduleForm.value.start_time),
      end_time: toIsoFromLocal(scheduleForm.value.end_time),
    })
    await fetchExam()
    scheduleMessage.value = '考试时间已更新'
  } catch (error: any) {
    scheduleError.value = error?.message || '保存考试时间失败，请稍后重试'
  } finally {
    scheduleLoading.value = false
  }
}
</script>

<template>
  <div class="exam-detail-dashboard">
    <header class="page-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="20" />
      </button>
      <div class="header-right" v-if="exam">
        <div class="status-pill" :class="`status--${effectiveStatus}`">{{ statusText }}</div>
        <button
          v-if="exam.status === 'draft'"
          class="setting-trigger setting-trigger--edit"
          @click="goEditDraft"
        >
          继续编辑
        </button>
        <button class="setting-trigger" @click="openSettingsPanel">
          <Settings2 :size="15" />
          设置
        </button>
      </div>
    </header>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <template v-else-if="exam">
      <section class="hero-card">
        <div class="hero-main">
          <h1 class="exam-title">{{ exam.title }}</h1>
          <p v-if="exam.instructions" class="exam-desc">{{ exam.instructions }}</p>
          <div class="meta-tags">
            <span class="meta-tag">{{ examKnowledgePointsText }}</span>
            <span class="meta-tag">{{ exam.duration_minutes }} 分钟</span>
            <span class="meta-tag">{{ exam.total_score }} 分</span>
            <span class="meta-tag">开始 {{ new Date(parseServerTime(String(exam.start_time || ''))).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
            <span class="meta-tag">结束 {{ new Date(parseServerTime(String(exam.end_time || ''))).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
        </div>
        <div class="hero-progress">
          <p class="hero-label">班级完成</p>
          <p class="hero-value">{{ progressText }}</p>
          <p class="hero-percent">{{ progressPercent }}%</p>
        </div>
      </section>

      <section class="kpi-grid">
        <article class="kpi-card kpi-card--interactive" role="button" tabindex="0" @click="openMetricModal('duration')" @keydown.enter="openMetricModal('duration')">
          <div class="kpi-head">
            <Clock3 :size="16" class="kpi-icon clock" />
            <span>平均做题时长</span>
          </div>
          <p class="kpi-value">{{ avgDuration }} 分钟</p>
          <p class="kpi-tip">点击查看分布</p>
        </article>
        <article class="kpi-card kpi-card--interactive" role="button" tabindex="0" @click="openMetricModal('score')" @keydown.enter="openMetricModal('score')">
          <div class="kpi-head">
            <Target :size="16" class="kpi-icon target" />
            <span>平均得分</span>
          </div>
          <p class="kpi-value">{{ avgScore }} 分</p>
          <p class="kpi-tip">点击查看分布</p>
        </article>
        <article class="kpi-card kpi-card--interactive" role="button" tabindex="0" @click="openMetricModal('wrongRate')" @keydown.enter="openMetricModal('wrongRate')">
          <div class="kpi-head">
            <AlertTriangle :size="16" class="kpi-icon alert" />
            <span>整体出错率</span>
          </div>
          <p class="kpi-value">{{ overallWrongRate }}%</p>
          <p class="kpi-tip">点击查看分布</p>
        </article>
        <article class="kpi-card kpi-card--interactive" role="button" tabindex="0" @click="openMetricModal('participants')" @keydown.enter="openMetricModal('participants')">
          <div class="kpi-head">
            <Users :size="16" class="kpi-icon users" />
            <span>参与人数</span>
          </div>
          <p class="kpi-value">{{ participantText }}</p>
          <p class="kpi-tip">点击查看名单</p>
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

      <div v-if="showSettingsPanel" class="settings-modal" @click.self="closeSettingsPanel">
        <div class="settings-modal-card">
          <div class="settings-modal-header">
            <div class="settings-modal-title">
              <Settings2 :size="16" />
              <h2>考试设置</h2>
            </div>
            <button class="icon-button" @click="closeSettingsPanel" aria-label="关闭设置">
              <X :size="18" />
            </button>
          </div>

          <section class="action-toolbar">
            <button
              class="action-btn action-primary"
              :disabled="actionLoading || !canPublishExam"
              :title="publishBlockedReason || '发布考试'"
              v-if="exam.status === 'draft'"
              @click="handlePublish"
            >
              <Play :size="16" />
              发布考试
            </button>
            <button class="action-btn action-warn" :disabled="actionLoading" v-if="exam.status === 'published'" @click="handlePause">
              <Pause :size="16" />
              暂停考试
            </button>
            <button class="action-btn action-danger" :disabled="actionLoading" v-if="effectiveStatus === 'published' || effectiveStatus === 'expired'" @click="handleFinish">
              <Square :size="16" />
              {{ effectiveStatus === 'expired' ? '结束并归档' : '结束考试' }}
            </button>
            <button class="action-btn" v-if="effectiveStatus === 'finished'">
              <CheckCircle :size="16" />
              进入阅卷
            </button>
          </section>

          <p v-if="exam.status === 'draft'" class="action-hint">
            当前已绑定班级：{{ boundClassCount }} 个，试题数：{{ exam.question_count || 0 }} 题
          </p>

          <p v-if="effectiveStatus === 'expired'" class="action-hint action-hint--warning">
            该考试已超过截止时间，但状态尚未归档，请点击“结束并归档”后再进行删除等操作。
          </p>

          <p v-if="actionError" class="action-error">{{ actionError }}</p>

          <section class="schedule-panel">
            <div class="panel-title-row schedule-header">
              <div class="schedule-title-wrap">
                <h2>考试时间设置</h2>
                <CalendarRange :size="16" class="panel-icon" />
              </div>
              <span class="q-count">{{ scheduleRangeText }}</span>
            </div>
            <p class="class-bind-tip">
              <template v-if="exam.status === 'draft'">草稿状态下可调整开始和结束时间；发布后只允许调整结束时间。</template>
              <template v-else-if="effectiveStatus === 'finished'">考试已结束，时间窗口已锁定。</template>
              <template v-else>当前考试已发布，可根据需要延长或缩短结束时间。</template>
            </p>
            <div class="schedule-grid">
              <label class="schedule-field">
                <span>开始时间</span>
                <input v-model="scheduleForm.start_time" type="datetime-local" class="schedule-input" :disabled="scheduleLoading || !canEditStartTime" />
              </label>
              <label class="schedule-field">
                <span>结束时间</span>
                <input v-model="scheduleForm.end_time" type="datetime-local" class="schedule-input" :disabled="scheduleLoading || !canEditSchedule" />
              </label>
            </div>
            <p v-if="scheduleValidationError" class="action-hint action-hint--warning">{{ scheduleValidationError }}</p>
            <p v-if="scheduleError" class="action-error">{{ scheduleError }}</p>
            <p v-if="scheduleMessage" class="schedule-success">{{ scheduleMessage }}</p>
            <div class="class-bind-actions">
              <button class="action-btn action-primary" :disabled="scheduleLoading || !isScheduleDirty || !!scheduleValidationError || !canEditSchedule" @click="handleSaveSchedule">
                <Save :size="16" />
                {{ scheduleLoading ? '保存中...' : '保存时间' }}
              </button>
            </div>
          </section>

          <section class="class-bind-panel">
            <div class="panel-title-row class-bind-header">
              <h2>发布班级设置</h2>
              <span class="q-count">已选 {{ selectedClassIds.length }} 个</span>
            </div>
            <p class="class-bind-tip">请勾选本场测验要发布到的班级，保存后再发布考试。</p>
            <div class="class-bind-list" v-if="allClasses.length">
              <label v-for="item in allClasses" :key="item.id" class="class-bind-item">
                <input type="checkbox" :value="item.id" v-model="selectedClassIds" :disabled="classBindingLoading" />
                <span>{{ item.name }}</span>
              </label>
            </div>
            <div class="empty-state" v-else>暂无可绑定班级，请先在班级管理中创建班级。</div>
            <div class="class-bind-actions">
              <button class="action-btn" :disabled="classBindingLoading" @click="selectedClassIds = [...(exam?.class_ids || [])]">重置</button>
              <button class="action-btn action-primary" :disabled="classBindingLoading" @click="handleSaveClassBinding">
                {{ classBindingLoading ? '保存中...' : '保存班级绑定' }}
              </button>
            </div>
          </section>
        </div>
      </div>

      <div v-if="metricModalVisible" class="metric-modal" @click.self="closeMetricModal">
        <div class="metric-modal-card">
          <div class="metric-modal-header">
            <h3>{{ metricModalTitle }}</h3>
            <button class="icon-button" @click="closeMetricModal" aria-label="关闭统计弹层">
              <X :size="18" />
            </button>
          </div>

          <template v-if="activeMetric === 'participants'">
            <div class="participant-summary">
              <span>已参与 {{ startedStudents.length }} 人</span>
              <span>未参与 {{ notStartedStudents.length }} 人</span>
            </div>
            <div class="participant-grid">
              <section class="participant-panel">
                <h4>已参与</h4>
                <div v-if="startedStudents.length" class="participant-list">
                  <article v-for="item in startedStudents" :key="`started-${item.student_id}`" class="participant-item">
                    <div>
                      <p class="participant-name">{{ item.student_name }}</p>
                      <p class="participant-class">{{ item.class_name || '未分班' }}</p>
                    </div>
                    <span class="participant-status" :class="`status-${getParticipantStatusClass(item.status)}`">{{ item.status_label || '已参与' }}</span>
                  </article>
                </div>
                <div v-else class="empty-state">暂无参与记录</div>
              </section>

              <section class="participant-panel">
                <h4>未参与</h4>
                <div v-if="notStartedStudents.length" class="participant-list">
                  <article v-for="item in notStartedStudents" :key="`pending-${item.student_id}`" class="participant-item">
                    <div>
                      <p class="participant-name">{{ item.student_name }}</p>
                      <p class="participant-class">{{ item.class_name || '未分班' }}</p>
                    </div>
                    <span class="participant-status status-pending">未参与</span>
                  </article>
                </div>
                <div v-else class="empty-state">全部学生已参与</div>
              </section>
            </div>
          </template>

          <template v-else>
            <div v-if="metricHasChartData" class="metric-chart-wrap">
              <VChart class="metric-chart" :option="activeMetricOption" autoresize />
            </div>
            <div v-else class="empty-state">当前暂无可视化数据</div>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.exam-detail-dashboard {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: -24px -16px 0;
  padding: calc(10px + 24px) 16px calc(18px + env(safe-area-inset-bottom));
  min-height: 100dvh;
  background:
    linear-gradient(180deg, #eef3f8 0%, #edf2f7 58%, #ebf0f6 100%);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.setting-trigger {
  border: 1px solid #d7e0ea;
  background: #fff;
  color: #334155;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.setting-trigger--edit {
  border-color: #9fd3bc;
  background: rgba(15, 118, 110, 0.08);
  color: #0f766e;
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

.status--expired {
  color: #b45309;
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
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

.kpi-card--interactive {
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.kpi-card--interactive:hover,
.kpi-card--interactive:focus-visible {
  transform: translateY(-1px);
  border-color: #c8d6e5;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
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

.kpi-tip {
  margin: 0;
  font-size: 11px;
  color: #64748b;
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

.chart-title-row h2 + .chip {
  letter-spacing: 0.01em;
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

.action-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.action-error {
  margin: -2px 0 0;
  font-size: 12px;
  color: #b91c1c;
}

.action-hint {
  margin: -2px 0 0;
  font-size: 12px;
  color: #64748b;
}

.action-hint--warning {
  color: #b45309;
}

.class-bind-panel {
  border: 1px solid #e4eaf2;
  border-radius: 14px;
  background: #fff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.schedule-panel {
  border: 1px solid #e4eaf2;
  border-radius: 14px;
  background: #fff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.schedule-header {
  margin-bottom: 0;
}

.schedule-title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.schedule-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #556278;
}

.schedule-input {
  width: 100%;
  min-width: 0;
  border: 1px solid #d9e2ec;
  border-radius: 10px;
  background: #f8fbff;
  color: #0f172a;
  padding: 10px 12px;
  font-size: 13px;
}

.schedule-input:disabled {
  opacity: 0.72;
  background: #f3f4f6;
}

.schedule-success {
  margin: 0;
  font-size: 12px;
  color: #0f766e;
}

.settings-modal {
  position: fixed;
  inset: 0;
  z-index: 70;
  background: rgba(15, 23, 42, 0.3);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 12px;
}

.metric-modal {
  position: fixed;
  inset: 0;
  z-index: 72;
  background: rgba(15, 23, 42, 0.34);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 12px;
}

.metric-modal-card {
  width: min(760px, 100%);
  max-height: min(82dvh, 860px);
  overflow: auto;
  border-radius: 18px;
  border: 1px solid #dce5ef;
  background: linear-gradient(180deg, #fbfdff 0%, #f3f8fc 100%);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.metric-modal-header h3 {
  margin: 0;
  font-size: 16px;
}

.metric-chart-wrap {
  border: 1px solid #e4eaf2;
  border-radius: 12px;
  background: #fff;
  padding: 8px;
}

.metric-chart {
  width: 100%;
  height: 290px;
}

.participant-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #556278;
}

.participant-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.participant-panel {
  border: 1px solid #e4eaf2;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.participant-panel h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.participant-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.participant-item {
  border: 1px solid #edf1f6;
  border-radius: 10px;
  background: #fbfdff;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.participant-name {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.participant-class {
  margin: 2px 0 0;
  font-size: 11px;
  color: #64748b;
}

.participant-status {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.status-progress {
  color: #1d4ed8;
  background: rgba(29, 78, 216, 0.12);
}

.status-submitted {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.12);
}

.status-reviewed {
  color: #0f766e;
  background: rgba(20, 184, 166, 0.16);
}

.status-pending {
  color: #64748b;
  background: rgba(148, 163, 184, 0.14);
}

.settings-modal-card {
  width: min(760px, 100%);
  max-height: min(86dvh, 900px);
  overflow: auto;
  border-radius: 18px;
  border: 1px solid #dce5ef;
  background: linear-gradient(180deg, #f8fbff 0%, #f4f8fc 100%);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.settings-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.settings-modal-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #0f172a;
}

.settings-modal-title h2 {
  margin: 0;
  font-size: 16px;
}

.class-bind-header {
  margin-bottom: 0;
}

.class-bind-tip {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.class-bind-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.class-bind-item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #edf1f6;
  border-radius: 10px;
  padding: 8px;
  font-size: 13px;
  color: #0f172a;
  background: #fbfdff;
}

.class-bind-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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
  .exam-detail-dashboard {
    padding-top: 8px;
  }

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

  .class-bind-list {
    grid-template-columns: 1fr;
  }

  .schedule-grid {
    grid-template-columns: 1fr;
  }

  .participant-grid {
    grid-template-columns: 1fr;
  }

  .settings-modal {
    padding: 8px;
  }

  .settings-modal-card {
    max-height: min(90dvh, 900px);
    border-radius: 16px;
  }
}

@media (min-width: 768px) {
  .exam-detail-dashboard {
    margin: -40px -32px 0;
    padding: calc(12px + 40px) 32px calc(24px + env(safe-area-inset-bottom));
  }
}
</style>
