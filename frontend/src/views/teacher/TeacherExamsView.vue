<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, FileText, ChevronRight } from 'lucide-vue-next'
import { getExams } from '@/api/teacher'

const router = useRouter()
const exams = ref<any[]>([])
const isLoading = ref(true)
const filterStatus = ref('all') // all, draft, published, finished
const keyword = ref('')

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

const goDetail = (id: number) => {
  router.push(`/app/teacher/exams/${id}`)
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'draft': return 'var(--ink-soft)'
    case 'published': return 'var(--success, #10b981)'
    case 'finished': return 'var(--ink-soft)'
    default: return 'var(--ink)'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'draft': return '草稿'
    case 'published': return '进行中'
    case 'finished': return '已结束'
    default: return status
  }
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
      <select class="status-select" v-model="filterStatus" @change="fetchExams">
        <option value="all">所有状态</option>
        <option value="draft">草稿</option>
        <option value="published">进行中</option>
        <option value="finished">已结束</option>
      </select>
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
        @click="goDetail(exam.id)"
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
          <span 
            class="status-badge" 
            :style="{ color: getStatusColor(exam.status) }"
          >
            {{ getStatusText(exam.status) }}
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
  display: flex;
  gap: 12px;
}

.search-box {
  flex: 1;
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
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 0 12px;
  background: #fff;
  font-size: 14px;
  color: var(--ink);
  outline: none;
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
}

.exam-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink);
}

.exam-meta {
  font-size: 13px;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
}

.dot {
  margin: 0 6px;
}

.card-side {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  font-size: 13px;
  font-weight: 500;
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
</style>


