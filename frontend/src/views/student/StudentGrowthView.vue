<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ArrowUpRight, Brain, ShieldAlert, Sparkles, Target, TrendingUp } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, RadarComponent, TooltipComponent } from 'echarts/components'
import http from '@/lib/http'
import { useAuthStore } from '@/stores/auth'

use([CanvasRenderer, PieChart, RadarChart, BarChart, LineChart, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

const loading = ref(true)
const loadError = ref('')
const authStore = useAuthStore()

const trendData = ref<any>({ exams: [], insights: [] })
const knowledgeData = ref<any>({ nodes: [] })
const taskData = ref<any>({ tasks: [], ai_overview: null, ai_actions: [] })
const dashboardData = ref<any>(null)
const growthAiData = ref<any>({ ability_profile: [], ai_summary: '', ai_actions: [], recommended_books: [] })
const CACHE_NAMESPACE = 'student-growth-profile-cache-v2'
const GROWTH_CACHE_TTL_MS = 10 * 60 * 1000
const PROFILE_REFRESH_NAMESPACE = 'student-growth-profile-refresh-at-v2'
const PROFILE_REFRESH_COOLDOWN_MS = 60 * 1000
const refreshLoading = ref(false)
const refreshCooldownLeft = ref(0)
let refreshTimer: number | undefined

const userScopeKey = computed(() => {
  const uid = Number(authStore.user?.id || 0)
  if (uid > 0) return `uid:${uid}`
  const tokenTail = String(authStore.token || '').slice(-16)
  return tokenTail ? `token:${tokenTail}` : 'anonymous'
})

const growthCacheKey = computed(() => `${CACHE_NAMESPACE}:${userScopeKey.value}`)
const profileRefreshCooldownKey = computed(() => `${PROFILE_REFRESH_NAMESPACE}:${userScopeKey.value}`)

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  judge: '判断题',
  true_false: '判断题',
  blank: '填空题',
  fill_blank: '填空题',
  short_answer: '简答题',
  material: '材料题',
  programming: '编程题',
  essay: '论述题',
  case: '案例题',
}

const TOPIC_PALETTE = ['#3b82f6', '#06b6d4', '#10b981', '#a3e635', '#f59e0b', '#ef4444', '#8b5cf6']

const resolveQuestionTypeLabel = (rawType: string) => {
  const normalized = String(rawType || '').trim().toLowerCase().replace(/\s+/g, '_')
  if (!normalized) return '未分类题型'
  if (QUESTION_TYPE_LABELS[normalized]) return QUESTION_TYPE_LABELS[normalized]
  return normalized.replace(/_/g, ' ')
}

const exams = computed(() => (trendData.value?.exams || []) as Array<any>)
const timelineLabelStep = computed(() => {
  const total = exams.value.length
  if (total <= 6) return 1
  if (total <= 10) return 2
  if (total <= 16) return 3
  return 4
})

const formatTimelineDateLabel = (raw: string) => {
  const text = String(raw || '')
  if (!text) return ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text.slice(5)
  }
  return text
}
const trendSummary = computed(() => {
  const raw = trendData.value?.trend_summary || {}
  return {
    windowSize: Number(raw.window_size || 0),
    sampleCount: Number(raw.sample_count || 0),
    startAvg: Number(raw.start_avg || 0),
    recentAvg: Number(raw.recent_avg || 0),
    momentum: Number(raw.momentum || 0),
    direction: String(raw.direction || 'flat'),
  }
})
const weakNodes = computed(() => {
  const nodes = (knowledgeData.value?.nodes || []) as Array<any>
  return [...nodes].sort((a, b) => Number(a.mastery || 0) - Number(b.mastery || 0)).slice(0, 5)
})

const averageScore = computed(() => {
  if (!exams.value.length) return 0
  const sum = exams.value.reduce((acc, item) => acc + Number(item.score || 0), 0)
  return Math.round((sum / exams.value.length) * 10) / 10
})

const scoreMomentum = computed(() => {
  if (trendSummary.value.sampleCount >= 2) {
    return Math.round(trendSummary.value.momentum * 10) / 10
  }
  if (exams.value.length < 2) return 0
  const first = Number(exams.value[0]?.score || 0)
  const last = Number(exams.value[exams.value.length - 1]?.score || 0)
  return Math.round((last - first) * 10) / 10
})

const trendSummaryText = computed(() => {
  if (trendSummary.value.sampleCount < 2) return '样本不足，完成更多测验后可计算趋势变化。'
  const n = Math.max(1, trendSummary.value.windowSize)
  return `趋势变化 = 最近${n}次均分(${trendSummary.value.recentAvg}) - 最早${n}次均分(${trendSummary.value.startAvg})`
})

type MetricExplainKey = 'average' | 'trend' | 'mastery'

const activeMetricKey = ref<MetricExplainKey | null>(null)

const openMetricExplain = (key: MetricExplainKey) => {
  activeMetricKey.value = key
}

const closeMetricExplain = () => {
  activeMetricKey.value = null
}

const metricExplainMap = computed(() => {
  const examCount = exams.value.length
  const scoreList = exams.value.map((item) => Number(item.score || 0))
  const scoreExpr = scoreList.map((item) => item.toFixed(1)).join(' + ')
  const nodes = (knowledgeData.value?.nodes || []) as Array<any>
  const masteryList = nodes.map((item) => Number(item.mastery || 0))
  const masteryExpr = masteryList.map((item) => Number(item * 100).toFixed(0)).join(' + ')
  const trendWindow = Math.max(1, Number(trendSummary.value.windowSize || 1))
  const startWindowScores = scoreList.slice(0, trendWindow)
  const recentWindowScores = scoreList.slice(-trendWindow)
  const startExpr = startWindowScores.map((item) => item.toFixed(1)).join(' + ')
  const recentExpr = recentWindowScores.map((item) => item.toFixed(1)).join(' + ')

  return {
    average: {
      title: '平均分',
      meaning: '反映最近测验的整体水平，用于判断当前阶段的稳定表现。',
      formula: '平均分 = 所有测验分数之和 ÷ 测验次数',
      calculation:
        examCount > 0
          ? `(${scoreExpr}) ÷ ${examCount} = ${averageScore.value.toFixed(1)}`
          : '暂无测验数据，无法计算平均分。',
      range: '区间：0-100，分值越高代表整体表现越稳。',
    },
    trend: {
      title: '趋势变化',
      meaning: '反映阶段性进步或回落，避免单次考试波动造成误判。',
      formula: '趋势变化 = 最近N次均分 - 最早N次均分（默认 N=3，样本不足自动降级）',
      calculation:
        trendSummary.value.sampleCount >= 2
          ? `[( ${recentExpr} ) ÷ ${trendWindow}] - [( ${startExpr} ) ÷ ${trendWindow}] = ${scoreMomentum.value.toFixed(1)}`
          : '样本不足，需至少 2 次测验后才可计算趋势变化。',
      range: '结果解读：>0 为上升，<0 为下降，接近 0 说明处于平台期。',
    },
    mastery: {
      title: '掌握度',
      meaning: '反映知识点层面的平均掌握水平，用于识别薄弱点密度。',
      formula: '掌握度(%) = 知识点掌握度平均值 × 100',
      calculation:
        masteryList.length > 0
          ? `(${masteryExpr}) ÷ ${masteryList.length} = ${masteryAverage.value}%`
          : '暂无知识点数据，无法计算掌握度。',
      range: '区间：0-100%，建议结合“薄弱知识点”列表一起看。',
    },
  }
})

const activeMetricExplain = computed(() => {
  if (!activeMetricKey.value) return null
  return metricExplainMap.value[activeMetricKey.value]
})

const masteryAverage = computed(() => {
  const nodes = (knowledgeData.value?.nodes || []) as Array<any>
  if (!nodes.length) return 0
  const total = nodes.reduce((acc, item) => acc + Number(item.mastery || 0), 0)
  return Math.round((total / nodes.length) * 100)
})

const aiRiskLevel = computed(() => {
  if (masteryAverage.value < 55) return '高风险'
  if (masteryAverage.value < 72) return '中风险'
  return '可控'
})

const aiCoachSummary = computed(() => {
  const backendSummary = String(growthAiData.value?.ai_summary || '').trim()
  if (backendSummary) return backendSummary

  const parts: string[] = []
  parts.push(`当前知识点平均掌握度 ${masteryAverage.value}%`) 
  if (scoreMomentum.value > 0) {
    parts.push(`最近成绩较初期提升 ${scoreMomentum.value} 分`)
  } else if (scoreMomentum.value < 0) {
    parts.push(`最近成绩较初期下降 ${Math.abs(scoreMomentum.value)} 分`)
  } else {
    parts.push('成绩波动较小，处于平台期')
  }
  if (weakNodes.value.length) {
    parts.push(`薄弱点主要集中在 ${weakNodes.value.slice(0, 2).map((x) => x.name).join('、')}`)
  }
  return parts.join('；')
})

const normalizeTypeText = (text: string) => {
  let normalized = String(text || '')
  for (const [key, label] of Object.entries(QUESTION_TYPE_LABELS)) {
    normalized = normalized.replaceAll(key, label)
  }
  return normalized
}

const dedupeOrdered = (items: string[]) => {
  const seen = new Set<string>()
  const output: string[] = []
  for (const raw of items) {
    const text = normalizeTypeText(String(raw || '').trim())
    if (!text || seen.has(text)) continue
    seen.add(text)
    output.push(text)
  }
  return output
}

const aiActions = computed(() => {
  const backendActions = (growthAiData.value?.ai_actions || []) as string[]
  const cleanedBackend = dedupeOrdered(backendActions)
  if (cleanedBackend.length >= 3) {
    return cleanedBackend.slice(0, 6)
  }

  const localActions: string[] = []
  if (weakNodes.value.length) {
    localActions.push(`优先复习 ${weakNodes.value[0].name}，建议按“基础题2题 + 变式题1题 + 错因复盘1次”执行。`)
  }
  if (Number(taskData.value?.ai_overview?.active_task_count || 0) > 0) {
    const mins = Number(taskData.value?.ai_overview?.suggested_session_minutes || 20)
    localActions.push(`按 ${mins} 分钟一轮执行复习：前 ${Math.max(6, Math.floor(mins * 0.4))} 分钟做题，后续时间专门复盘错因。`)
  }
  if (scoreMomentum.value <= 0) {
    localActions.push('最近成绩进入平台期，建议每道错题标记“概念不清/审题偏差/计算失误”之一，便于下次针对训练。')
  }
  return dedupeOrdered([...cleanedBackend, ...localActions]).slice(0, 6)
})

const abilityProfile = computed(() => {
  const profileList = (growthAiData.value?.ability_profile || []) as Array<any>
  if (profileList.length) {
    return profileList.map((item) => ({
      name: String(item.name || '综合能力'),
      value: Math.max(0, Math.min(100, Math.round(Number(item.value || 0)))),
      questionCount: Number(item.question_count || 0),
      accuracy: Math.round(Number(item.accuracy || 0) * 100),
      reason: String(item.reason || ''),
    }))
  }
  const profile = dashboardData.value?.ability_profile_summary || {}
  return Object.entries(profile).map(([name, value]) => ({
    name,
    value: Math.round(Number(value || 0) * 100),
    questionCount: 0,
    accuracy: 0,
    reason: '',
  }))
})

const recommendedBooks = computed(() => {
  return ((growthAiData.value?.recommended_books || []) as Array<any>).map((book) => ({
    title: String(book.title || ''),
    author: String(book.author || ''),
    isbn: String(book.isbn || ''),
    link: String(book.link || ''),
    reason: String(book.reason || ''),
    topics: Array.isArray(book.related_topics) ? book.related_topics : [],
  }))
})

const topicDistribution = computed(() => {
  return ((growthAiData.value?.topic_distribution || []) as Array<any>).map((item) => ({
    topic: String(item.topic || '综合能力'),
    questionCount: Number(item.question_count || 0),
    accuracy: Math.round(Number(item.accuracy || 0) * 100),
  }))
})

const topicLegendItems = computed(() => {
  return topicDistribution.value.map((item, index) => ({
    label: item.topic,
    questionCount: item.questionCount,
    color: TOPIC_PALETTE[index % TOPIC_PALETTE.length],
  }))
})

const questionTypeDistribution = computed(() => {
  return ((growthAiData.value?.question_type_distribution || []) as Array<any>).map((item) => {
    const raw = String(item.type || '')
    return {
      type: resolveQuestionTypeLabel(raw),
      questionCount: Number(item.question_count || 0),
      accuracy: Math.round(Number(item.accuracy || 0) * 100),
    }
  })
})

const selectedAbility = ref<any | null>(null)

const getAbilityInsight = (ability: any) => {
  const score = Number(ability?.value || 0)
  const accuracy = Number(ability?.accuracy || 0)
  const name = String(ability?.name || '该能力')

  let level = '基础待强化'
  let strengths = `在${name}维度已具备基础作答能力，但稳定性仍有提升空间。`
  let risks = '遇到复杂题型时可能出现步骤跳跃或细节丢失。'
  let advice = '建议采用“先慢后快”的专项训练：先做2题基础，再做1题变式并复盘。'

  if (score >= 80) {
    level = '优势能力'
    strengths = `你在${name}上表现稳定，能够较好完成同类题目的识别与作答。`
    risks = '主要风险是高分阶段的粗心失分与难题边界判断。'
    advice = '保持每周1次高阶题训练，并记录“易错触发点”防止回落。'
  } else if (score >= 65) {
    level = '中段可提升'
    strengths = `你在${name}上已经形成一定方法，常规题可较快进入状态。`
    risks = '在综合题和陌生题场景下，解题路径仍可能不够稳。'
    advice = '每次练习后补1次错因复盘，重点记录“为什么这步会错”。'
  }

  if (accuracy > 0) {
    advice = `${advice} 当前相关题正确率约 ${accuracy}%。`
  }

  return { level, strengths, risks, advice }
}

const openAbilityModal = (ability: any) => {
  selectedAbility.value = ability
}

const closeAbilityModal = () => {
  selectedAbility.value = null
}

const abilityRadarOption = computed(() => {
  const items = abilityProfile.value.slice(0, 6)
  if (!items.length) return null
  return {
    tooltip: { trigger: 'item' },
    radar: {
      radius: '62%',
      indicator: items.map((item) => ({ name: item.name, max: 100 })),
      splitNumber: 4,
      axisName: { color: '#48576b', fontSize: 12 },
      splitLine: { lineStyle: { color: '#dfe8f4' } },
      splitArea: { areaStyle: { color: ['#fbfdff', '#f4f8fe'] } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: items.map((item) => item.value),
            name: '能力值',
            areaStyle: { color: 'rgba(15, 118, 110, 0.2)' },
            lineStyle: { color: '#0f766e', width: 2 },
            itemStyle: { color: '#0f766e' },
          },
        ],
      },
    ],
  }
})

const topicPieOption = computed(() => {
  const items = topicDistribution.value
  if (!items.length) return null
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>题量 {c} · 占比 {d}%' },
    series: [
      {
        type: 'pie',
        radius: ['44%', '70%'],
        center: ['50%', '50%'],
        data: items.map((item, index) => ({
          name: item.topic,
          value: item.questionCount,
          itemStyle: { color: TOPIC_PALETTE[index % TOPIC_PALETTE.length] },
        })),
        label: { show: false },
      },
    ],
  }
})

const questionTypeBarOption = computed(() => {
  const items = questionTypeDistribution.value
  if (!items.length) return null
  const labels = items.map((item) => item.type)
  const values = items.map((item) => item.questionCount)
  const barPalette = ['#0ea5e9', '#f97316', '#14b8a6', '#eab308', '#6366f1', '#ef4444', '#8b5cf6']
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any[]) => {
        const first = params?.[0]
        return `${first?.name || '题型'}<br/>题量 ${Number(first?.value || 0)}`
      },
    },
    grid: { left: 86, right: 16, top: 8, bottom: 24 },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { lineStyle: { color: '#d7e1ef' } },
      splitLine: { lineStyle: { color: '#ecf2fb' } },
      axisLabel: { color: '#5a6b80' },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d7e1ef' } },
      axisLabel: { color: '#46556b', width: 72, overflow: 'truncate' },
    },
    series: [
      {
        type: 'bar',
        barWidth: 18,
        data: values.map((value, index) => ({
          value,
          itemStyle: {
            color: barPalette[index % barPalette.length],
            borderRadius: [0, 8, 8, 0],
          },
        })),
      },
    ],
  }
})

const scoreTrendLineOption = computed(() => {
  if (!exams.value.length) return null
  const labels = exams.value.map((item) => String(item.date || ''))
  const step = Math.max(1, timelineLabelStep.value)
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { color: '#5a6b80', fontSize: 12 } },
    grid: { left: 18, right: 18, top: 12, bottom: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d7e1ef' } },
      axisLabel: {
        color: '#516175',
        rotate: 0,
        formatter: (value: string, index: number) => {
          if (labels.length <= 1) return formatTimelineDateLabel(value)
          const isBoundary = index === 0 || index === labels.length - 1
          if (!isBoundary && index % step !== 0) return ''
          return formatTimelineDateLabel(value)
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: '#d7e1ef' } },
      splitLine: { lineStyle: { color: '#ecf2fb' } },
      axisLabel: { color: '#5a6b80' },
    },
    series: [
      {
        name: '我的成绩',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        lineStyle: { color: '#0f766e', width: 2.5 },
        itemStyle: { color: '#0f766e' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(15, 118, 110, 0.22)' },
              { offset: 1, color: 'rgba(15, 118, 110, 0.03)' },
            ],
          },
        },
        data: exams.value.map((item) => Number(item.score || 0)),
      },
      {
        name: '班级均分',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        lineStyle: { color: '#1d4ed8', width: 2, type: 'dashed' },
        itemStyle: { color: '#1d4ed8' },
        data: exams.value.map((item) => Number(item.class_avg || 0)),
      },
    ],
  }
})

const canRefreshProfile = computed(() => refreshCooldownLeft.value <= 0 && !refreshLoading.value)

const updateCooldown = () => {
  let lastRefreshAt = 0
  try {
    lastRefreshAt = Number(localStorage.getItem(profileRefreshCooldownKey.value) || 0)
  } catch {
    lastRefreshAt = 0
  }
  const left = Math.ceil((lastRefreshAt + PROFILE_REFRESH_COOLDOWN_MS - Date.now()) / 1000)
  refreshCooldownLeft.value = Math.max(0, left)
}

const loadGrowthData = async (forceProfileRefresh = false) => {
  let cachedGrowthProfile: any = null
  if (!forceProfileRefresh) {
    try {
      const raw = localStorage.getItem(growthCacheKey.value)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (String(parsed?.scope || '') !== userScopeKey.value) {
          cachedGrowthProfile = null
        }
        const cachedAt = Number(parsed?.cachedAt || 0)
        if (String(parsed?.scope || '') === userScopeKey.value && Date.now() - cachedAt < GROWTH_CACHE_TTL_MS && parsed?.payload) {
          cachedGrowthProfile = parsed.payload
        }
      }
    } catch {
      cachedGrowthProfile = null
    }
  }

  const profilePromise = cachedGrowthProfile
    ? Promise.resolve(cachedGrowthProfile)
    : http.get('/student/growth/ability-profile', { params: { force_refresh: forceProfileRefresh || undefined } })

  const [growthRes, knowledgeRes, tasksRes, overviewRes, growthProfileRes] = await Promise.all([
    http.get('/student/growth-trend'),
    http.get('/student/knowledge-map'),
    http.get('/student/study-tasks'),
    http.get('/student/dashboard/overview'),
    profilePromise,
  ])

  trendData.value = growthRes || { exams: [], insights: [] }
  knowledgeData.value = knowledgeRes || { nodes: [] }
  taskData.value = tasksRes || { tasks: [], ai_overview: null, ai_actions: [] }
  dashboardData.value = overviewRes || null
  growthAiData.value = growthProfileRes || {
    ability_profile: [],
    ai_summary: '',
    ai_actions: [],
    recommended_books: [],
    topic_distribution: [],
    question_type_distribution: [],
  }

  try {
    if (growthProfileRes) {
      localStorage.setItem(
        growthCacheKey.value,
        JSON.stringify({
          scope: userScopeKey.value,
          cachedAt: Date.now(),
          payload: growthProfileRes,
        }),
      )
    }
  } catch {
    // Ignore localStorage failures silently.
  }
}

const refreshGrowthProfile = async () => {
  if (!canRefreshProfile.value) return
  try {
    refreshLoading.value = true
    await loadGrowthData(true)
    localStorage.setItem(profileRefreshCooldownKey.value, String(Date.now()))
    updateCooldown()
  } catch (error: any) {
    console.error('手动更新成长档案失败', error)
    loadError.value = error?.message || '更新成长档案失败'
  } finally {
    refreshLoading.value = false
  }
}

onMounted(async () => {
  try {
    loading.value = true
    loadError.value = ''
    updateCooldown()
    refreshTimer = window.setInterval(updateCooldown, 1000)
    await loadGrowthData(false)
  } catch (error: any) {
    console.error('加载成长档案失败', error)
    loadError.value = error?.message || '成长档案数据加载失败'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
})
</script>

<template>
  <div v-if="loading" class="loading-state">
    <div class="spinner"></div>
    <p>AI 正在生成成长诊断...</p>
  </div>

  <div v-else-if="loadError" class="error-state">
    {{ loadError }}
  </div>

  <div v-else class="view-growth">
    <header class="header">
      <div class="header-row">
        <h1 class="title">成长档案</h1>
        <button class="refresh-btn" :disabled="!canRefreshProfile" @click="refreshGrowthProfile">
          {{ refreshLoading ? '检测中...' : refreshCooldownLeft > 0 ? `重新检测(${refreshCooldownLeft}s)` : '重新检测' }}
        </button>
      </div>
      <p class="subtitle">AI 从成绩趋势、知识掌握和任务执行三方面为你生成个性化诊断。</p>
    </header>

    <section class="ai-hero">
      <div class="ai-hero-head">
        <div class="hero-title-row">
          <Brain :size="18" />
          <h2>AI 成长诊断</h2>
        </div>
        <span class="risk-pill" :class="{ high: aiRiskLevel === '高风险', mid: aiRiskLevel === '中风险' }">{{ aiRiskLevel }}</span>
      </div>
      <p class="hero-summary">{{ aiCoachSummary }}</p>
      <div class="hero-stats">
        <div class="hero-stat">
          <div class="hero-stat-head">
            <span>平均分</span>
            <button class="metric-help-btn" @click="openMetricExplain('average')">计算说明</button>
          </div>
          <strong>{{ averageScore }} 分</strong>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-head">
            <span>趋势变化</span>
            <button class="metric-help-btn" @click="openMetricExplain('trend')">计算说明</button>
          </div>
          <strong :class="{ up: scoreMomentum > 0, down: scoreMomentum < 0 }">
            {{ scoreMomentum > 0 ? '+' : '' }}{{ scoreMomentum }} 分
          </strong>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-head">
            <span>掌握度</span>
            <button class="metric-help-btn" @click="openMetricExplain('mastery')">计算说明</button>
          </div>
          <strong>{{ masteryAverage }}%</strong>
        </div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>薄弱知识点（AI分类）</h2>
        <span class="section-sub">AI 建议先攻克前 3 项</span>
      </div>
      <div v-if="weakNodes.length" class="weak-list">
        <div v-for="(item, idx) in weakNodes" :key="item.id" class="weak-item">
          <div class="weak-main">
            <p class="weak-name">{{ idx + 1 }}. {{ item.name }}</p>
            <p class="weak-meta">掌握度 {{ Math.round(Number(item.mastery || 0) * 100) }}% · {{ item.status === 'weak' ? '薄弱' : item.status === 'average' ? '一般' : '稳定' }}</p>
          </div>
          <div class="weak-bar-track">
            <div class="weak-bar-fill" :style="{ width: `${Math.round(Number(item.mastery || 0) * 100)}%` }"></div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">完成更多测验后，这里会自动生成你的薄弱点优先级。</div>
    </section>

    <section class="chart-grid">
      <article class="card-block chart-card">
        <div class="section-title-row">
          <h2>能力雷达图</h2>
          <Target :size="16" class="icon-accent" />
        </div>
        <VChart v-if="abilityRadarOption" :option="abilityRadarOption" autoresize class="chart" />
        <div v-else class="empty-state">暂无能力画像图表数据。</div>
        <div v-if="abilityProfile.length" class="ability-chip-row">
          <button
            v-for="item in abilityProfile.slice(0, 6)"
            :key="`ability-chip-${item.name}`"
            class="ability-chip"
            @click="openAbilityModal(item)"
          >
            {{ item.name }}
          </button>
        </div>
      </article>

      <article class="card-block chart-card">
        <div class="section-title-row">
          <h2>作答主题分布</h2>
          <TrendingUp :size="16" class="icon-accent" />
        </div>
        <VChart v-if="topicPieOption" :option="topicPieOption" autoresize class="chart" />
        <div v-if="topicLegendItems.length" class="topic-legend">
          <span v-for="item in topicLegendItems" :key="`topic-legend-${item.label}`" class="topic-legend-item">
            <i class="topic-dot" :style="{ backgroundColor: item.color }"></i>
            <span class="topic-name">{{ item.label }}</span>
            <span class="topic-count">{{ item.questionCount }}题</span>
          </span>
        </div>
        <div v-else class="empty-state">暂无主题分布数据。</div>
      </article>

      <article class="card-block chart-card">
        <div class="section-title-row">
          <h2>题型构成柱图</h2>
          <Sparkles :size="16" class="icon-accent" />
        </div>
        <VChart v-if="questionTypeBarOption" :option="questionTypeBarOption" autoresize class="chart" />
        <div v-else class="empty-state">暂无题型分布数据。</div>
      </article>
    </section>

    <section class="split-grid">
      <article class="card-block">
        <div class="section-title-row">
          <h2>AI 行动建议</h2>
          <Sparkles :size="16" class="icon-accent" />
        </div>
        <ul class="action-list" v-if="aiActions.length">
          <li v-for="(item, idx) in aiActions" :key="`action-${idx}`">{{ item }}</li>
        </ul>
        <div v-else class="empty-state">暂无行动建议，继续完成任务后可获得更精准指导。</div>
      </article>

      <article class="card-block">
        <div class="section-title-row">
          <h2>能力画像</h2>
          <Target :size="16" class="icon-accent" />
        </div>
        <div v-if="abilityProfile.length" class="ability-list">
          <div v-for="item in abilityProfile" :key="item.name" class="ability-item">
            <div class="ability-head">
              <span>{{ item.name }}</span>
              <strong>{{ item.value }}%</strong>
            </div>
            <div class="ability-track">
              <div class="ability-fill" :style="{ width: `${item.value}%` }"></div>
            </div>
            <p v-if="item.questionCount" class="ability-meta">样本 {{ item.questionCount }} 题 · 正确率 {{ item.accuracy }}%</p>
            <p v-if="item.reason" class="ability-reason">{{ item.reason }}</p>
          </div>
        </div>
        <div v-else class="empty-state">能力画像正在生成中。</div>
      </article>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>AI 书籍推荐</h2>
        <span class="section-sub">基于你最近作答题目自动匹配</span>
      </div>
      <div v-if="recommendedBooks.length" class="book-list">
        <article v-for="book in recommendedBooks" :key="book.isbn || book.title" class="book-item">
          <div class="book-head">
            <h3>{{ book.title }}</h3>
            <a v-if="book.link" :href="book.link" target="_blank" rel="noopener noreferrer">查看书籍</a>
          </div>
          <p class="book-author">{{ book.author }}<span v-if="book.isbn"> · ISBN {{ book.isbn }}</span></p>
          <p class="book-reason">{{ book.reason }}</p>
          <p v-if="book.topics.length" class="book-topics">关联题目方向：{{ book.topics.join('、') }}</p>
        </article>
      </div>
      <div v-else class="empty-state">继续完成相关题目后，这里会推荐更贴合你的参考书。</div>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>成绩时间线</h2>
        <TrendingUp :size="16" class="icon-accent" />
      </div>
      <p class="trend-summary-text">{{ trendSummaryText }}</p>
      <VChart v-if="scoreTrendLineOption" :option="scoreTrendLineOption" autoresize class="chart chart-score-line" />
      <div v-if="exams.length" class="history-list">
        <div v-for="(exam, idx) in exams" :key="idx" class="history-item">
          <p class="history-date">{{ exam.date }}</p>
          <div class="history-main">
            <div>
              <p class="history-title">测验成绩</p>
              <p class="history-meta">班级均分 {{ exam.class_avg }}</p>
            </div>
            <div class="history-score">
              <span>{{ exam.score }}</span>
              <small>分</small>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">暂无历史成绩记录。</div>
    </section>

    <section class="tip-box">
      <div class="tip-head">
        <ShieldAlert :size="16" />
        <span>AI 提醒</span>
      </div>
      <p>{{ dashboardData?.ai_reminders?.[0] || '建议每次测验后完成错题复盘，系统将持续优化你的成长诊断。' }}</p>
      <div class="tip-link-row">
        <ArrowUpRight :size="14" />
        <span>可前往“复习计划”执行今日任务</span>
      </div>
    </section>

    <div v-if="selectedAbility" class="ability-modal-mask" @click.self="closeAbilityModal">
      <article class="ability-modal">
        <div class="ability-modal-head">
          <h3>{{ selectedAbility.name }} · {{ getAbilityInsight(selectedAbility).level }}</h3>
          <button class="ability-modal-close" @click="closeAbilityModal">关闭</button>
        </div>
        <div class="ability-modal-body">
          <p><strong>优势表现：</strong>{{ getAbilityInsight(selectedAbility).strengths }}</p>
          <p><strong>当前短板：</strong>{{ getAbilityInsight(selectedAbility).risks }}</p>
          <p><strong>AI 建议：</strong>{{ getAbilityInsight(selectedAbility).advice }}</p>
        </div>
      </article>
    </div>

    <div v-if="activeMetricExplain" class="ability-modal-mask" @click.self="closeMetricExplain">
      <article class="ability-modal metric-modal">
        <div class="ability-modal-head">
          <h3>{{ activeMetricExplain.title }} · 计算说明</h3>
          <button class="ability-modal-close" @click="closeMetricExplain">关闭</button>
        </div>
        <div class="ability-modal-body metric-modal-body">
          <p><strong>指标意义：</strong>{{ activeMetricExplain.meaning }}</p>
          <p><strong>计算公式：</strong>{{ activeMetricExplain.formula }}</p>
          <p><strong>代入结果：</strong>{{ activeMetricExplain.calculation }}</p>
          <p><strong>解释口径：</strong>{{ activeMetricExplain.range }}</p>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.view-growth {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 20px;
}

.header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.refresh-btn {
  border: 1px solid #c9d8eb;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff, #f4f8ff);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 10px;
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.title {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: #556278;
  line-height: 1.5;
}

.ai-hero,
.section-block,
.card-block,
.tip-box {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  padding: 12px;
}

.ai-hero {
  background: linear-gradient(145deg, #ffffff, #eef7ff);
}

.ai-hero-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.hero-title-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.hero-title-row h2 {
  margin: 0;
  font-size: 17px;
}

.risk-pill {
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  padding: 3px 10px;
  color: #166534;
  background: rgba(22, 101, 52, 0.1);
}

.risk-pill.mid {
  color: #b45309;
  background: rgba(245, 158, 11, 0.18);
}

.risk-pill.high {
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.16);
}

.hero-summary {
  margin: 10px 0 0;
  color: #334155;
  font-size: 13px;
  line-height: 1.6;
}

.hero-stats {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.hero-stat {
  border: 1px solid #e6edf5;
  border-radius: 10px;
  background: #fff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.hero-stat span {
  font-size: 12px;
  color: #64748b;
}

.hero-stat strong {
  font-size: 18px;
  color: #0f172a;
}

.hero-stat .up {
  color: #0f766e;
}

.hero-stat .down {
  color: #dc2626;
}

.metric-help-btn {
  border: 1px solid #d4e0ef;
  background: #f8fbff;
  color: #1d4ed8;
  font-size: 11px;
  line-height: 1;
  border-radius: 999px;
  padding: 4px 8px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 10px;
}

.section-title-row h2 {
  margin: 0;
  font-size: 16px;
}

.section-sub {
  font-size: 12px;
  color: #64748b;
}

.trend-summary-text {
  margin: 0 0 8px;
  font-size: 12px;
  color: #5b697d;
  line-height: 1.5;
}

.icon-accent {
  color: #0f766e;
}

.weak-list,
.ability-list,
.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weak-item,
.history-item {
  border: 1px solid #edf2f8;
  border-radius: 10px;
  padding: 9px;
  background: #fbfdff;
}

.weak-name {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
}

.weak-meta {
  margin: 3px 0 0;
  font-size: 12px;
  color: #64748b;
}

.weak-bar-track,
.ability-track {
  margin-top: 7px;
  height: 8px;
  border-radius: 999px;
  background: #e8eef7;
  overflow: hidden;
}

.weak-bar-fill,
.ability-fill {
  height: 100%;
  background: linear-gradient(90deg, #0f766e, #14b8a6);
  border-radius: 999px;
}

.split-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.chart-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart {
  width: 100%;
  height: 240px;
}

.chart-score-line {
  height: 220px;
  margin-bottom: 10px;
}

.topic-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.topic-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #dbe6f4;
  background: #f8fbff;
  border-radius: 999px;
  padding: 4px 9px;
  color: #425166;
  font-size: 12px;
  line-height: 1;
}

.topic-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.topic-name {
  max-width: 88px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topic-count {
  color: #64748b;
}

.ability-chip-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ability-chip {
  border: 1px solid #c6d8f0;
  background: #f3f8ff;
  color: #1e3a8a;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  border-radius: 999px;
  padding: 7px 10px;
}

.ability-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 14px;
}

.ability-modal {
  width: min(560px, 100%);
  border-radius: 14px;
  background: #fff;
  border: 1px solid #dbe6f4;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}

.metric-modal {
  border-color: #d2deee;
}

.metric-modal-body p {
  line-height: 1.65;
}

.ability-modal-head {
  padding: 12px;
  border-bottom: 1px solid #e7eef8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ability-modal-head h3 {
  margin: 0;
  font-size: 15px;
  color: #0f172a;
}

.ability-modal-close {
  border: 1px solid #d6dfec;
  background: #f8fbff;
  color: #1f3a66;
  font-size: 12px;
  font-weight: 600;
  border-radius: 8px;
  padding: 6px 9px;
}

.ability-modal-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ability-modal-body p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.action-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 13px;
  line-height: 1.5;
}

.ability-item {
  border: 1px solid #edf2f8;
  border-radius: 10px;
  background: #fbfdff;
  padding: 9px;
}

.ability-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #334155;
}

.ability-head strong {
  color: #0f172a;
}

.ability-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.ability-reason {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.book-item {
  border: 1px solid #edf2f8;
  border-radius: 10px;
  padding: 10px;
  background: #fbfdff;
}

.book-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.book-head h3 {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
}

.book-head a {
  font-size: 12px;
  color: #1d4ed8;
  font-weight: 600;
  text-decoration: none;
}

.book-author,
.book-reason,
.book-topics {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.history-date {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.history-main {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-title {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
}

.history-meta {
  margin: 2px 0 0;
  font-size: 12px;
  color: #64748b;
}

.history-score {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
}

.history-score span {
  font-size: 21px;
  color: #0f766e;
  font-weight: 700;
}

.history-score small {
  color: #64748b;
}

.tip-box {
  background: linear-gradient(140deg, #fff, #f3f7ff);
}

.tip-head {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.tip-box p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.55;
}

.tip-link-row {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.empty-state {
  border: 1px dashed #d8e2ef;
  border-radius: 10px;
  background: #f9fbff;
  padding: 14px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.loading-state,
.error-state {
  min-height: 56vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  gap: 12px;
}

.error-state {
  color: #b91c1c;
}

.spinner {
  width: 26px;
  height: 26px;
  border: 2px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 860px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .split-grid {
    grid-template-columns: 1fr;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }
}
</style>


