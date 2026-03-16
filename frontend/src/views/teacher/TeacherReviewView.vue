<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckCircle, AlertCircle, ChevronRight } from 'lucide-vue-next'
import { getReviewItems, getReviewTasks, submitReview } from '@/api/teacher'

const router = useRouter()
const route = useRoute()
const reviewItems = ref<any[]>([])
const isLoading = ref(true)
const activeView = ref<'all' | 'pending' | 'completed'>('all')
const reviewDetailItems = ref<any[]>([])
const submissionOverview = ref<any[]>([])
const scoreDraft = ref<Record<number, number>>({})
const commentDraft = ref<Record<number, string>>({})
const submittingReviewId = ref<number | null>(null)

const currentExamId = computed(() => Number(route.params.id || 0))
const isExamReviewMode = computed(() => route.name === 'teacher-review' && currentExamId.value > 0)

const goToExamReview = (examId: number) => {
  router.push(`/app/teacher/exams/${examId}/review`)
}

const backToReviewTasks = () => {
  router.push('/app/teacher/review')
}

const fetchReviewData = async () => {
  try {
    isLoading.value = true
    if (isExamReviewMode.value) {
      const reviewStatus = activeView.value === 'all' ? undefined : (activeView.value === 'completed' ? 'reviewed' : 'pending')
      const detailRes = await getReviewItems({ exam_id: currentExamId.value, review_status: reviewStatus, page_size: 100 })
      reviewDetailItems.value = (detailRes as any).items || []
      submissionOverview.value = (detailRes as any).submissions || []
      const nextScoreDraft: Record<number, number> = {}
      const nextCommentDraft: Record<number, string> = {}
      for (const item of reviewDetailItems.value) {
        const id = Number(item.id)
        nextScoreDraft[id] = Number(item.final_score ?? item.ai_suggest_score ?? 0)
        nextCommentDraft[id] = ''
      }
      scoreDraft.value = nextScoreDraft
      commentDraft.value = nextCommentDraft
      reviewItems.value = []
      return
    }

    const taskRes = await getReviewTasks({ view: activeView.value, page_size: 100 })
    reviewItems.value = (taskRes as any).items || []
  } catch (error) {
    console.error('Failed to fetch review items', error)
  } finally {
    isLoading.value = false
  }
}

const submitOneReview = async (item: any) => {
  const reviewItemId = Number(item.id)
  const finalScore = Number(scoreDraft.value[reviewItemId])
  if (Number.isNaN(finalScore)) {
    alert('请输入有效分数')
    return
  }
  try {
    submittingReviewId.value = reviewItemId
    await submitReview({
      review_item_id: reviewItemId,
      final_score: finalScore,
      review_comment: (commentDraft.value[reviewItemId] || '').trim() || undefined,
    })
    await fetchReviewData()
  } catch (error: any) {
    alert(error?.message || '提交批阅失败，请稍后重试')
  } finally {
    submittingReviewId.value = null
  }
}

const switchView = (view: 'all' | 'pending' | 'completed') => {
  if (activeView.value === view) return
  activeView.value = view
  fetchReviewData()
}

const getSubmissionStatusText = (item: any) => {
  if (item.pending_manual_count > 0) return `待人工复核 ${item.pending_manual_count} 题`
  if (item.manual_item_count > 0) return '人工复核已完成'
  if (item.status === 'submitted' || item.status === 'completed' || item.status === 'reviewed') return '客观题已完成，无需人工复核'
  return '进行中'
}

const getTaskStatusText = (item: any) => {
  if (item.review_mode === 'objective_only') return '无需复核'
  return item.task_status === 'pending' ? '待复核' : '已完成'
}

const getTaskActionText = (item: any) => {
  if (item.review_mode === 'objective_only') return '查看提交记录'
  return '开始批阅'
}

onMounted(() => {
  fetchReviewData()
})

watch(
  () => [route.name, route.params.id],
  () => {
    fetchReviewData()
  },
)
</script>

<template>
  <div class="view-review">
    <header class="page-header">
      <h1 class="page-title">阅卷任务</h1>
    </header>

    <section v-if="isExamReviewMode" class="exam-review-panel">
      <div class="exam-review-head">
        <button class="btn-ghost" @click="backToReviewTasks">返回任务列表</button>
        <span>考试 ID：{{ currentExamId }}</span>
      </div>

      <div class="task-tabs">
        <button class="tab-btn" :class="{ active: activeView === 'all' }" @click="switchView('all')">全部题目</button>
        <button class="tab-btn" :class="{ active: activeView === 'pending' }" @click="switchView('pending')">待批阅</button>
        <button class="tab-btn" :class="{ active: activeView === 'completed' }" @click="switchView('completed')">已批阅</button>
      </div>

      <div v-if="isLoading" class="loading-state">加载中...</div>

      <div v-else-if="reviewDetailItems.length === 0" class="empty-state">
        <template v-if="submissionOverview.length">
          <div class="submission-panel">
            <h3>已提交学生记录</h3>
            <p class="submission-tip">本场考试暂无需要人工复核的题目，以下为学生提交情况。</p>
            <div class="submission-list">
              <article v-for="sub in submissionOverview" :key="sub.submission_id" class="submission-card">
                <div class="submission-head">
                  <strong>{{ sub.student_name || `学生#${sub.student_id}` }}</strong>
                  <span>{{ getSubmissionStatusText(sub) }}</span>
                </div>
                <div class="submission-meta">
                  <span>提交状态：{{ sub.status }}</span>
                  <span>总分：{{ Number(sub.total_score || 0).toFixed(1) }}</span>
                </div>
              </article>
            </div>
          </div>
        </template>
        <template v-else>
          <CheckCircle :size="48" class="empty-icon text-success" />
          <p>该考试暂未收到学生提交。</p>
        </template>
      </div>

      <div v-else class="detail-list">
        <article v-for="item in reviewDetailItems" :key="item.id" class="detail-card">
          <div class="detail-top">
            <h3>题目 #{{ item.question_id }}</h3>
            <span class="status-tag" :class="item.review_status === 'reviewed' ? 'done' : 'ready'">
              {{ item.review_status === 'reviewed' ? '已批阅' : '待批阅' }}
            </span>
          </div>
          <div class="detail-metrics">
            <span>AI 建议分：{{ item.ai_suggest_score ?? '-' }}</span>
            <span>当前最终分：{{ item.final_score ?? '-' }}</span>
          </div>
          <div class="detail-inputs">
            <label>
              <span>最终分</span>
              <input type="number" step="0.5" v-model.number="scoreDraft[item.id]" />
            </label>
            <label>
              <span>评语（可选）</span>
              <input type="text" v-model="commentDraft[item.id]" placeholder="填写批阅意见" />
            </label>
          </div>
          <div class="detail-actions">
            <button class="btn-primary" :disabled="submittingReviewId === item.id" @click="submitOneReview(item)">
              {{ submittingReviewId === item.id ? '提交中...' : '提交批阅' }}
            </button>
          </div>
        </article>
      </div>
    </section>

    <template v-else>
    <div class="task-tabs">
      <button class="tab-btn" :class="{ active: activeView === 'all' }" @click="switchView('all')">全部任务</button>
      <button class="tab-btn" :class="{ active: activeView === 'pending' }" @click="switchView('pending')">待阅任务</button>
      <button class="tab-btn" :class="{ active: activeView === 'completed' }" @click="switchView('completed')">已阅任务</button>
    </div>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <div v-else-if="reviewItems.length === 0" class="empty-state">
      <CheckCircle :size="48" class="empty-icon text-success" />
      <p>当前没有待处理阅卷任务。</p>
    </div>

    <div v-if="reviewItems.length" class="review-list">
      <div v-for="item in reviewItems" :key="item.exam_id" class="review-card clickable" @click="goToExamReview(item.exam_id)">
        <div class="card-header">
          <h3 class="exam-title">{{ item.exam_title }}</h3>
          <span class="status-tag" :class="item.task_status === 'pending' ? 'ready' : 'done'">
            {{ getTaskStatusText(item) }}
          </span>
        </div>
        
        <div class="card-body">
          <div class="stat-group">
            <span class="stat-label">学生提交</span>
            <span class="stat-value highlight">{{ item.total_submissions || 0 }} 份</span>
          </div>
          <div class="stat-group">
            <span class="stat-label">待人工复核</span>
            <span class="stat-value warning"><AlertCircle :size="14"/> {{ item.pending_count || 0 }} 题</span>
          </div>
        </div>

        <div class="card-footer">
          <span class="action-text">{{ getTaskActionText(item) }}</span>
          <ChevronRight :size="16" />
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<style scoped>
.view-review {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  color: var(--ink-soft);
  gap: 16px;
}

.empty-icon.text-success {
  color: #10b981;
  opacity: 1;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-review-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-review-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #475569;
  font-size: 12px;
}

.detail-list {
  display: grid;
  gap: 10px;
}

.detail-card {
  border: 1px solid #d8e3ed;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}

.submission-panel {
  width: 100%;
  max-width: 760px;
  border: 1px solid #d8e3ed;
  border-radius: 14px;
  padding: 14px;
  background: #fff;
}

.submission-panel h3 {
  margin: 0;
  font-size: 16px;
  color: var(--ink);
}

.submission-tip {
  margin: 6px 0 0;
  color: var(--ink-soft);
  font-size: 12px;
}

.submission-list {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.submission-card {
  border: 1px solid #e5edf5;
  border-radius: 10px;
  padding: 10px;
  background: #fbfdff;
}

.submission-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.submission-head strong {
  font-size: 14px;
  color: #0f172a;
}

.submission-head span {
  font-size: 12px;
  color: #0f766e;
}

.submission-meta {
  margin-top: 6px;
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: #64748b;
}

.detail-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-top h3 {
  margin: 0;
  font-size: 14px;
  color: #1f2937;
}

.detail-metrics {
  margin-top: 8px;
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #475569;
}

.detail-inputs {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.detail-inputs label {
  display: grid;
  gap: 6px;
}

.detail-inputs span {
  font-size: 12px;
  color: #475569;
}

.detail-inputs input {
  height: 36px;
  border: 1px solid #d6e0ea;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 13px;
}

.detail-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.task-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
}

.tab-btn.active {
  background: #ecfeff;
  border-color: #99f6e4;
  color: #0f766e;
}

.btn-primary,
.btn-ghost {
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
}

.btn-primary {
  border: 1px solid #0f766e;
  background: #0f766e;
  color: #fff;
}

.btn-ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
}

.review-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.2s ease;
}

.review-card:hover {
  border-color: var(--accent);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.exam-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  flex: 1;
  padding-right: 16px;
}

.status-tag {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.status-tag.ready {
  background: rgba(37, 99, 235, 0.1);
  color: var(--accent);
}

.status-tag.done {
  background: #ecfdf5;
  color: #047857;
}

.card-body {
  display: flex;
  gap: 32px;
  padding: 16px;
  background: var(--bg);
  border-radius: 8px;
}

.stat-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--ink-soft);
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-value.highlight {
  color: var(--accent);
}

.stat-value.warning {
  color: #f59e0b;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px dashed var(--line);
  color: var(--accent);
  font-size: 14px;
  font-weight: 500;
}
</style>





