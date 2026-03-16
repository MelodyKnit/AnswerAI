<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Search, Filter, Calendar } from 'lucide-vue-next'
import http from '@/lib/http'

interface Exam {
  id: string
  title: string
  subject: string
  duration_minutes: number
  status: string
  start_time: string
  end_time: string
  submission_status?: string | null
  has_submitted?: boolean
  retake_request_status?: string | null
  retake_request_created_at?: string | null
}

const exams = ref<Exam[]>([])
const loading = ref(true)
const activeTab = ref('all') // 'all', 'upcoming', 'ongoing', 'finished'

const fetchExams = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 20 }
    if (activeTab.value !== 'all') {
      params.status = activeTab.value
    }
    const res = await http.get(`/student/exams`, {
      params
    })
    exams.value = ((res as any)?.items || []) || []
  } catch (error) {
    console.error('Failed to fetch exams:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchExams()
})

const switchTab = (tab: string) => {
  activeTab.value = tab
  fetchExams()
}

const canApplyRetake = (exam: Exam) => {
  if (!canViewResult(exam)) return false
  return !['pending', 'approved'].includes(String(exam.retake_request_status || ''))
}

const getRetakeStatusLabel = (exam: Exam) => {
  const status = String(exam.retake_request_status || '')
  if (status === 'pending') return '重考申请待审批'
  if (status === 'approved') return '重考申请已通过'
  if (status === 'rejected') return '重考申请被驳回'
  if (status === 'consumed') return '已使用重考机会'
  return ''
}

const submitRetakeRequest = async (exam: Exam) => {
  try {
    const reason = window.prompt('请输入重考申请理由（可选）', '希望再次尝试本场考试，查漏补缺。') || undefined
    await http.post('/student/exams/retake-request', {
      exam_id: Number(exam.id),
      reason,
    })
    await fetchExams()
    alert('重考申请已提交，等待教师审批。')
  } catch (error: any) {
    alert(error?.message || '申请失败，请稍后重试')
  }
}

const parseServerTime = (value: string) => {
  if (!value) return Number.NaN
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`).getTime()
}

const getExamState = (exam: Exam) => {
  if (canViewResult(exam)) return 'completed'
  if (exam.status === 'finished') return 'finished'
  if (exam.status === 'draft') return 'upcoming'
  const now = Date.now()
  const start = parseServerTime(exam.start_time)
  const end = parseServerTime(exam.end_time)
  if (Number.isNaN(start) || Number.isNaN(end)) return exam.status === 'published' ? 'ongoing' : 'upcoming'
  if (now < start) return 'upcoming'
  if (now > end) return 'finished'
  return 'ongoing'
}

const canViewResult = (exam: Exam) => {
  return Boolean(exam.has_submitted || ['submitted', 'reviewed'].includes(String(exam.submission_status || '')))
}

const getActionText = (exam: Exam) => {
  const state = getExamState(exam)
  if (state === 'upcoming') return '查看详情'
  if (state === 'ongoing') return '进入考试'
  return canViewResult(exam) ? '查看成绩' : '已截止'
}

const getExamStateLabel = (exam: Exam) => {
  const state = getExamState(exam)
  if (state === 'completed') return '已完成'
  if (state === 'upcoming') return '未开始'
  if (state === 'finished') return '已结束'
  return '进行中'
}

const formatDate = (dateStr: string) => {
  const t = parseServerTime(dateStr)
  const d = Number.isNaN(t) ? new Date(dateStr) : new Date(t)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="view-exams">
    <!-- Header -->
    <header class="page-header">
      <h1 class="page-title">全部考试</h1>
      <div class="header-actions">
        <button class="icon-button"><Search :size="20" /></button>
        <button class="icon-button"><Filter :size="20" /></button>
      </div>
    </header>

    <!-- Tabs -->
    <div class="tabs">
      <button
        class="tab-item"
        :class="{ active: activeTab === 'all' }"
        @click="switchTab('all')"
      >全部</button>
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'upcoming' }"
        @click="switchTab('upcoming')"
      >待考试</button>
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'ongoing' }"
        @click="switchTab('ongoing')"
      >进行中</button>
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'finished' }"
        @click="switchTab('finished')"
      >已结束</button>
    </div>

    <!-- Exam List -->
    <div class="exam-list" v-if="!loading && exams.length">
      <div v-for="exam in exams" :key="exam.id" class="exam-card">
        <div class="exam-header">
          <h3>{{ exam.title }}</h3>
          <span class="status-badge" :class="getExamState(exam)">{{ getExamStateLabel(exam) }}</span>
        </div>
        <div class="exam-body">
          <div class="meta-row">
            <span class="meta-label">科目</span>
            <span class="meta-value">{{ exam.subject || '综合' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">时长</span>
            <span class="meta-value">{{ exam.duration_minutes }} 分钟</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">时间</span>
            <span class="meta-value time"><Calendar :size="14" class="icon-m" /> {{ formatDate(exam.start_time) }} - {{ formatDate(exam.end_time) }}</span>
          </div>
        </div>
        <div class="exam-footer">
          <RouterLink :to="`/app/student/results/${exam.id}`" class="button button--outline" v-if="canViewResult(exam)">
            {{ getActionText(exam) }}
          </RouterLink>
          <RouterLink :to="`/app/student/exams/${exam.id}/prep`" class="button" v-else-if="getExamState(exam) !== 'finished'">
            {{ getActionText(exam) }}
          </RouterLink>
          <button class="button button--outline button--disabled" v-else disabled>
            {{ getActionText(exam) }}
          </button>
        </div>
        <div v-if="canViewResult(exam)" class="retake-row">
          <span v-if="getRetakeStatusLabel(exam)" class="retake-status">{{ getRetakeStatusLabel(exam) }}</span>
          <button
            v-if="canApplyRetake(exam)"
            class="retake-btn"
            @click="submitRetakeRequest(exam)"
          >申请重考</button>
          <RouterLink
            v-else-if="exam.retake_request_status === 'approved'"
            :to="`/app/student/exams/${exam.id}/prep`"
            class="retake-btn retake-btn--approved"
          >进入重考</RouterLink>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div class="empty-state" v-if="!loading && exams.length === 0">
      <div class="empty-icon">📝</div>
      <p>暂无相关考试</p>
    </div>

    <!-- Loading State -->
    <div class="loading-state" v-if="loading">
      加载中...
    </div>
  </div>
</template>

<style scoped>
.view-exams {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.icon-button {
  background: none;
  border: none;
  color: var(--ink);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 2px;
}

.tab-item {
  background: none;
  border: none;
  font-size: 15px;
  color: var(--ink-soft);
  padding: 8px 4px;
  cursor: pointer;
  position: relative;
  font-weight: 500;
  transition: color 0.2s ease;
}

.tab-item.active {
  color: var(--ink);
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -3px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
  border-radius: 2px;
}

.exam-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.exam-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.exam-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}

.status-badge.upcoming {
  background: var(--bg);
  color: var(--ink-soft);
}

.status-badge.ongoing {
  background: #eef2ff;
  color: #3b82f6;
}

.status-badge.finished {
  background: #f1f5f9;
  color: #64748b;
}

.status-badge.completed {
  background: #ecfdf5;
  color: #047857;
}

.exam-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg);
  padding: 12px;
  border-radius: var(--radius-sm);
}

.meta-row {
  display: flex;
  font-size: 13px;
}

.meta-label {
  color: var(--ink-soft);
  width: 60px;
  flex-shrink: 0;
}

.meta-value {
  color: var(--ink);
  font-weight: 500;
}

.meta-value.time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 400;
}

.icon-m {
  margin-top: -2px;
}

.exam-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

.retake-row {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.retake-status {
  font-size: 12px;
  color: #475569;
}

.retake-btn {
  border: 1px solid #0f766e;
  background: #ecfdf5;
  color: #065f46;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
}

.retake-btn--approved {
  background: #0f766e;
  color: #fff;
}

.button {
  padding: 10px 24px;
  font-size: 14px;
}

.button--outline {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--ink);
  box-shadow: none;
}

.button--outline:hover {
  background: var(--bg);
  transform: translateY(-1px);
}

.button--disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--ink-soft);
  font-size: 14px;
  text-align: center;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 16px;
  opacity: 0.5;
}
</style>
