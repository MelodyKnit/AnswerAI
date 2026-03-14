<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Play, Pause, Square, BarChart, CheckCircle } from 'lucide-vue-next'
import { getExamDetail, publishExam, pauseExam, finishExam } from '@/api/teacher'

const route = useRoute()
const router = useRouter()
const examId = Number(route.params.id)

const exam = ref<any>(null)
const isLoading = ref(true)

const fetchExam = async () => {
  try {
    isLoading.value = true
    const res: any = await getExamDetail(examId)
    exam.value = res.exam; 
    exam.value.question_items = res.question_items || []
  } catch (error) {
    console.error('Failed to fetch exam', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchExam()
})

const goBack = () => router.back()

const handlePublish = async () => {
  await publishExam(examId)
  fetchExam()
}
const handlePause = async () => {
  await pauseExam(examId)
  fetchExam()
}
const handleFinish = async () => {
  await finishExam(examId)
  fetchExam()
}
</script>

<template>
  <div class="view-exam-detail">
    <header class="page-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="24" />
      </button>
      <div v-if="exam" class="status-badge" :class="`status--${exam.status}`">
        {{ exam.status === 'draft' ? '草稿' : exam.status === 'published' ? '进行中' : '已结束' }}
      </div>
    </header>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <template v-else-if="exam">
      <section class="exam-info">
        <h1 class="exam-title">{{ exam.title }}</h1>
        <p class="exam-desc" v-if="exam.instructions">{{ exam.instructions }}</p>
        <div class="meta-tags">
          <span class="tag">{{ exam.subject || '不限范围' }}</span>
          <span class="tag">{{ exam.duration_minutes }} 分钟</span>
          <span class="tag">{{ exam.total_score }} 分</span>
        </div>
      </section>

      <section class="action-grid">
        <button class="action-card" v-if="exam.status === 'draft'" @click="handlePublish">
          <Play :size="24" class="icon publish-icon" />
          <span>发布考试</span>
        </button>
        <button class="action-card" v-if="exam.status === 'published'" @click="handlePause">
          <Pause :size="24" class="icon pause-icon" />
          <span>暂停考试</span>
        </button>
        <button class="action-card" v-if="exam.status === 'published'" @click="handleFinish">
          <Square :size="24" class="icon stop-icon" />
          <span>结束考试</span>
        </button>
        
        <button class="action-card" v-if="exam.status === 'finished'">
          <CheckCircle :size="24" class="icon review-icon" />
          <span>去阅卷</span>
        </button>
        <button class="action-card" v-if="exam.status === 'finished'">
          <BarChart :size="24" class="icon chart-icon" />
          <span>分析报告</span>
        </button>
      </section>
      
      <section class="section-block">
        <h2 class="section-title">试题列表 ({{ exam.question_items ? exam.question_items.length : 0 }})</h2>
        <div class="questions-list" v-if="exam.question_items && exam.question_items.length > 0">
          <div class="q-item" v-for="(q, idx) in exam.question_items" :key="q.question_id">
            <span class="q-num">{{ Number(idx) + 1 }}.</span> 
            <span class="q-content">{{ q.question?.stem || '题干加载失败' }}</span>
            <span class="q-score">{{ q.score || 0 }}分</span>
          </div>
        </div>
        <div class="empty-state" v-else>
          试卷目前还是空的
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.view-exam-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.icon-button {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  margin-left: -8px;
}

.status-badge {
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 20px;
  background: var(--bg);
  border: 1px solid var(--line);
}
.status--published {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-color: #10b981;
}
.status--finished {
  background: var(--bg);
  color: var(--ink-soft);
}

.loading-state, .empty-state {
  text-align: center;
  color: var(--ink-soft);
  padding: 40px 0;
}

.exam-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.exam-desc {
  font-size: 14px;
  color: var(--ink-soft);
  line-height: 1.5;
}

.meta-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  font-size: 12px;
  padding: 4px 8px;
  background: var(--line);
  color: var(--ink);
  border-radius: 4px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 24px 16px;
  transition: all 0.2s;
  cursor: pointer;
}

.action-card:hover {
  border-color: var(--accent);
}

.action-card span {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.publish-icon { color: #10b981; }
.pause-icon { color: #f59e0b; }
.stop-icon { color: #ef4444; }
.review-icon { color: var(--accent); }
.chart-icon { color: #8b5cf6; }

.section-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.q-item {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  align-items: flex-start;
}
.q-num {
  font-weight: 600;
  color: var(--ink-soft);
}
.q-content {
  flex: 1;
  font-size: 14px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.q-score {
  font-size: 13px;
  color: var(--ink-soft);
  white-space: nowrap;
}
</style>



