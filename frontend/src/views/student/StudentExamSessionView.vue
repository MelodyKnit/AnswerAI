<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, ChevronLeft, ChevronRight, Check } from 'lucide-vue-next'
import http from '@/lib/http'
import ImageLightbox from '@/components/common/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)
const submissionId = Number(route.params.sessionId)

const questions = ref<any[]>([])
const currentIndex = ref(0)
const loading = ref(true)
const submitting = ref(false)
const remainingSeconds = ref(0)
const isLightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('题目插图')
const isAnswerSheetOpen = ref(false)
const questionEnterAt = ref(Date.now())
const paperLoaded = ref(false)
let countdownTimer: number | null = null

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
const QUESTION_TYPE_ORDER = ['single_choice', 'multiple_choice', 'fill_in_the_blank', 'short_answer']
const TEXT_QUESTION_TYPES = new Set(['fill_in_the_blank', 'fill_blank', 'blank', 'short_answer', 'essay', 'material'])

const getQuestionTypeLabel = (type: string) => {
  if (type === 'single_choice') return '单选题'
  if (type === 'multiple_choice') return '多选题'
  if (type === 'fill_in_the_blank' || type === 'fill_blank') return '填空题'
  if (type === 'short_answer') return '简答题'
  return '其他题型'
}

const groupedQuestionSheet = computed(() => {
  const groups = new Map<string, Array<{ q: any; idx: number }>>()
  questions.value.forEach((q, idx) => {
    const t = String(q?.type || 'other')
    if (!groups.has(t)) groups.set(t, [])
    groups.get(t)!.push({ q, idx })
  })

  const ordered = Array.from(groups.keys()).sort((a, b) => {
    const ia = QUESTION_TYPE_ORDER.indexOf(a)
    const ib = QUESTION_TYPE_ORDER.indexOf(b)
    const ra = ia === -1 ? Number.MAX_SAFE_INTEGER : ia
    const rb = ib === -1 ? Number.MAX_SAFE_INTEGER : ib
    return ra - rb
  })

  return ordered.map((type) => ({
    type,
    label: getQuestionTypeLabel(type),
    items: groups.get(type) || [],
  }))
})

const formattedRemainingTime = computed(() => {
  const total = Math.max(0, remainingSeconds.value)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const isTimeWarning = computed(() => remainingSeconds.value <= 300)
const answeredCount = computed(() => {
  return questions.value.filter((q) => isQuestionAnswered(q.question_id)).length
})

const apiBase = String(import.meta.env.VITE_API_URL || '/api/v1')

const getBackendOrigin = () => {
  if (/^https?:\/\//i.test(apiBase)) {
    try {
      return new URL(apiBase).origin
    } catch {
      return ''
    }
  }
  return ''
}

const normalizeAssetUrl = (rawUrl: string) => {
  const trimmed = rawUrl.trim()
  if (!trimmed) return ''
  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith('//') || trimmed.startsWith('blob:')) {
    return trimmed
  }
  const backendOrigin = getBackendOrigin()
  if (trimmed.startsWith('/')) {
    return backendOrigin ? `${backendOrigin}${trimmed}` : trimmed
  }
  // 兼容导入题库中的裸文件名，如 t175.png
  if (/\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(trimmed)) {
    const path = `/uploads/subject-import/${trimmed.replace(/^\/+/, '')}`
    return backendOrigin ? `${backendOrigin}${path}` : path
  }
  return backendOrigin ? `${backendOrigin}/${trimmed.replace(/^\/+/, '')}` : trimmed
}

const escapeHtml = (value: string) => {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderFromRichBlocks = (raw: string) => {
  const trimmed = raw.trim()
  if (!trimmed.startsWith('[') || !trimmed.endsWith(']')) return ''
  try {
    const blocks = JSON.parse(trimmed)
    if (!Array.isArray(blocks)) return ''
    const html = blocks
      .map((item: any) => {
        const blockType = String(item?.type || '').toLowerCase()
        const blockContent = String(item?.content || '')
        if (blockType === 'image') {
          const src = normalizeAssetUrl(blockContent)
          return src ? `<img class="session-rich-image" src="${src}" alt="题目插图" />` : ''
        }
        return `<span class="session-rich-text">${escapeHtml(blockContent)}</span>`
      })
      .filter(Boolean)
      .join('')
    return html
  } catch {
    return ''
  }
}

const renderQuestionContent = (value: unknown) => {
  const raw = String(value ?? '')
  if (!raw.trim()) return ''

  const fromBlocks = renderFromRichBlocks(raw)
  if (fromBlocks) {
    return fromBlocks
  }

  // 兼容 markdown 图片语法
  const escaped = escapeHtml(raw)
  return escaped
    .replace(/!\[[^\]]*\]\(([^)]+)\)/g, (_, src) => {
      const normalized = normalizeAssetUrl(String(src || ''))
      return normalized ? `<img class="session-rich-image" src="${normalized}" alt="题目插图" />` : ''
    })
    .replace(/\n/g, '<br />')
}

// Track answers locally
const answers = ref<Record<number, any>>({})

onMounted(async () => {
  let loadedOk = false
  try {
    const res = await http.get('/student/exams/paper', {
      params: { exam_id: examId, submission_id: submissionId }
    })
    questions.value = ((res as any)?.questions || []) || []
    remainingSeconds.value = Number((res as any)?.remaining_seconds || 0)
    paperLoaded.value = true
    loadedOk = true
    
    // Initialize empty answers
    questions.value.forEach(q => {
      answers.value[q.question_id] = q.type === 'multiple_choice' ? [] : ''
    })
  } catch (error) {
    console.error('Failed to load exam paper:', error)
    alert('无法加载试卷数据，可能该考试已提交或已结束。')
    router.replace(`/app/student/results/${examId}`)
  } finally {
    loading.value = false
  }

  questionEnterAt.value = Date.now()
  if (loadedOk && remainingSeconds.value > 0) {
    startCountdown()
  }
})

onBeforeUnmount(() => {
  if (countdownTimer !== null) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
})

const startCountdown = () => {
  if (!paperLoaded.value) return
  if (countdownTimer !== null) {
    window.clearInterval(countdownTimer)
  }
  countdownTimer = window.setInterval(() => {
    if (remainingSeconds.value <= 0) {
      window.clearInterval(countdownTimer as number)
      countdownTimer = null
      if (!submitting.value && paperLoaded.value) {
        submitExam(true)
      }
      return
    }
    remainingSeconds.value -= 1
  }, 1000)
}

const saveCurrentAnswer = async () => {
  if (!currentQuestion.value) return
  
  const qId = currentQuestion.value.question_id
  const val = answers.value[qId]
  const spentSeconds = Math.max(1, Math.round((Date.now() - questionEnterAt.value) / 1000))
  
  try {
    await http.post('/student/exams/answer/save', {
      exam_id: examId,
      submission_id: submissionId,
      question_id: qId,
      answer: currentQuestion.value.type === 'multiple_choice' ? val : (currentQuestion.value.type === 'single_choice' ? val : null),
      answer_text: TEXT_QUESTION_TYPES.has(String(currentQuestion.value.type || '')) ? val : null,
      spent_seconds: spentSeconds
    })
    questionEnterAt.value = Date.now()
  } catch (err) {
    console.error('Failed to save answer:', err)
  }
}

const nextQuestion = async () => {
  await saveCurrentAnswer()
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
  }
}

const prevQuestion = async () => {
  await saveCurrentAnswer()
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

const submitExam = async (forced = false) => {
  if (!forced && !confirm('确定要交卷吗？')) return
  
  await saveCurrentAnswer()
  submitting.value = true
  
  try {
    await http.post('/student/exams/submit', {
      exam_id: examId,
      submission_id: submissionId,
      confirm_submit: true
    })
    if (countdownTimer !== null) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }
    router.replace(`/app/student/results/${examId}`)
  } catch (error) {
    console.error('Submit failed', error)
    alert(forced ? '自动交卷失败，请立即手动交卷' : '交卷失败，请重试')
    submitting.value = false
  }
}

const handleSubmitClick = async () => {
  await submitExam(false)
}

const isQuestionAnswered = (questionId: number) => {
  const value = answers.value[questionId]
  if (Array.isArray(value)) {
    return value.length > 0
  }
  if (typeof value === 'string') {
    return value.trim().length > 0
  }
  return value !== null && value !== undefined && String(value).trim().length > 0
}

const goToQuestion = async (index: number) => {
  await saveCurrentAnswer()
  currentIndex.value = index
  isAnswerSheetOpen.value = false
}

const handleRichImageClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  const image = target?.closest('img') as HTMLImageElement | null
  if (!image) return
  event.preventDefault()
  event.stopPropagation()
  lightboxSrc.value = image.currentSrc || image.src
  lightboxAlt.value = image.alt || '题目插图'
  isLightboxOpen.value = true
}
</script>

<template>
  <div class="view-exam-session">
    <header class="session-header">
      <div class="progress-info">
        <span class="progress-text">进度: {{ currentIndex + 1 }} / {{ questions.length }}</span>
      </div>
      <div class="timer" :class="{ warning: isTimeWarning }">
        <Clock :size="16" class="timer-icon" />
        <span>{{ formattedRemainingTime }}</span>
      </div>
      <button class="button button--small submit-btn" @click="handleSubmitClick" :disabled="submitting">
        <Check :size="14" class="mr-1"/> {{ submitting ? '交卷中...' : '交卷' }}
      </button>
    </header>

    <div class="question-container" v-if="!loading && currentQuestion" @click.capture="handleRichImageClick">
      <div class="question-type-badge">
        {{ getQuestionTypeLabel(String(currentQuestion.type || '')) }}
      </div>
      
      <div class="question-stem" v-html="renderQuestionContent(currentQuestion.stem)"></div>
      
      <!-- Choices -->
      <div class="options" v-if="currentQuestion.type.includes('choice')">
        <div 
          v-for="opt in currentQuestion.options" 
          :key="`${currentQuestion.question_id}-${opt.key}`"
          class="option-item"
        >
          <input 
            :type="currentQuestion.type === 'single_choice' ? 'radio' : 'checkbox'" 
            :id="`opt-${currentQuestion.question_id}-${opt.key}`"
            :name="`q-${currentQuestion.question_id}`"
            :value="opt.key"
            v-model="answers[currentQuestion.question_id]"
          />
          <label :for="`opt-${currentQuestion.question_id}-${opt.key}`" class="option-label">
            <span class="opt-value">{{ opt.key }}.</span>
            <span class="opt-content" v-html="renderQuestionContent(opt.content)"></span>
          </label>
        </div>
      </div>
      
      <!-- Text input -->
      <div class="text-input" v-else>
        <textarea 
          v-model="answers[currentQuestion.question_id]"
          placeholder="请输入你的答案..."
          rows="6"
        ></textarea>
      </div>
    </div>
    
    <div class="loading-state" v-else-if="loading">
      加载试卷中...
    </div>

    <ImageLightbox v-model="isLightboxOpen" :src="lightboxSrc" :alt="lightboxAlt" />

    <button v-if="!loading" class="answer-sheet-fab" @click="isAnswerSheetOpen = true">
      答题卡
      <span>{{ answeredCount }}/{{ questions.length }}</span>
    </button>

    <section v-if="isAnswerSheetOpen" class="sheet-mask" @click.self="isAnswerSheetOpen = false">
      <div class="sheet-panel">
        <div class="sheet-header">
          <h3>答题卡</h3>
          <button class="sheet-close" @click="isAnswerSheetOpen = false">关闭</button>
        </div>
        <p class="sheet-summary">已作答 {{ answeredCount }} 题，未作答 {{ questions.length - answeredCount }} 题</p>
        <div class="sheet-groups">
          <section v-for="group in groupedQuestionSheet" :key="group.type" class="sheet-group">
            <div class="sheet-group-head">
              <h4>{{ group.label }}</h4>
              <span>{{ group.items.length }} 题</span>
            </div>
            <div class="sheet-grid">
              <button
                v-for="item in group.items"
                :key="item.q.question_id"
                class="sheet-item"
                :class="{
                  current: item.idx === currentIndex,
                  answered: isQuestionAnswered(item.q.question_id),
                }"
                @click="goToQuestion(item.idx)"
              >
                {{ item.idx + 1 }}
              </button>
            </div>
          </section>
        </div>
      </div>
    </section>

    <!-- Bottom Navigation -->
    <footer class="session-footer" v-if="!loading">
      <button class="nav-btn" @click="prevQuestion" :disabled="currentIndex === 0">
        <ChevronLeft :size="20"/> 上一题
      </button>
      
      <div class="dots-indicator">
        <div 
          v-for="(_, idx) in questions" 
          :key="idx" 
          class="dot"
          :class="{ active: idx === currentIndex, answered: answers[questions[idx].question_id] && answers[questions[idx].question_id].length > 0 }"
        ></div>
      </div>

      <button class="nav-btn" @click="nextQuestion" v-if="currentIndex < questions.length - 1">
        下一题 <ChevronRight :size="20"/>
      </button>
      <button class="button nav-btn btn-primary" @click="handleSubmitClick" v-else :disabled="submitting">
        立即交卷
      </button>
    </footer>
  </div>
</template>

<style scoped>
.view-exam-session {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fff;
  border-bottom: 1px solid var(--line);
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.progress-info {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.timer {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg);
  padding: 4px 12px;
  border-radius: 12px;
  font-family: monospace;
  font-size: 14px;
  color: var(--ink);
  font-weight: 600;
}

.timer.warning {
  background: #fef2f2;
  color: #b91c1c;
}

.timer.warning .timer-icon {
  color: #dc2626;
}

.timer-icon {
  color: var(--accent);
}

.submit-btn {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--ink);
  padding: 6px 12px;
  display: flex;
  align-items: center;
}

.submit-btn:hover {
  background: var(--bg);
  box-shadow: none;
  transform: none;
}

.mr-1 {
  margin-right: 4px;
}

.question-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.question-type-badge {
  align-self: flex-start;
  background: #eef2ff;
  color: #3b82f6;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.question-stem {
  font-size: 16px;
  color: var(--ink);
  line-height: 1.6;
  margin-bottom: 12px;
}

:deep(.question-stem img),
:deep(.opt-content img) {
  display: block;
  max-width: 100%;
  margin: 10px 0;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  cursor: zoom-in;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-item {
  position: relative;
}

.option-item input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.option-label {
  display: flex;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 15px;
  gap: 12px;
  align-items: flex-start;
}

.opt-value {
  font-weight: 600;
  color: var(--ink-soft);
}

.opt-content {
  color: var(--ink);
  line-height: 1.5;
}

.option-item input:checked ~ .option-label {
  border-color: var(--accent);
  background: var(--accent-light);
  box-shadow: 0 2px 4px rgba(15, 118, 110, 0.05);
}

.option-item input:checked ~ .option-label .opt-value {
  color: var(--accent);
}

.text-input textarea {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  font-size: 15px;
  line-height: 1.6;
  outline: none;
  resize: vertical;
  font-family: inherit;
}

.text-input textarea:focus {
  border-color: var(--accent);
}

.session-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid var(--line);
  padding-bottom: calc(16px + env(safe-area-inset-bottom));
}

.nav-btn {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  color: var(--ink);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-sm);
  gap: 4px;
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-primary {
  padding: 8px 24px;
  background: var(--accent);
  color: #fff;
  box-shadow: 0 4px 12px rgba(15, 118, 110, 0.2);
}

.dots-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
  overflow-x: auto;
  max-width: 150px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--line);
  flex-shrink: 0;
}

.dot.answered {
  background: var(--ink-soft);
}

.dot.active {
  background: var(--accent);
  transform: scale(1.3);
}

.loading-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-soft);
}

.answer-sheet-fab {
  position: fixed;
  right: 14px;
  bottom: calc(84px + env(safe-area-inset-bottom));
  border: none;
  border-radius: 999px;
  background: #0f766e;
  color: #fff;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 10px 20px rgba(15, 118, 110, 0.28);
  z-index: 1100;
}

.answer-sheet-fab span {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  padding: 2px 8px;
}

.sheet-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 1200;
  display: flex;
  align-items: flex-end;
}

.sheet-panel {
  width: 100%;
  max-height: min(65vh, 520px);
  overflow-y: auto;
  background: #fff;
  border-radius: 18px 18px 0 0;
  padding: 14px 14px calc(14px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--line);
  box-shadow: 0 -10px 30px rgba(15, 23, 42, 0.12);
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sheet-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--ink);
}

.sheet-close {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}

.sheet-summary {
  margin: 10px 0 12px;
  font-size: 13px;
  color: var(--ink-soft);
}

.sheet-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sheet-group {
  border: 1px solid #e8edf3;
  border-radius: 12px;
  padding: 10px;
  background: #fbfdff;
}

.sheet-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.sheet-group-head h4 {
  margin: 0;
  font-size: 13px;
  color: var(--ink);
}

.sheet-group-head span {
  font-size: 12px;
  color: var(--ink-soft);
}

.sheet-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.sheet-item {
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
}

.sheet-item.answered {
  border-color: rgba(15, 118, 110, 0.35);
  color: #0f766e;
  background: rgba(15, 118, 110, 0.08);
}

.sheet-item.current {
  border-color: var(--accent);
  background: rgba(37, 99, 235, 0.12);
  color: var(--accent);
}

@media (max-width: 420px) {
  .sheet-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .answer-sheet-fab {
    right: 10px;
    padding: 9px 12px;
  }
}
</style>
