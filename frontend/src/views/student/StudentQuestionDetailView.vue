<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Brain, CheckCircle2, CircleAlert, RefreshCw } from 'lucide-vue-next'
import http from '@/lib/http'
import ImageLightbox from '@/components/common/ImageLightbox.vue'
import { renderRichContent as renderRichContentHtml } from '@/utils/richContent'

const route = useRoute()
const router = useRouter()

const examId = Number(route.params.id)
const questionId = computed(() => Number(route.params.questionId))

const loading = ref(true)
const errorMsg = ref('')
const wrongQuestions = ref<Array<{ question_id: number, score: number }>>([])
const detailLoading = ref(false)
const questionDetail = ref<any>(null)
const isLightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('题目图片')

const apiBase = String(import.meta.env.VITE_API_URL || '/api/v1')

const renderRichContent = (value: unknown) => {
  return renderRichContentHtml(value, {
    apiBase,
    imageClassName: 'analysis-rich-image',
    imageAlt: '题目图片',
  })
}

const handleImageClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  const image = target?.closest('img') as HTMLImageElement | null
  if (!image) return
  event.preventDefault()
  event.stopPropagation()
  lightboxSrc.value = image.currentSrc || image.src
  lightboxAlt.value = image.alt || '题目图片'
  isLightboxOpen.value = true
}

const normalizedQuestionType = computed(() => {
  const t = String(questionDetail.value?.question?.question_type || '')
  if (t === 'single_choice') return '单选题'
  if (t === 'multiple_choice') return '多选题'
  if (t === 'judge') return '判断题'
  if (t === 'blank') return '填空题'
  return '主观题'
})

const correctnessText = computed(() => {
  const v = questionDetail.value?.answer?.is_correct
  if (v === true) return '本题已掌握'
  if (v === false) return '本题作答错误'
  return '本题待复核'
})

const scoreText = computed(() => {
  const gain = Number(questionDetail.value?.answer?.gain_score || 0)
  const full = Number(questionDetail.value?.answer?.full_score || 0)
  return `${gain} / ${full}`
})

const optionList = computed(() => (questionDetail.value?.question?.options || []) as Array<any>)

const formatAnswer = (value: any) => {
  if (Array.isArray(value)) return value.join('、')
  if (value === null || value === undefined || value === '') return '未作答'
  return String(value)
}

const fetchQuestionDetail = async () => {
  if (!questionId.value) return
  try {
    detailLoading.value = true
    const res = await http.get('/student/results/question-analysis', {
      params: {
        exam_id: examId,
        question_id: questionId.value,
      },
    })
    questionDetail.value = res
  } catch (error: any) {
    errorMsg.value = error?.message || '单题解析加载失败'
  } finally {
    detailLoading.value = false
  }
}

const currentIndex = computed(() => {
  return wrongQuestions.value.findIndex((item) => item.question_id === questionId.value)
})

const currentQuestion = computed(() => {
  if (currentIndex.value < 0) return null
  return wrongQuestions.value[currentIndex.value]
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < wrongQuestions.value.length - 1)

const jumpTo = async (index: number) => {
  const target = wrongQuestions.value[index]
  if (!target) return
  await router.replace(`/app/student/results/${examId}/question/${target.question_id}`)
  await fetchQuestionDetail()
}

const goPrev = async () => {
  if (!hasPrev.value) return
  await jumpTo(currentIndex.value - 1)
}

const goNext = async () => {
  if (!hasNext.value) return
  await jumpTo(currentIndex.value + 1)
}

onMounted(async () => {
  try {
    const res = await http.get('/student/results/overview', { params: { exam_id: examId } })
    const rows = (res as any)?.type_score_distribution || []
    wrongQuestions.value = rows
      .filter((item: any) => Number(item?.score || 0) <= 0)
      .map((item: any) => ({ question_id: Number(item.question_id), score: Number(item.score || 0) }))
      .filter((item: { question_id: number }) => Number.isFinite(item.question_id))

    await fetchQuestionDetail()
  } catch (error: any) {
    errorMsg.value = error?.message || '无法加载错题解析数据'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="analysis-view">
    <div v-if="loading" class="state-box">加载中...</div>
    <div v-else-if="errorMsg" class="state-box">{{ errorMsg }}</div>
    <div v-else-if="wrongQuestions.length === 0" class="state-box">当前没有可解析的错题</div>
    <div v-else-if="!currentQuestion" class="state-box">题目不存在或已被移除</div>
    <div v-else class="content-shell">
      <section class="summary-card">
        <p class="index-text">第 {{ currentIndex + 1 }} / {{ wrongQuestions.length }} 题</p>
        <div class="summary-main">
          <h2>题号 {{ currentQuestion.question_id }}</h2>
          <span class="type-chip">{{ normalizedQuestionType }}</span>
        </div>
        <div class="summary-meta">
          <span class="score-pill">得分：{{ scoreText }}</span>
          <span class="status-pill" :class="{ ok: questionDetail?.answer?.is_correct === true, bad: questionDetail?.answer?.is_correct === false }">{{ correctnessText }}</span>
        </div>
      </section>

      <section v-if="detailLoading" class="state-box">正在加载单题详情...</section>

      <template v-else-if="questionDetail">
        <section class="panel-card">
          <div class="panel-title-row">
            <h3>题干与选项</h3>
          </div>
          <div class="stem-text" v-html="renderRichContent(questionDetail.question.stem)" @click.capture="handleImageClick"></div>
          <div v-if="optionList.length" class="option-list">
            <div v-for="opt in optionList" :key="opt.key" class="option-item">
              <span class="opt-key">{{ opt.key }}</span>
              <span v-html="renderRichContent(opt.content)" @click.capture="handleImageClick"></span>
            </div>
          </div>
        </section>

        <section class="panel-card answer-compare">
          <div class="panel-title-row">
            <h3>答案对比</h3>
            <CheckCircle2 v-if="questionDetail.answer.is_correct === true" :size="16" class="ok-icon" />
            <CircleAlert v-else :size="16" class="warn-icon" />
          </div>
          <div class="answer-grid">
            <div class="answer-cell">
              <p class="label">你的答案</p>
              <p class="value">{{ formatAnswer(questionDetail.answer.student_answer) }}</p>
            </div>
            <div class="answer-cell">
              <p class="label">标准答案</p>
              <p class="value">{{ formatAnswer(questionDetail.answer.standard_answer) }}</p>
            </div>
          </div>
        </section>

        <section class="panel-card">
          <div class="panel-title-row">
            <Brain :size="16" class="brain-icon" />
            <h3>AI 诊断建议</h3>
          </div>
          <p class="diagnosis-type">诊断结果：{{ questionDetail.diagnosis.type }}</p>
          <p class="diagnosis-reason">{{ questionDetail.diagnosis.reason }}</p>
          <ul class="step-list">
            <li v-for="(item, idx) in questionDetail.diagnosis.fix_steps" :key="`step-${idx}`">{{ item }}</li>
          </ul>
          <div class="next-actions">
            <button class="button button--ghost" @click="router.push(`/app/student/ai-chat?examId=${examId}&questionId=${questionId}`)">AI追问</button>
            <button class="button button--ghost" @click="router.push(`/app/student/study-plan`)">加入复习计划</button>
          </div>
        </section>

        <section class="panel-card">
          <div class="panel-title-row">
            <h3>标准解析</h3>
          </div>
          <p class="analysis-text">{{ questionDetail.question.analysis || '暂无解析，请联系教师补充。' }}</p>
        </section>
      </template>

      <div class="actions">
        <button class="button button--outline" :disabled="!hasPrev" @click="goPrev">上一题</button>
        <button class="button button--ghost" @click="fetchQuestionDetail">
          <RefreshCw :size="14" />
          刷新解析
        </button>
        <button class="button" :disabled="!hasNext" @click="goNext">下一题</button>
      </div>
    </div>

    <ImageLightbox v-model="isLightboxOpen" :src="lightboxSrc" :alt="lightboxAlt" />
  </div>
</template>

<style scoped>
.analysis-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: calc(100% + 48px);
  width: calc(100% + 32px);
  margin: -24px -16px;
  padding: calc(14px + 24px) 16px calc(20px + env(safe-area-inset-bottom));
  background:
    radial-gradient(110% 44% at 104% -10%, rgba(37, 99, 235, 0.16), rgba(37, 99, 235, 0) 60%),
    linear-gradient(180deg, #f7faff 0%, #eef3fa 100%);
}

.state-box,
.panel-card,
.summary-card {
  background: #fff;
  border: 1px solid #d8e1ef;
  border-radius: 14px;
  padding: 14px;
}

.content-shell {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-card {
  background: linear-gradient(160deg, #ffffff, #eef6ff);
}

.index-text {
  margin: 0 0 10px;
  color: var(--ink-soft);
  font-size: 13px;
}

.summary-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.summary-main h2 {
  margin: 0;
  font-size: 32px;
  letter-spacing: -0.03em;
}

.type-chip {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #1d4ed8;
  background: #dbeafe;
}

.summary-meta {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.score-pill,
.status-pill {
  font-size: 12px;
  border-radius: 999px;
  padding: 4px 10px;
  background: #f1f5f9;
  color: #334155;
}

.status-pill.ok {
  color: #065f46;
  background: #d1fae5;
}

.status-pill.bad {
  color: #991b1b;
  background: #fee2e2;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-start;
}

.panel-title-row h3 {
  margin: 0;
  font-size: 15px;
}

.stem-text,
.analysis-text,
.diagnosis-reason {
  margin: 10px 0 0;
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}

.option-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 9px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 14px;
  color: #334155;
}

:deep(.analysis-rich-image) {
  display: block;
  max-width: 100%;
  margin: 10px 0;
  border: 1px solid #dbe4ef;
  border-radius: 10px;
  background: #fff;
  cursor: zoom-in;
}

.opt-key {
  min-width: 20px;
  font-weight: 700;
  color: #1d4ed8;
}

.answer-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.answer-cell {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  padding: 10px;
}

.answer-cell .label {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.answer-cell .value {
  margin: 6px 0 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
  line-height: 1.5;
}

.ok-icon {
  color: #059669;
}

.warn-icon {
  color: #dc2626;
}

.brain-icon {
  color: #2563eb;
}

.diagnosis-type {
  margin: 10px 0 0;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.step-list {
  margin: 10px 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #334155;
  font-size: 13px;
  line-height: 1.5;
}

.next-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

@media (max-width: 640px) {
  .summary-main h2 {
    font-size: 28px;
  }

  .answer-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 768px) {
  .analysis-view {
    width: calc(100% + 64px);
    margin: -40px -32px;
    min-height: calc(100% + 80px);
    padding: calc(16px + 40px) 32px calc(24px + env(safe-area-inset-bottom));
  }
}
</style>
