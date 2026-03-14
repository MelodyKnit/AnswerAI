<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock, FileText, Target, AlertCircle } from 'lucide-vue-next'
import http from '@/lib/http'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const exam = ref<any>(null)
const loading = ref(true)
const starting = ref(false)
const errorMsg = ref('')

onMounted(async () => {
  try {
    const res = await http.get('/student/exams/detail', { params: { exam_id: examId } })
    exam.value = res.data.data
  } catch (error: any) {
    errorMsg.value = error.response?.data?.message || '无法获取考试信息'
  } finally {
    loading.value = false
  }
})

const startExam = async () => {
  starting.value = true
  errorMsg.value = ''
  try {
    const res = await http.post('/student/exams/start', { exam_id: examId })
    const sessionId = res.data.data.submission.id
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
      </div>

      <div class="instructions-card">
        <h3>考试须知</h3>
        <div class="instructions-text">
          {{ exam.instructions || '1. 考试期间请勿切换应用\n2. 遇到问题请举手示意\n3. 答题完毕后请仔细检查后提交' }}
        </div>
      </div>

      <div class="bottom-action">
        <button 
          class="button button-large" 
          @click="startExam" 
          :disabled="starting"
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
  height: 100vh;
  background: var(--bg);
  padding: 16px;
  max-width: 480px;
  margin: 0 auto;
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
  gap: 24px;
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
  margin-top: auto;
  padding-bottom: 32px;
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
</style>
