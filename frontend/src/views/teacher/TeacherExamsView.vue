<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, FileText, ChevronRight, Trash2 } from 'lucide-vue-next'
import { useUiDialog } from '@/composables/useUiDialog'
import { deleteExam, getExams } from '@/api/teacher'
import AppDropdown from '@/components/common/AppDropdown.vue'

const router = useRouter()
const exams = ref<any[]>([])
const isLoading = ref(true)
const filterStatus = ref('all') // all, draft, published, finished
const keyword = ref('')
const ui = useUiDialog()

const statusOptions = [
  { label: '所有状态', value: 'all' },
  { label: '草稿', value: 'draft' },
  { label: '进行中', value: 'published' },
  { label: '已结束', value: 'finished' },
]

const parseServerTime = (value: string) => {
  if (!value) return Number.NaN
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`).getTime()
}

const getEffectiveStatus = (exam: any): 'draft' | 'published' | 'finished' | 'expired' => {
  const status = String(exam?.status || '')
  if (status === 'draft') return 'draft'
  if (status === 'finished') return 'finished'
  if (status === 'published') {
    const end = parseServerTime(String(exam?.end_time || ''))
    if (!Number.isNaN(end) && Date.now() > end) return 'expired'
    return 'published'
  }
  return 'draft'
}

const fetchExams = async () => {
  try {
    isLoading.value = true
    const res = await getExams({
      status: filterStatus.value !== 'all' ? filterStatus.value : undefined,
      keyword: keyword.value || undefined,
    })
    exams.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to fetch exams', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchExams()
})

const goCreate = () => {
  router.push('/app/teacher/exams/create')
}

const goExam = (exam: any) => {
  const id = Number(exam?.id)
  if (!Number.isFinite(id) || id <= 0) return
  if (getEffectiveStatus(exam) === 'draft') {
    router.push(`/app/teacher/exams/create?exam_id=${id}`)
    return
  }
  router.push(`/app/teacher/exams/${id}`)
}

const canDelete = (exam: any) => {
  const status = getEffectiveStatus(exam)
  return status === 'draft' || status === 'finished'
}

const handleDelete = async (exam: any) => {
  if (!canDelete(exam)) return
  const confirmed = await ui.confirm(`确认删除考试「${exam.title}」吗？此操作不可恢复。`, {
    title: '删除考试',
    confirmText: '确认删除',
    tone: 'warning',
  })
  if (!confirmed) return
  try {
    await deleteExam(Number(exam.id))
    await fetchExams()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    await ui.alert(typeof detail === 'string' ? detail : '删除失败，请稍后重试', { tone: 'error' })
  }
}

const getStatusColor = (exam: any) => {
  const status = getEffectiveStatus(exam)
  switch (status) {
    case 'draft':
      return 'var(--ink-soft)'
    case 'published':
      return 'var(--success, #10b981)'
    case 'finished':
      return 'var(--ink-soft)'
    case 'expired':
      return '#b45309'
    default:
      return 'var(--ink)'
  }
}

const getStatusText = (exam: any) => {
  const status = getEffectiveStatus(exam)
  switch (status) {
    case 'draft':
      return '草稿'
    case 'published':
      return '进行中'
    case 'finished':
      return '已结束'
    case 'expired':
      return '已超时(待结束)'
    default:
      return String(exam?.status || '未知')
  }
}

const handleStatusChange = async () => {
  await fetchExams()
}
</script>

<template>
  <div class="view-exams">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">考试管理</h1>
        <button class="button button--small" @click="goCreate">
          <Plus :size="16" />
          <span>组卷/发布</span>
        </button>
      </div>
      <p class="page-desc">创建试卷，发布考试与分析考试结果。</p>
    </header>

    <div class="filter-bar">
      <div class="search-box">
        <Search :size="16" class="search-icon" />
        <input type="text" placeholder="搜索试卷名称..." class="search-input" v-model="keyword" @keyup.enter="fetchExams" />
      </div>
      <AppDropdown
        v-model="filterStatus"
        class="status-select"
        :options="statusOptions"
        aria-label="考试状态筛选"
        @change="handleStatusChange"
      />
    </div>

    <div v-if="isLoading" class="loading-state">加载中...</div>
    
    <div v-else-if="exams.length === 0" class="empty-state">
      <FileText :size="48" class="empty-icon" />
      <p>暂无考试任务</p>
      <button class="button" @click="goCreate">去创建一份试卷</button>
    </div>

    <div v-else class="exam-list">
      <div 
        v-for="exam in exams" 
        :key="exam.id" 
        class="exam-card clickable"
        @click="goExam(exam)"
      >
        <div class="card-main">
          <h3 class="exam-title">{{ exam.title }}</h3>
          <div class="exam-meta">
            <span>{{ exam.subject || '通用' }}</span>
            <span class="dot">·</span>
            <span>共 {{ exam.total_score || 100 }} 分</span>
            <span class="dot">·</span>
            <span>{{ exam.duration_minutes || 60 }} 分钟</span>
          </div>
        </div>
        <div class="card-side">
          <button
            class="delete-button"
            :class="{ 'delete-button--disabled': !canDelete(exam) }"
            :disabled="!canDelete(exam)"
            @click.stop="handleDelete(exam)"
            :title="canDelete(exam) ? '删除考试' : '仅草稿或已结束考试可删除'"
            aria-label="删除考试"
          >
            <Trash2 :size="15" />
          </button>
          <span 
            class="status-badge" 
            :style="{ color: getStatusColor(exam) }"
          >
            {{ getStatusText(exam) }}
          </span>
          <ChevronRight :size="18" class="icon-right" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-exams {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.search-box {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid var(--line);
  padding: 8px 12px;
  border-radius: var(--radius-md);
}

.search-icon {
  color: var(--ink-soft);
}

.search-input {
  border: none;
  background: none;
  outline: none;
  font-size: 14px;
  width: 100%;
}

.status-select {
  width: clamp(108px, 30vw, 132px);
}

.exam-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
}

.exam-card:hover {
  border-color: var(--ink-light);
}

.card-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.exam-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink);
  margin: 0;
  line-height: 1.35;
}

.exam-meta {
  font-size: 13px;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  row-gap: 4px;
}

.dot {
  margin: 0 6px;
}

.card-side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.delete-button {
  width: 28px;
  height: 28px;
  border: 1px solid #fecaca;
  color: #dc2626;
  background: #fff1f2;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.delete-button:hover {
  background: #ffe4e6;
}

.delete-button--disabled,
.delete-button:disabled {
  border-color: var(--line);
  color: var(--ink-soft);
  background: #f8fafc;
  cursor: not-allowed;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  background: #f8fafc;
  border: 1px solid currentColor;
  opacity: 0.92;
}

.icon-right {
  color: var(--ink-soft);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 0;
  color: var(--ink-soft);
}
.empty-icon {
  opacity: 0.5;
}

@media (max-width: 768px) {
  .filter-bar {
    grid-template-columns: minmax(0, 1fr) 112px;
    gap: 8px;
  }

  .status-select {
    width: 100%;
  }

  .exam-card {
    align-items: flex-start;
  }

  .card-side {
    min-width: 108px;
    justify-content: flex-end;
    align-self: center;
  }

  .status-badge {
    max-width: 100%;
  }
}
</style>


