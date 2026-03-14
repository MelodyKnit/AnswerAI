<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Search, Filter, Calendar } from 'lucide-vue-next'
import http from '@/lib/http'

interface Exam {
  id: string
  title: string
  subject: string
  duration_minutes: number
  status: string
  start_time: string
  end_time: string
}

const exams = ref<Exam[]>([])
const loading = ref(true)
const activeTab = ref('upcoming') // 'upcoming', 'ongoing', 'finished'

const fetchExams = async () => {
  loading.value = true
  try {
    const res = await http.get(`/student/exams`, {
      params: { status: activeTab.value, page: 1, page_size: 20 }
    })
    exams.value = res.data.data.items || []
  } catch (error) {
    console.error('Failed to fetch exams:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchExams()
})

const switchTab = (tab: string) => {
  activeTab.value = tab
  fetchExams()
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="view-exams">
    <!-- Header -->
    <header class="page-header">
      <h1 class="page-title">全部考试</h1>
      <div class="header-actions">
        <button class="icon-button"><Search :size="20" /></button>
        <button class="icon-button"><Filter :size="20" /></button>
      </div>
    </header>

    <!-- Tabs -->
    <div class="tabs">
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'upcoming' }"
        @click="switchTab('upcoming')"
      >待考试</button>
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'ongoing' }"
        @click="switchTab('ongoing')"
      >进行中</button>
      <button 
        class="tab-item" 
        :class="{ active: activeTab === 'finished' }"
        @click="switchTab('finished')"
      >已结束</button>
    </div>

    <!-- Exam List -->
    <div class="exam-list" v-if="!loading && exams.length">
      <div v-for="exam in exams" :key="exam.id" class="exam-card">
        <div class="exam-header">
          <h3>{{ exam.title }}</h3>
          <span class="status-badge" :class="activeTab">{{ activeTab === 'upcoming' ? '未开始' : (activeTab === 'ongoing' ? '进行中' : '已结束') }}</span>
        </div>
        <div class="exam-body">
          <div class="meta-row">
            <span class="meta-label">科目</span>
            <span class="meta-value">{{ exam.subject || '综合' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">时长</span>
            <span class="meta-value">{{ exam.duration_minutes }} 分钟</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">时间</span>
            <span class="meta-value time"><Calendar :size="14" class="icon-m" /> {{ formatDate(exam.start_time) }} - {{ formatDate(exam.end_time) }}</span>
          </div>
        </div>
        <div class="exam-footer">
          <RouterLink :to="`/app/student/exams/${exam.id}/prep`" class="button" v-if="activeTab !== 'finished'">
            {{ activeTab === 'upcoming' ? '查看详情' : '进入考试' }}
          </RouterLink>
          <RouterLink :to="`/app/student/results/${exam.id}`" class="button button--outline" v-else>
            查看成绩
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div class="empty-state" v-if="!loading && exams.length === 0">
      <div class="empty-icon">📝</div>
      <p>暂无相关考试</p>
    </div>

    <!-- Loading State -->
    <div class="loading-state" v-if="loading">
      加载中...
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
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.icon-button {
  background: none;
  border: none;
  color: var(--ink);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 2px;
}

.tab-item {
  background: none;
  border: none;
  font-size: 15px;
  color: var(--ink-soft);
  padding: 8px 4px;
  cursor: pointer;
  position: relative;
  font-weight: 500;
  transition: color 0.2s ease;
}

.tab-item.active {
  color: var(--ink);
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -3px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
  border-radius: 2px;
}

.exam-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.exam-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.exam-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}

.status-badge.upcoming {
  background: var(--bg);
  color: var(--ink-soft);
}

.status-badge.ongoing {
  background: #eef2ff;
  color: #3b82f6;
}

.status-badge.finished {
  background: #f1f5f9;
  color: #64748b;
}

.exam-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg);
  padding: 12px;
  border-radius: var(--radius-sm);
}

.meta-row {
  display: flex;
  font-size: 13px;
}

.meta-label {
  color: var(--ink-soft);
  width: 60px;
  flex-shrink: 0;
}

.meta-value {
  color: var(--ink);
  font-weight: 500;
}

.meta-value.time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 400;
}

.icon-m {
  margin-top: -2px;
}

.exam-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

.button {
  padding: 10px 24px;
  font-size: 14px;
}

.button--outline {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--ink);
  box-shadow: none;
}

.button--outline:hover {
  background: var(--bg);
  transform: translateY(-1px);
}

.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--ink-soft);
  font-size: 14px;
  text-align: center;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 16px;
  opacity: 0.5;
}
</style>
