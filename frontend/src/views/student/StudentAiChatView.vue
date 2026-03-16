<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Send } from 'lucide-vue-next'
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
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const messagesRef = ref<HTMLElement | null>(null)

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
  appendAssistant('我已读取当前错题上下文。你可以问我：为什么错、这题怎么想、同类题怎么避免再错。')
  await scrollToBottom()
})
</script>

<template>
  <div class="chat-view">
    <h1 class="chat-title">AI 错题对话</h1>

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
