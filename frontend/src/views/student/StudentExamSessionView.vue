<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, ChevronLeft, ChevronRight, Check } from 'lucide-vue-next'
import http from '@/lib/http'

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)
const submissionId = Number(route.params.sessionId)

const questions = ref<any[]>([])
const currentIndex = ref(0)
const loading = ref(true)
const submitting = ref(false)

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)

// Track answers locally
const answers = ref<Record<number, any>>({})

onMounted(async () => {
  try {
    const res = await http.get('/student/exams/paper', {
      params: { exam_id: examId, submission_id: submissionId }
    })
    questions.value = res.data.data.questions || []
    
    // Initialize empty answers
    questions.value.forEach(q => {
      answers.value[q.id] = q.type === 'multiple_choice' ? [] : ''
    })
  } catch (error) {
    console.error('Failed to load exam paper:', error)
    alert('无法加载试卷数据')
  } finally {
    loading.value = false
  }
})

const saveCurrentAnswer = async () => {
  if (!currentQuestion.value) return
  
  const qId = currentQuestion.value.id
  const val = answers.value[qId]
  
  try {
    await http.post('/student/exams/answer/save', {
      exam_id: examId,
      submission_id: submissionId,
      question_id: qId,
      answer: currentQuestion.value.type === 'multiple_choice' ? val : (currentQuestion.value.type === 'single_choice' ? val : null),
      answer_text: (currentQuestion.value.type === 'fill_in_the_blank' || currentQuestion.value.type === 'short_answer') ? val : null,
      spent_seconds: 10 // Mock for now
    })
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

const submitExam = async () => {
  if (!confirm('确定要交卷吗？')) return
  
  await saveCurrentAnswer()
  submitting.value = true
  
  try {
    await http.post('/student/exams/submit', {
      exam_id: examId,
      submission_id: submissionId,
      confirm_submit: true
    })
    router.replace(`/app/student/results/${examId}`)
  } catch (error) {
    console.error('Submit failed', error)
    alert('交卷失败，请重试')
    submitting.value = false
  }
}
</script>

<template>
  <div class="view-exam-session">
    <header class="session-header">
      <div class="progress-info">
        <span class="progress-text">进度: {{ currentIndex + 1 }} / {{ questions.length }}</span>
      </div>
      <div class="timer">
        <Clock :size="16" class="timer-icon" />
        <span>00:45:00</span> <!-- Mock static timer -->
      </div>
      <button class="button button--small submit-btn" @click="submitExam" :disabled="submitting">
        <Check :size="14" class="mr-1"/> {{ submitting ? '交卷中...' : '交卷' }}
      </button>
    </header>

    <div class="question-container" v-if="!loading && currentQuestion">
      <div class="question-type-badge">
        {{ 
          currentQuestion.type === 'single_choice' ? '单选题' : 
          currentQuestion.type === 'multiple_choice' ? '多选题' : 
          currentQuestion.type === 'fill_in_the_blank' ? '填空题' : '简答题' 
        }}
      </div>
      
      <div class="question-stem" v-html="currentQuestion.stem"></div>
      
      <!-- Choices -->
      <div class="options" v-if="currentQuestion.type.includes('choice')">
        <div 
          v-for="opt in currentQuestion.options" 
          :key="opt.id"
          class="option-item"
        >
          <input 
            :type="currentQuestion.type === 'single_choice' ? 'radio' : 'checkbox'" 
            :id="`opt-${opt.id}`"
            :name="`q-${currentQuestion.id}`"
            :value="opt.value"
            v-model="answers[currentQuestion.id]"
          />
          <label :for="`opt-${opt.id}`" class="option-label">
            <span class="opt-value">{{ opt.value }}.</span>
            <span class="opt-content" v-html="opt.content"></span>
          </label>
        </div>
      </div>
      
      <!-- Text input -->
      <div class="text-input" v-else>
        <textarea 
          v-model="answers[currentQuestion.id]"
          placeholder="请输入你的答案..."
          rows="6"
        ></textarea>
      </div>
    </div>
    
    <div class="loading-state" v-else-if="loading">
      加载试卷中...
    </div>

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
          :class="{ active: idx === currentIndex, answered: answers[questions[idx].id] && answers[questions[idx].id].length > 0 }"
        ></div>
      </div>

      <button class="nav-btn" @click="nextQuestion" v-if="currentIndex < questions.length - 1">
        下一题 <ChevronRight :size="20"/>
      </button>
      <button class="button nav-btn btn-primary" @click="submitExam" v-else :disabled="submitting">
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
</style>
