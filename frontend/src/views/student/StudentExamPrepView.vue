<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock, FileText, Target, AlertCircle, CalendarRange } from 'lucide-vue-next'
import http from '@/lib/http'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const exam = ref<any>(null)
const loading = ref(true)
const starting = ref(false)
const errorMsg = ref('')
const canStart = ref(false)

const parseServerTime = (value: string) => {
  if (!value) return Number.NaN
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`).getTime()
}

const formatDateTime = (value: string) => {
  const timestamp = parseServerTime(value)
  if (Number.isNaN(timestamp)) return '--'
  const d = new Date(timestamp)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const examTimeRangeText = () => {
  if (!exam.value?.start_time || !exam.value?.end_time) return '未设置'
  return `${formatDateTime(String(exam.value.start_time))} - ${formatDateTime(String(exam.value.end_time))}`
}

onMounted(async () => {
  try {
    const res = await http.get('/student/exams/detail', { params: { exam_id: examId } })
    exam.value = (res as any)?.exam || res
    canStart.value = Boolean((res as any)?.can_start)
  } catch (error: any) {
    errorMsg.value = error.response?.data?.message || '无法获取考试信息'
  } finally {
    loading.value = false
  }
})

const startExam = async () => {
  if (!canStart.value) {
    errorMsg.value = '当前不在考试开放时间内，暂不能开始。'
    return
  }
  starting.value = true
  errorMsg.value = ''
  try {
    const res = await http.post('/student/exams/start', { exam_id: examId })
    const sessionId = (res as any)?.submission?.id
    router.push(`/app/student/exams/${examId}/session/${sessionId}`)
  } catch (error: any) {
    errorMsg.value = error.response?.data?.message || '无法开始考试，请稍后重试'
    starting.value = false
  }
}
</script>

<template>
  <div class="view-exam-prep">
    <header class="top-nav">
      <button class="icon-button" @click="router.back()">
        <ArrowLeft :size="24" />
      </button>
      <span class="nav-title">考试准备</span>
      <div style="width: 24px"></div>
    </header>

    <div v-if="loading" class="loading-state">
      加载中...
    </div>

    <div v-else-if="errorMsg" class="error-state">
      <AlertCircle :size="40" class="error-icon" />
      <p>{{ errorMsg }}</p>
      <button class="button" @click="router.back()" style="margin-top: 16px;">返回列表</button>
    </div>

    <div v-else-if="exam" class="prep-content">
      <h1 class="exam-title">{{ exam.title }}</h1>
      
      <div class="info-grid">
        <div class="info-item">
          <Clock :size="20" class="info-icon" />
          <div class="info-text">
            <span class="label">考试时长</span>
            <span class="value">{{ exam.duration_minutes }} 分钟</span>
          </div>
        </div>
        <div class="info-item">
          <Target :size="20" class="info-icon" />
          <div class="info-text">
            <span class="label">总分</span>
            <span class="value">{{ exam.total_score }} 分</span>
          </div>
        </div>
        <div class="info-item">
          <FileText :size="20" class="info-icon" />
          <div class="info-text">
            <span class="label">题目数量</span>
            <span class="value">{{ exam.question_count }} 题</span>
          </div>
        </div>
        <div class="info-item">
          <CalendarRange :size="20" class="info-icon" />
          <div class="info-text">
            <span class="label">考试时间区间</span>
            <span class="value">{{ examTimeRangeText() }}</span>
          </div>
        </div>
      </div>

      <div class="instructions-card">
        <h3>考试须知</h3>
        <div class="instructions-text">
          {{ exam.instructions || '1. 考试期间请勿切换应用\n2. 遇到问题请举手示意\n3. 答题完毕后请仔细检查后提交' }}
        </div>
      </div>

      <div class="bottom-action">
        <p v-if="!canStart" class="start-hint">当前不在考试开放时间，暂不可开始。</p>
        <button 
          class="button button-large" 
          @click="startExam" 
          :disabled="starting || !canStart"
        >
          {{ starting ? '准备中...' : '开始考试' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-exam-prep {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  height: auto;
  background: var(--bg);
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  width: min(100%, 480px);
  margin: 0 auto;
  box-sizing: border-box;
  overflow-y: auto;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
}

.icon-button {
  background: none;
  border: none;
  color: var(--ink);
  padding: 4px;
}

.nav-title {
  font-size: 17px;
  font-weight: 500;
  color: var(--ink);
}

.prep-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 0;
}

.exam-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
  margin-top: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
}

.info-icon {
  color: var(--accent);
}

.info-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 13px;
  color: var(--ink-soft);
}

.value {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink);
}

.instructions-card {
  background: var(--accent-light);
  padding: 20px;
  border-radius: var(--radius-lg);
  margin-top: 8px;
}

.instructions-card h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
}

.instructions-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink-soft);
  white-space: pre-wrap;
}

.bottom-action {
  margin-top: 8px;
  padding-top: 8px;
}

.start-hint {
  margin: 0 0 10px;
  text-align: center;
  color: #b45309;
  font-size: 13px;
}

.button-large {
  width: 100%;
  padding: 16px;
  font-size: 16px;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--ink-soft);
}

.error-icon {
  color: #ef4444;
  margin-bottom: 16px;
}

@media (max-width: 420px) {
  .view-exam-prep {
    padding-left: 12px;
    padding-right: 12px;
  }

  .exam-title {
    font-size: 21px;
  }

  .info-item {
    padding: 14px;
    gap: 12px;
  }
}
</style>
