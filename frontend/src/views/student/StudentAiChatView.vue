<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronDown, ChevronUp, Send } from 'lucide-vue-next'
import http from '@/lib/http'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

const route = useRoute()

const examId = Number(route.query.examId || 0)
const questionId = Number(route.query.questionId || 0)

const loading = ref(false)
const errorText = ref('')
const contextLoading = ref(false)
const contextError = ref('')
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const messagesRef = ref<HTMLElement | null>(null)
const previewExpanded = ref(false)

const examTitle = ref('')
const questionPreview = ref<any>(null)

const normalizeQuestionType = (value: unknown) => {
  const t = String(value || '')
  if (t === 'single_choice') return '单选题'
  if (t === 'multiple_choice') return '多选题'
  if (t === 'judge') return '判断题'
  if (t === 'blank') return '填空题'
  return '主观题'
}

const toPlainText = (value: unknown) => {
  const raw = String(value ?? '').trim()
  if (!raw) return ''
  if (raw.startsWith('[') && raw.endsWith(']')) {
    try {
      const blocks = JSON.parse(raw)
      if (Array.isArray(blocks)) {
        return blocks
          .map((block: any) => String(block?.content || '').trim())
          .filter(Boolean)
          .join(' ')
      }
    } catch {
      // ignore parse errors and fallback to plain string mode
    }
  }
  return raw.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

const questionTypeText = computed(() => normalizeQuestionType(questionPreview.value?.question?.question_type))
const questionStemText = computed(() => toPlainText(questionPreview.value?.question?.stem))
const studentAnswerText = computed(() => {
  const value = questionPreview.value?.answer?.student_answer
  if (Array.isArray(value)) return value.join('、')
  if (value === null || value === undefined || value === '') return '未作答'
  return String(value)
})
const standardAnswerText = computed(() => {
  const value = questionPreview.value?.answer?.standard_answer
  if (Array.isArray(value)) return value.join('、')
  if (value === null || value === undefined || value === '') return '暂无'
  return String(value)
})
const optionItems = computed(() => {
  const rows = Array.isArray(questionPreview.value?.question?.options)
    ? questionPreview.value.question.options
    : []
  return rows.map((item: any) => ({
    key: String(item?.key || ''),
    content: toPlainText(item?.content),
  }))
})

const loadPreviewContext = async () => {
  if (!examId || !questionId) return
  contextError.value = ''
  contextLoading.value = true
  try {
    const [examRes, questionRes] = await Promise.all([
      http.get('/student/exams/detail', { params: { exam_id: examId } }),
      http.get('/student/results/question-analysis', {
        params: { exam_id: examId, question_id: questionId },
      }),
    ])
    examTitle.value = String((examRes as any)?.exam?.title || '')
    questionPreview.value = questionRes
  } catch (error: any) {
    contextError.value = error?.message || '题目预览加载失败，请稍后重试。'
  } finally {
    contextLoading.value = false
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const appendAssistant = (content: string) => {
  messages.value.push({ role: 'assistant', content })
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  await scrollToBottom()

  if (!examId || !questionId) {
    appendAssistant('当前未绑定具体错题上下文，请从错题解析页进入 AI 追问。')
    await scrollToBottom()
    return
  }

  try {
    loading.value = true
    const res: any = await http.post('/student/ai-chat/follow-up', {
      exam_id: examId,
      question_id: questionId,
      messages: messages.value,
    })
    appendAssistant(String(res?.reply || '我先帮你定位关键步骤，再追问我你卡住的点。'))
  } catch (error: any) {
    appendAssistant(error?.message || 'AI 回复失败，请稍后再试。')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

onMounted(async () => {
  if (!examId || !questionId) {
    appendAssistant('你可以在错题解析页点击“AI追问”进入本页，我会基于该题给你更具体的辅导。')
    return
  }
  await loadPreviewContext()
  appendAssistant('我已读取当前错题上下文。你可以问我：为什么错、这题怎么想、同类题怎么避免再错。')
  await scrollToBottom()
})
</script>

<template>
  <div class="chat-view">
    <h1 class="chat-title">AI 错题对话</h1>

    <section v-if="examId && questionId" class="preview-card">
      <button class="preview-head" type="button" @click="previewExpanded = !previewExpanded">
        <div>
          <p class="preview-kicker">对照预览</p>
          <p class="preview-title">{{ examTitle || `考试 #${examId}` }} · 题目 #{{ questionId }}</p>
        </div>
        <component :is="previewExpanded ? ChevronUp : ChevronDown" :size="18" />
      </button>

      <p v-if="contextLoading" class="preview-loading">正在加载题目预览...</p>
      <p v-else-if="contextError" class="preview-error">{{ contextError }}</p>

      <div v-else-if="questionPreview" class="preview-body" :class="{ collapsed: !previewExpanded }">
        <p class="preview-meta">{{ questionTypeText }} · 你的答案：{{ studentAnswerText }} · 标准答案：{{ standardAnswerText }}</p>
        <p class="preview-stem">{{ questionStemText || '题干为空' }}</p>

        <div v-if="previewExpanded && optionItems.length" class="preview-options">
          <p class="preview-label">选项</p>
          <div v-for="item in optionItems" :key="item.key" class="preview-option-row">
            <span class="preview-option-key">{{ item.key }}</span>
            <span class="preview-option-text">{{ item.content || '（空）' }}</span>
          </div>
        </div>
      </div>
    </section>

    <section ref="messagesRef" class="message-list">
      <div v-for="(item, idx) in messages" :key="idx" class="msg-row" :class="item.role">
        <div class="bubble">{{ item.content }}</div>
      </div>
      <div v-if="loading" class="msg-row assistant">
        <div class="bubble">正在思考你的问题...</div>
      </div>
    </section>

    <footer class="input-bar">
      <input
        v-model="inputText"
        type="text"
        placeholder="例如：这题我为什么会选错？"
        @keyup.enter="sendMessage"
      />
      <button class="send-btn" :disabled="loading || !inputText.trim()" @click="sendMessage">
        <Send :size="16" />
      </button>
    </footer>

    <p v-if="errorText" class="error-text">{{ errorText }}</p>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100%;
  gap: 10px;
}

@supports (height: 100dvh) {
  .chat-view {
    min-height: calc(100dvh - 56px - 48px);
  }
}

.chat-title {
  margin: 0;
  font-size: 18px;
}

.preview-card {
  border: 1px solid #dce4ef;
  border-radius: 14px;
  background: #f8fafc;
  overflow: hidden;
}

.preview-head {
  width: 100%;
  border: none;
  background: transparent;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  text-align: left;
  padding: 10px 12px;
}

.preview-kicker {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.preview-title {
  margin: 2px 0 0;
  font-size: 14px;
  color: #0f172a;
}

.preview-loading,
.preview-error {
  margin: 0;
  padding: 0 12px 10px;
  font-size: 13px;
  color: #64748b;
}

.preview-error {
  color: #b91c1c;
}

.preview-body {
  padding: 0 12px 12px;
}

.preview-body.collapsed .preview-stem {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.preview-meta {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: #334155;
}

.preview-stem {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: #0f172a;
}

.preview-options {
  margin-top: 8px;
  border-top: 1px dashed #d4dce8;
  padding-top: 8px;
}

.preview-label {
  margin: 0 0 6px;
  font-size: 12px;
  color: #64748b;
}

.preview-option-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.5;
  color: #0f172a;
}

.preview-option-key {
  min-width: 18px;
  color: #0f766e;
  font-weight: 600;
}

.preview-option-text {
  flex: 1;
}

.message-list {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  border: 1px solid #dce4ef;
  border-radius: 14px;
  background: #f8fafc;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.msg-row {
  display: flex;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 82%;
  border-radius: 12px;
  padding: 9px 10px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.msg-row.user .bubble {
  background: #0f766e;
  color: #fff;
}

.msg-row.assistant .bubble {
  background: #fff;
  border: 1px solid #d9e3ef;
  color: #334155;
}

.input-bar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #dce4ef;
  border-radius: 12px;
  background: #fff;
  padding: 8px;
  position: sticky;
  bottom: 0;
}

.input-bar input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
}

.send-btn {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 10px;
  background: #0f766e;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  opacity: 0.55;
}
</style>
