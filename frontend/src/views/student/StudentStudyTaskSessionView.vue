<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, BookOpen, CheckCircle2, Clock3, Sparkles, Target } from 'lucide-vue-next'
import http from '@/lib/http'
import { mapStudyTaskTypeLabel } from '@/utils/studyTask'
import { useUiDialog } from '@/composables/useUiDialog'

const route = useRoute()
const router = useRouter()

const taskId = Number(route.params.taskId)
const loading = ref(true)
const saving = ref(false)
const task = ref<any | null>(null)
const coachingData = ref<any>({ coach_summary: '', drill_steps: [], practice_items: [] })
const stepChecked = ref<Record<string, boolean>>({})
const reflection = ref('')
const revealState = ref<Record<string, boolean>>({})
const masteryState = ref<Record<string, 'mastered' | 'unmastered'>>({})
const ui = useUiDialog()

const formatAnswer = (value: any) => {
  if (Array.isArray(value)) return value.join('、')
  if (value === null || value === undefined || value === '') return '未提供'
  return String(value)
}

const getPracticeStatusText = (status?: string) => {
  if (status === 'unanswered') return '未作答'
  if (status === 'wrong') return '答错题'
  return '复习题'
}

const activeSteps = computed(() => {
  const serverSteps = (coachingData.value?.drill_steps || []) as string[]
  if (serverSteps.length) return serverSteps
  const mins = Number(task.value?.estimated_minutes || 20)
  return [`阅读任务目标`, `计时 ${mins} 分钟完成专项练习`, '核对答案并记录错因', '提交复盘']
})

const practiceItems = computed(() => (coachingData.value?.practice_items || []) as Array<any>)

const displayTaskType = computed(() => {
  const preferred = String(coachingData.value?.task?.task_type_label || '').trim()
  if (preferred) return preferred
  return mapStudyTaskTypeLabel(coachingData.value?.task?.task_type || task.value?.task_type)
})

const displayTaskTitle = computed(() => {
  const rawTitle = String(task.value?.title || '').trim()
  if (!rawTitle) return '任务复习'
  if ((coachingData.value?.task?.task_type || task.value?.task_type) !== 'wrong_question_review') {
    return rawTitle
  }
  const targetQuestionCount = Number(coachingData.value?.task?.target_question_count || 0)
  const questionCount = targetQuestionCount > 0 ? targetQuestionCount : practiceItems.value.length
  const normalizedTitle = rawTitle.replace(/（\d+题）/g, '').replace(/\(\d+题\)/g, '').trim()
  if (questionCount <= 0) return normalizedTitle
  return `${normalizedTitle}（${questionCount}题）`
})

const progressPercent = computed(() => {
  const steps = activeSteps.value
  if (!steps.length) return 0
  let done = 0
  for (let i = 0; i < steps.length; i += 1) {
    if (stepChecked.value[`step-${i}`]) done += 1
  }
  return Math.round((done / steps.length) * 100)
})

const practiceCompletion = computed(() => {
  const total = practiceItems.value.length
  if (!total) return 0
  let done = 0
  for (const item of practiceItems.value) {
    const key = `q-${item.question_id}`
    if (masteryState.value[key] === 'mastered' || masteryState.value[key] === 'unmastered') done += 1
  }
  return Math.round((done / total) * 100)
})

const masteredCount = computed(() => {
  let count = 0
  for (const value of Object.values(masteryState.value)) {
    if (value === 'mastered') count += 1
  }
  return count
})

const canSubmitReview = computed(() => progressPercent.value >= 50 && (practiceItems.value.length === 0 || practiceCompletion.value >= 60))

const toggleReveal = (questionId: number) => {
  const key = `q-${questionId}`
  revealState.value[key] = !revealState.value[key]
}

const markMastery = (questionId: number, status: 'mastered' | 'unmastered') => {
  masteryState.value[`q-${questionId}`] = status
}

const jumpToAnalysis = (item: any) => {
  const examId = Number(item?.exam_id || 0)
  const questionId = Number(item?.question_id || 0)
  if (!examId || !questionId) return
  router.push(`/app/student/results/${examId}/question/${questionId}`)
}

const loadTask = async () => {
  const taskRes: any = await http.get('/student/study-tasks')
  const merged = [...(taskRes?.tasks || []), ...(taskRes?.ignored_tasks || [])]
  const current = merged.find((item: any) => Number(item.id) === taskId)
  if (!current) {
    throw new Error('任务不存在或已被移除')
  }

  const [, coachRes] = await Promise.all([
    http.post('/student/study-tasks/action', { task_id: taskId, action: 'start' }),
    http.get('/student/study-tasks/coaching', { params: { task_id: taskId } }),
  ])

  task.value = {
    ...current,
    status: 'in_progress',
  }
  coachingData.value = coachRes || { coach_summary: '', drill_steps: [], practice_items: [] }
}

const goBack = () => {
  router.push('/app/student/study-plan')
}

const pauseTask = async () => {
  if (!task.value) return
  try {
    saving.value = true
    await http.post('/student/study-tasks/action', { task_id: task.value.id, action: 'pause' })
    router.push('/app/student/study-plan')
  } catch (error) {
    console.error('暂停复习任务失败', error)
    await ui.alert('暂停失败，请稍后重试', { tone: 'error' })
  } finally {
    saving.value = false
  }
}

const completeTask = async () => {
  if (!task.value) return
  try {
    saving.value = true
    await http.post('/student/study-tasks/action', {
      task_id: task.value.id,
      action: 'complete',
      feedback: reflection.value || undefined,
    })
    router.push('/app/student/study-plan')
  } catch (error) {
    console.error('完成复习任务失败', error)
    await ui.alert('提交复盘失败，请稍后重试', { tone: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadTask()
  } catch (error: any) {
    console.error('加载复习任务失败', error)
    await ui.alert(error?.message || '加载复习任务失败', { tone: 'error' })
    router.push('/app/student/study-plan')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="study-session-view">
    <header class="session-header">
      <button class="back-btn" @click="goBack">
        <ArrowLeft :size="18" />
        返回计划
      </button>
      <span class="session-progress">步骤进度 {{ progressPercent }}%</span>
    </header>

    <div v-if="loading" class="state-card">加载中...</div>

    <template v-else-if="task">
      <section class="hero-card">
        <div class="hero-kicker-row">
          <span class="hero-chip">
            <Sparkles :size="14" />
            AI 复习教练
          </span>
          <span class="hero-time">{{ task.estimated_minutes || 20 }} 分钟</span>
        </div>
        <h1>{{ displayTaskTitle }}</h1>
        <p class="hero-desc">{{ coachingData.coach_summary || task.content || '按步骤完成本次复习。' }}</p>
        <div class="hero-meta">
          <span><Target :size="14" /> {{ displayTaskType }}</span>
          <span><Clock3 :size="14" /> 建议专注 {{ task.estimated_minutes || 20 }} 分钟</span>
          <span><BookOpen :size="14" /> 当前状态 {{ task.status === 'in_progress' ? '进行中' : '待开始' }}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
        </div>
      </section>

      <section class="panel-card">
        <h2>复习步骤</h2>
        <div class="step-list">
          <label v-for="(step, idx) in activeSteps" :key="idx" class="step-item">
            <input type="checkbox" v-model="stepChecked[`step-${idx}`]" />
            <span>{{ step }}</span>
          </label>
        </div>
      </section>

      <section v-if="practiceItems.length" class="panel-card practice-panel">
        <div class="practice-head">
          <h2>今日针对题</h2>
          <span>完成度 {{ practiceCompletion }}% · 已掌握 {{ masteredCount }}/{{ practiceItems.length }}</span>
        </div>
        <article v-for="item in practiceItems" :key="item.question_id" class="practice-card">
          <div class="practice-top-row">
            <span class="practice-status-badge" :class="`status-${item.practice_status || 'review'}`">
              {{ getPracticeStatusText(item.practice_status) }}
            </span>
          </div>
          <p class="practice-stem">{{ item.stem }}</p>
          <div class="practice-actions">
            <button class="tiny-btn" @click="toggleReveal(item.question_id)">
              {{ revealState[`q-${item.question_id}`] ? '收起答案' : '查看答案' }}
            </button>
            <button class="tiny-btn" @click="jumpToAnalysis(item)">去错题解析</button>
            <button class="tiny-btn" :class="{ active: masteryState[`q-${item.question_id}`] === 'mastered' }" @click="markMastery(item.question_id, 'mastered')">我会了</button>
            <button class="tiny-btn" :class="{ active: masteryState[`q-${item.question_id}`] === 'unmastered' }" @click="markMastery(item.question_id, 'unmastered')">还不会</button>
          </div>
          <div v-if="revealState[`q-${item.question_id}`]" class="practice-answer">
            <p><strong>标准答案：</strong>{{ formatAnswer(item.standard_answer) }}</p>
            <p><strong>上次作答：</strong>{{ formatAnswer(item.last_student_answer) }}</p>
            <p><strong>解析：</strong>{{ item.analysis || '暂无解析，请结合课堂笔记复盘。' }}</p>
          </div>
        </article>
      </section>

      <section class="panel-card reflection-panel">
        <h2>复盘输入</h2>
        <textarea v-model="reflection" rows="4" placeholder="例如：我在第2步遇到概念混淆，已通过错题对比理解..." />
      </section>

      <footer class="action-bar">
        <button class="ghost-btn" :disabled="saving" @click="pauseTask">稍后继续</button>
        <button class="start-btn" :disabled="saving || !canSubmitReview" @click="completeTask">
          <CheckCircle2 :size="16" />
          {{ saving ? '提交中...' : '完成并提交复盘' }}
        </button>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.study-session-view {
  --paper: #f6f7f4;
  --ink-900: #1f2a1f;
  --ink-600: #5f6d5f;
  --line-soft: #d9dfd4;
  --brand: #1d6b4f;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: calc(100% + 48px);
  width: calc(100% + 32px);
  margin: -24px -16px;
  padding: calc(14px + 24px) 14px calc(26px + env(safe-area-inset-bottom));
  background:
    radial-gradient(circle at 90% -10%, rgba(29, 107, 79, 0.14), transparent 38%),
    linear-gradient(180deg, #fbfcfa 0%, var(--paper) 100%);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.back-btn {
  border: 1px solid #d7dfd8;
  background: #fff;
  color: #335245;
  border-radius: 999px;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.session-progress {
  font-size: 12px;
  color: var(--ink-600);
}

.state-card,
.hero-card,
.panel-card {
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  background: #fff;
  padding: 14px;
}

.hero-card {
  background: linear-gradient(160deg, #ffffff 0%, #edf7f1 100%);
}

.hero-kicker-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--brand);
  background: #e8f4ee;
  border: 1px solid #c8dfd2;
  border-radius: 999px;
  padding: 3px 10px;
}

.hero-time {
  font-size: 12px;
  color: var(--ink-600);
}

.hero-card h1 {
  margin: 12px 0 6px;
  font-size: 28px;
  line-height: 1.1;
  color: var(--ink-900);
}

.hero-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #3b5648;
}

.hero-meta {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--ink-600);
}

.hero-meta span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.progress-track {
  margin-top: 12px;
  height: 9px;
  border-radius: 999px;
  background: #e1ece5;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #0f766e, #1f8a63);
}

.panel-card h2 {
  margin: 0 0 10px;
  font-size: 16px;
  color: var(--ink-900);
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink-900);
}

.practice-panel {
  background: #f5faf7;
}

.practice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.practice-head span {
  font-size: 12px;
  color: var(--ink-600);
}

.practice-card {
  border: 1px solid #cddfd5;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.practice-card + .practice-card {
  margin-top: 8px;
}

.practice-top-row {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 6px;
}

.practice-status-badge {
  font-size: 11px;
  line-height: 1;
  padding: 5px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-weight: 600;
}

.practice-status-badge.status-unanswered {
  color: #9a3412;
  background: #fff7ed;
  border-color: #fed7aa;
}

.practice-status-badge.status-wrong {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.practice-status-badge.status-review {
  color: #334155;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.practice-stem {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2a1f;
}

.practice-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tiny-btn {
  border: 1px solid #cfdad4;
  background: #fff;
  color: #486252;
  font-size: 12px;
  padding: 6px 9px;
  border-radius: 8px;
}

.tiny-btn.active {
  background: #1d6b4f;
  border-color: #1d6b4f;
  color: #fff;
}

.practice-answer {
  margin-top: 8px;
  border-top: 1px dashed #cfe0d6;
  padding: 8px;
  background: #fafdfb;
  border-radius: 8px;
}

.practice-answer p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: #40584b;
}

.reflection-panel textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d8e3db;
  border-radius: 10px;
  padding: 10px;
  font-size: 13px;
  resize: vertical;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.ghost-btn {
  border: 1px solid #d8e3db;
  background: #fff;
  color: var(--ink-600);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
}

.start-btn {
  border: 1px solid #195b43;
  background: linear-gradient(180deg, #1f7a59, #1d6b4f);
  color: #fff;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ghost-btn:disabled,
.start-btn:disabled,
.tiny-btn:disabled,
.back-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (min-width: 768px) {
  .study-session-view {
    width: calc(100% + 64px);
    margin: -40px -32px;
    min-height: calc(100% + 80px);
    padding: calc(16px + 40px) 18px calc(28px + env(safe-area-inset-bottom));
  }
}
</style>
