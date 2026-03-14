<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { CheckCircle, AlertCircle, ChevronRight } from 'lucide-vue-next'
import { getExams, getReviewItems } from '@/api/teacher'

const reviewItems = ref<any[]>([])
const isLoading = ref(true)

const fetchReviewItems = async () => {
  try {
    isLoading.value = true
    const examRes = await getExams({ status: 'finished', page_size: 50 })
    const exams = (examRes as any).items || []

    const tasks = await Promise.all(
      exams.map(async (exam: any) => {
        const reviewRes = await getReviewItems({ exam_id: exam.id, page_size: 200 })
        const items = (reviewRes as any).items || []
        const pendingCount = items.filter((item: any) => item.review_status === 'pending').length
        const conflictCount = items.filter(
          (item: any) => item.final_score != null && item.ai_suggest_score != null && Number(item.final_score) !== Number(item.ai_suggest_score),
        ).length
        return {
          exam_id: exam.id,
          exam_title: exam.title,
          ai_status: 'completed',
          pending_count: pendingCount,
          conflict_count: conflictCount,
        }
      }),
    )

    reviewItems.value = tasks
  } catch (error) {
    console.error('Failed to fetch review items', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchReviewItems()
})
</script>

<template>
  <div class="view-review">
    <header class="page-header">
      <h1 class="page-title">阅卷任务</h1>
      <p class="page-desc">AI 已完成初步预判，需您复核主观题得分并发布最终成绩。</p>
    </header>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <div v-else-if="reviewItems.length === 0" class="empty-state">
      <CheckCircle :size="48" class="empty-icon text-success" />
      <p>太棒了！所有试卷已批阅完毕。</p>
    </div>

    <div v-else class="review-list">
      <div v-for="item in reviewItems" :key="item.exam_id" class="review-card clickable">
        <div class="card-header">
          <h3 class="exam-title">{{ item.exam_title }}</h3>
          <span class="status-tag" :class="item.ai_status === 'completed' ? 'ready' : 'pending'">
            {{ item.ai_status === 'completed' ? '待复核' : 'AI评分中' }}
          </span>
        </div>
        
        <div class="card-body">
          <div class="stat-group">
            <span class="stat-label">待复核试卷</span>
            <span class="stat-value highlight">{{ item.pending_count || 0 }} 份</span>
          </div>
          <div class="stat-group">
            <span class="stat-label">存在争议题</span>
            <span class="stat-value warning"><AlertCircle :size="14"/> {{ item.conflict_count || 0 }} 题</span>
          </div>
        </div>

        <div class="card-footer">
          <span class="action-text">开始批阅</span>
          <ChevronRight :size="16" />
        </div>
      </div>
    </div>
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

.page-desc {
  font-size: 14px;
  color: var(--ink-soft);
  line-height: 1.5;
}

.loading-state, .empty-state {
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

.status-tag.pending {
  background: var(--bg);
  color: var(--ink-soft);
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





