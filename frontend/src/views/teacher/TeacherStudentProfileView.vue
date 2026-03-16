<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  Clock3,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, RadarComponent, TooltipComponent } from 'echarts/components'
import { getStudentDetail, type TeacherStudentPortrait } from '@/api/teacher'

use([CanvasRenderer, LineChart, PieChart, BarChart, RadarChart, GridComponent, TooltipComponent, LegendComponent, RadarComponent])

const route = useRoute()
const router = useRouter()
const studentId = Number(route.params.id)

const loading = ref(true)
const errorText = ref('')
const portrait = ref<TeacherStudentPortrait | null>(null)

const riskLabelMap: Record<string, string> = {
  high: '高关注',
  medium: '需跟进',
  low: '状态稳定',
}

const questionTypeLabelMap: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  judge: '判断题',
  blank: '填空题',
  essay: '简答题',
  material: '材料题',
}

const student = computed(() => portrait.value?.student)
const classInfo = computed(() => portrait.value?.class)
const overview = computed(() => portrait.value?.overview)
const aiInsight = computed(() => portrait.value?.ai_insight)
const trend = computed(() => portrait.value?.trend || [])
const abilityProfile = computed(() => portrait.value?.ability_profile || [])
const knowledgePoints = computed(() => portrait.value?.knowledge_points || [])
const questionTypes = computed(() => portrait.value?.question_type_distribution || [])
const studyTasks = computed(() => portrait.value?.study_tasks || [])

const riskText = computed(() => riskLabelMap[String(overview.value?.risk_level || 'low')] || '状态稳定')
const accuracyPercent = computed(() => Math.round(Number(overview.value?.avg_correct_rate || 0) * 100))
const positiveMomentum = computed(() => Number(overview.value?.momentum || 0) >= 0)

const summaryCards = computed(() => {
  const current = overview.value
  return [
    {
      label: '最近成绩',
      value: `${Number(current?.latest_score || 0).toFixed(1)} 分`,
      sub: current?.exam_count ? `共完成 ${current.exam_count} 次测验` : '暂无测验记录',
      tone: 'blue',
      icon: TrendingUp,
    },
    {
      label: '平均正确率',
      value: `${accuracyPercent.value}%`,
      sub: `整体风险等级：${riskText.value}`,
      tone: 'teal',
      icon: Target,
    },
    {
      label: '学习任务负载',
      value: `${Number(overview.value?.active_task_count || 0)} 项`,
      sub: `预计还需 ${Number(overview.value?.estimated_study_minutes || 0)} 分钟`,
      tone: 'amber',
      icon: Clock3,
    },
    {
      label: '趋势动量',
      value: `${positiveMomentum.value ? '+' : ''}${Number(overview.value?.momentum || 0).toFixed(1)} 分`,
      sub: positiveMomentum.value ? '最近表现呈上升趋势' : '近期波动需要重点跟进',
      tone: 'slate',
      icon: Sparkles,
    },
  ]
})

const trendLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, textStyle: { color: '#5b697d', fontSize: 12 } },
  grid: { left: 20, right: 18, top: 16, bottom: 44, containLabel: true },
  xAxis: {
    type: 'category',
    data: trend.value.map((item) => item.exam_title),
    axisTick: { show: false },
    axisLabel: { color: '#5b697d', interval: 0, rotate: trend.value.length > 4 ? 18 : 0 },
    axisLine: { lineStyle: { color: '#d7e2ee' } },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#5b697d' },
    splitLine: { lineStyle: { color: '#edf3f9' } },
  },
  series: [
    {
      name: '学生成绩',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: trend.value.map((item) => Number(item.score || 0)),
      lineStyle: { color: '#1d4ed8', width: 3 },
      itemStyle: { color: '#1d4ed8' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(29, 78, 216, 0.22)' },
            { offset: 1, color: 'rgba(29, 78, 216, 0.02)' },
          ],
        },
      },
    },
    {
      name: '班级均分',
      type: 'line',
      smooth: true,
      symbolSize: 6,
      data: trend.value.map((item) => Number(item.class_avg || 0)),
      lineStyle: { color: '#0f766e', width: 2, type: 'dashed' },
      itemStyle: { color: '#0f766e' },
    },
  ],
}))

const abilityRadarOption = computed(() => ({
  tooltip: { trigger: 'item' },
  radar: {
    radius: '64%',
    indicator: abilityProfile.value.slice(0, 6).map((item) => ({ name: item.name, max: 100 })),
    splitNumber: 4,
    axisName: { color: '#4d5c70', fontSize: 12 },
    splitLine: { lineStyle: { color: '#d9e5f0' } },
    splitArea: { areaStyle: { color: ['#fbfdff', '#f1f7ff'] } },
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: abilityProfile.value.slice(0, 6).map((item) => Number(item.value || 0)),
          name: '能力值',
          areaStyle: { color: 'rgba(15, 118, 110, 0.2)' },
          lineStyle: { color: '#0f766e', width: 2 },
          itemStyle: { color: '#0f766e' },
        },
      ],
    },
  ],
}))

const knowledgeBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    formatter: (params: any[]) => {
      const current = params?.[0]
      return `${current?.name || ''}<br/>掌握度 ${Number(current?.value || 0)}%`
    },
  },
  grid: { left: 18, right: 18, top: 8, bottom: 24, containLabel: true },
  xAxis: {
    type: 'value',
    max: 100,
    axisLabel: { formatter: '{value}%', color: '#5b697d' },
    splitLine: { lineStyle: { color: '#edf3f9' } },
  },
  yAxis: {
    type: 'category',
    data: knowledgePoints.value.slice(0, 6).map((item) => item.name),
    axisTick: { show: false },
    axisLabel: { color: '#46556b' },
  },
  series: [
    {
      type: 'bar',
      barWidth: 16,
      data: knowledgePoints.value.slice(0, 6).map((item) => ({
        value: Math.round(Number(item.mastery || 0) * 100),
        itemStyle: { color: Number(item.mastery || 0) < 0.6 ? '#f97316' : '#3b82f6', borderRadius: [0, 8, 8, 0] },
      })),
    },
  ],
}))

const questionTypePieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}<br/>题量 {c} · 占比 {d}%' },
  legend: { bottom: 0, textStyle: { color: '#5b697d', fontSize: 12 } },
  series: [
    {
      type: 'pie',
      radius: ['44%', '72%'],
      center: ['50%', '42%'],
      label: { show: false },
      data: questionTypes.value.map((item, index) => ({
        name: questionTypeLabelMap[item.type] || item.type,
        value: Number(item.question_count || 0),
        itemStyle: { color: ['#2563eb', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9'][index % 6] },
      })),
    },
  ],
}))

const goBack = () => {
  router.back()
}

const fetchPortrait = async () => {
  try {
    loading.value = true
    errorText.value = ''
    portrait.value = await getStudentDetail(studentId)
  } catch (error: any) {
    errorText.value = error?.message || '加载学生画像失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPortrait()
})
</script>

<template>
  <div class="view-student-profile">
    <header class="hero-panel">
      <div class="hero-top">
        <button class="back-button" @click="goBack" aria-label="返回">
          <ArrowLeft :size="18" />
        </button>
        <span class="hero-eyebrow">教师学生画像</span>
      </div>

      <div v-if="student" class="hero-main">
        <div class="hero-identity">
          <div class="avatar-badge">{{ student.name?.slice(0, 1) || '学' }}</div>
          <div class="identity-copy">
            <h1>{{ student.name }}</h1>
            <p>
              {{ classInfo?.name || '未分配班级' }}
              <span v-if="classInfo?.subject"> · {{ classInfo.subject }}</span>
              <span v-if="student.grade_name"> · {{ student.grade_name }}</span>
            </p>
          </div>
        </div>

        <div class="hero-risk" :class="String(overview?.risk_level || 'low')">
          <span class="risk-label">{{ riskText }}</span>
          <strong>{{ Number(overview?.latest_score || 0).toFixed(1) }} 分</strong>
        </div>
      </div>

      <div v-if="aiInsight" class="hero-summary">
        <div class="summary-icon">
          <BrainCircuit :size="18" />
        </div>
        <p>{{ aiInsight.summary || '当前尚未积累足够数据，建议先观察该学生下一次测验表现。' }}</p>
      </div>
    </header>

    <div v-if="loading" class="state-panel">加载学生画像中...</div>
    <div v-else-if="errorText" class="state-panel state-panel--error">{{ errorText }}</div>

    <template v-else-if="portrait">
      <section class="stats-grid">
        <article v-for="card in summaryCards" :key="card.label" class="stat-tile" :data-tone="card.tone">
          <div class="stat-head">
            <span class="stat-icon">
              <component :is="card.icon" :size="16" />
            </span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
          <div class="stat-value">{{ card.value }}</div>
          <p class="stat-sub">{{ card.sub }}</p>
        </article>
      </section>

      <section class="insight-grid">
        <article class="panel panel-wide">
          <div class="panel-head">
            <div>
              <h2>成绩趋势对比</h2>
              <p>观察学生个人表现与班级平均水平的偏差与变化。</p>
            </div>
            <span class="pill">{{ trend.length }} 次记录</span>
          </div>
          <VChart v-if="trend.length" class="chart chart-line" :option="trendLineOption" autoresize />
          <div v-else class="empty-tip">暂无足够考试数据生成趋势。</div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>能力雷达</h2>
              <p>基于真实作答记录生成能力维度画像。</p>
            </div>
          </div>
          <VChart v-if="abilityProfile.length" class="chart" :option="abilityRadarOption" autoresize />
          <div v-else class="empty-tip">暂无能力画像数据。</div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>知识点掌握</h2>
              <p>优先查看薄弱知识点的掌握度与错题压力。</p>
            </div>
          </div>
          <VChart v-if="knowledgePoints.length" class="chart" :option="knowledgeBarOption" autoresize />
          <div v-else class="empty-tip">当前没有知识点统计。</div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>题型结构</h2>
              <p>观察该学生最近作答覆盖的题型重心。</p>
            </div>
          </div>
          <VChart v-if="questionTypes.length" class="chart" :option="questionTypePieOption" autoresize />
          <div v-else class="empty-tip">暂无题型统计。</div>
        </article>
      </section>

      <section class="two-column-grid">
        <article class="panel coaching-panel">
          <div class="panel-head">
            <div>
              <h2>AI 教学建议</h2>
              <p>面向教师的可执行跟进建议，而不是只看分数。</p>
            </div>
            <Sparkles :size="18" class="panel-accent" />
          </div>

          <div class="focus-row">
            <div class="focus-box focus-box--good" v-if="aiInsight?.highlight">
              <span>当前优势</span>
              <strong>{{ aiInsight.highlight.name }}</strong>
              <small>能力值 {{ aiInsight.highlight.value }} / 100</small>
            </div>
            <div class="focus-box focus-box--risk" v-if="aiInsight?.risk_focus">
              <span>重点短板</span>
              <strong>{{ aiInsight.risk_focus.name }}</strong>
              <small>能力值 {{ aiInsight.risk_focus.value }} / 100</small>
            </div>
          </div>

          <div class="chip-row" v-if="aiInsight?.weak_knowledge_points?.length">
            <span v-for="point in aiInsight.weak_knowledge_points" :key="point" class="chip">{{ point }}</span>
          </div>

          <ul class="suggestion-list" v-if="aiInsight?.coaching_suggestions?.length">
            <li v-for="(tip, idx) in aiInsight.coaching_suggestions" :key="idx">{{ tip }}</li>
          </ul>
          <div v-else class="empty-tip">当前暂无 AI 跟进建议。</div>
        </article>

        <article class="panel task-panel">
          <div class="panel-head">
            <div>
              <h2>学习任务负载</h2>
              <p>了解学生当前被系统安排的复习任务密度。</p>
            </div>
            <BookOpen :size="18" class="panel-accent" />
          </div>

          <div class="task-summary-strip">
            <div>
              <strong>{{ portrait.task_summary.pending_count }}</strong>
              <span>待推进</span>
            </div>
            <div>
              <strong>{{ portrait.task_summary.completed_count }}</strong>
              <span>已完成</span>
            </div>
            <div>
              <strong>{{ portrait.task_summary.ignored_count }}</strong>
              <span>已忽略</span>
            </div>
          </div>

          <div v-if="studyTasks.length" class="task-list">
            <article v-for="task in studyTasks" :key="task.id" class="task-item">
              <div>
                <h3>{{ task.title }}</h3>
                <p>{{ task.task_type || '综合复习' }} · 优先级 {{ task.priority }}</p>
              </div>
              <div class="task-meta">
                <span class="task-status" :class="task.status">{{ task.status }}</span>
                <small>{{ Number(task.estimated_minutes || 0) }} 分钟</small>
              </div>
            </article>
          </div>
          <div v-else class="empty-tip">当前没有可展示的学习任务。</div>
        </article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.view-student-profile {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-bottom: 28px;
}

.hero-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.18), transparent 36%),
    linear-gradient(160deg, #f7fbff 0%, #eef6ff 52%, #f9fcff 100%);
  border: 1px solid #dce9f7;
}

.hero-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-button {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid #d9e5f3;
  background: rgba(255, 255, 255, 0.72);
  color: #1e293b;
}

.hero-eyebrow {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #53708d;
}

.hero-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.hero-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.avatar-badge {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  border-radius: 18px;
  background: linear-gradient(145deg, #2563eb 0%, #0f766e 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
}

.identity-copy h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.05;
  color: #0f172a;
  letter-spacing: -0.04em;
}

.identity-copy p {
  margin: 6px 0 0;
  color: #5a6d84;
  font-size: 13px;
}

.hero-risk {
  min-width: 110px;
  padding: 10px 12px;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  border: 1px solid transparent;
}

.hero-risk.high {
  background: #fff1f2;
  color: #b91c1c;
  border-color: #fecdd3;
}

.hero-risk.medium {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}

.hero-risk.low {
  background: #ecfeff;
  color: #0f766e;
  border-color: #99f6e4;
}

.risk-label {
  font-size: 12px;
  font-weight: 600;
}

.hero-summary {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(190, 218, 245, 0.9);
}

.summary-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.12);
  flex: 0 0 34px;
}

.hero-summary p {
  margin: 0;
  color: #29435c;
  line-height: 1.7;
  font-size: 14px;
}

.state-panel {
  border-radius: 16px;
  border: 1px dashed #d8e4f1;
  background: #f8fbff;
  padding: 28px 16px;
  text-align: center;
  color: #64748b;
}

.state-panel--error {
  color: #b91c1c;
  background: #fff7f7;
  border-color: #fecaca;
}

.stats-grid,
.insight-grid,
.two-column-grid {
  display: grid;
  gap: 12px;
}

.stat-tile,
.panel {
  background: #fff;
  border: 1px solid #dfe8f3;
  border-radius: 18px;
}

.stat-tile {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-icon {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.stat-tile[data-tone='blue'] .stat-icon { background: #e8f1ff; color: #2563eb; }
.stat-tile[data-tone='teal'] .stat-icon { background: #e7fbf8; color: #0f766e; }
.stat-tile[data-tone='amber'] .stat-icon { background: #fff7df; color: #d97706; }
.stat-tile[data-tone='slate'] .stat-icon { background: #eef2f7; color: #475569; }

.stat-label,
.stat-sub,
.panel-head p,
.empty-tip,
.task-item p,
.focus-box small {
  color: #617489;
}

.stat-label { font-size: 12px; }
.stat-value { font-size: 26px; font-weight: 700; color: #0f172a; letter-spacing: -0.04em; }
.stat-sub { margin: 0; font-size: 12px; line-height: 1.5; }

.panel {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-wide { grid-column: span 1; }

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.panel-head h2 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
}

.panel-head p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
}

.panel-accent { color: #2563eb; }

.pill {
  font-size: 11px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 4px 8px;
}

.chart { width: 100%; height: 280px; }
.chart-line { height: 320px; }

.focus-row {
  display: grid;
  gap: 10px;
}

.focus-box {
  padding: 12px;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.focus-box span { font-size: 12px; color: #55697d; }
.focus-box strong { font-size: 18px; color: #0f172a; }
.focus-box--good { background: #effcf8; border: 1px solid #bbf7d0; }
.focus-box--risk { background: #fff7ed; border: 1px solid #fed7aa; }

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border-radius: 999px;
  border: 1px solid #cfe2fb;
  background: #f4f9ff;
  color: #1d4ed8;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
}

.suggestion-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
  font-size: 13px;
  line-height: 1.65;
  color: #334155;
}

.task-summary-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.task-summary-strip > div {
  border-radius: 14px;
  background: #f7fafc;
  border: 1px solid #e3ebf5;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-summary-strip strong {
  font-size: 20px;
  color: #0f172a;
}

.task-summary-strip span {
  font-size: 12px;
  color: #64748b;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-radius: 14px;
  border: 1px solid #e6eef7;
  background: #fbfdff;
  padding: 12px;
}

.task-item h3 {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
}

.task-item p {
  margin: 6px 0 0;
  font-size: 12px;
}

.task-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.task-status {
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 4px 8px;
  text-transform: uppercase;
}

.task-status.pending { background: #eff6ff; color: #1d4ed8; }
.task-status.in_progress { background: #ecfeff; color: #0f766e; }
.task-status.completed { background: #f0fdf4; color: #15803d; }
.task-status.ignored { background: #f8fafc; color: #64748b; }

@media (min-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .insight-grid {
    grid-template-columns: 1.35fr 1fr;
  }

  .panel-wide {
    grid-row: span 2;
  }

  .two-column-grid {
    grid-template-columns: 1.2fr 1fr;
  }

  .focus-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .hero-main,
  .task-item {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-risk,
  .task-meta {
    align-items: flex-start;
  }

  .identity-copy h1 {
    font-size: 26px;
  }

  .chart,
  .chart-line {
    height: 260px;
  }
}
</style>