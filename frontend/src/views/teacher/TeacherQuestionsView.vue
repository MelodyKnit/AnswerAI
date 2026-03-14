<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Search, Sparkles, Filter, Database } from 'lucide-vue-next'
import { getQuestions } from '@/api/teacher'

const questions = ref<any[]>([])
const isLoading = ref(true)
const keyword = ref('')

const fetchQuestions = async () => {
  try {
    isLoading.value = true
    const res = await getQuestions({ keyword: keyword.value || undefined })
    questions.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to fetch questions', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchQuestions()
})

const getQType = (type: string) => {
  const map: Record<string, string> = {
    'single_choice': '单选题',
    'multiple_choice': '多选题',
    'fill_blank': '填空题',
    'subjective': '主观题'
  }
  return map[type] || type
}

const getDifficulty = (diff: number) => {
  if (diff <= 0.34) return '简单'
  if (diff <= 0.67) return '中等'
  return '困难'
}
</script>

<template>
  <div class="view-questions">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">题库中心</h1>
        <div class="header-actions">
          <button class="icon-button ai-btn" aria-label="AI智能出题">
            <Sparkles :size="18" />
          </button>
          <button class="button button--small">
            <Plus :size="16" />
            <span>录入试题</span>
          </button>
        </div>
      </div>
      <p class="page-desc">管理您的专属题库，支持 AI 辅助出题与解析。</p>
    </header>

    <div class="search-section">
      <div class="search-bar">
        <Search :size="16" class="search-icon" />
        <input type="text" placeholder="搜索题目内容、知识点..." class="search-input" v-model="keyword" @keyup.enter="fetchQuestions" />
      </div>
      <button class="icon-button filter-btn" @click="fetchQuestions">
        <Filter :size="18" />
      </button>
    </div>

    <div class="filter-chips">
      <span class="chip active">全部</span>
      <span class="chip">单选题</span>
      <span class="chip">主观题</span>
      <span class="chip">易错题</span>
    </div>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <div v-else-if="questions.length === 0" class="empty-state">
      <Database :size="48" class="empty-icon" />
      <p>题库空空如也</p>
      <button class="button button--primary" style="margin-top: 12px;">
        <Sparkles :size="16" style="margin-right: 6px"/> 尝试 AI 生成题目
      </button>
    </div>

    <div v-else class="question-list">
      <div v-for="q in questions" :key="q.id" class="question-card">
        <div class="q-header">
          <div class="q-meta">
            <span class="q-type">{{ getQType(q.type) }}</span>
            <span class="q-diff">{{ getDifficulty(q.difficulty || 0.5) }}</span>
          </div>
          <span class="q-subject">{{ q.subject }}</span>
        </div>
        
        <div class="q-content">
          {{ q.stem }}
        </div>
        
        <div class="q-footer">
          <div class="q-knowledge">
            <span v-for="k in (q.knowledge_points || [])" :key="k.id" class="k-tag">#{{ k.name }}</span>
          </div>
          <button class="button button--ghost button--small">解析</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-questions {
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

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.icon-button.ai-btn {
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.1);
  padding: 6px;
  border-radius: 8px;
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

.search-section {
  display: flex;
  gap: 12px;
}

.search-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid var(--line);
  padding: 8px 12px;
  border-radius: var(--radius-md);
}

.search-icon {color: var(--ink-soft);}
.search-input {
  border: none;
  background: none;
  outline: none;
  width: 100%;
  font-size: 14px;
}

.filter-btn {
  padding: 8px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  color: var(--ink);
}

.filter-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  -ms-overflow-style: none;  
  scrollbar-width: none;  
}
.filter-chips::-webkit-scrollbar { 
  display: none; 
}

.chip {
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 20px;
  background: var(--bg);
  color: var(--ink-soft);
  white-space: nowrap;
  border: 1px solid transparent;
  cursor: pointer;
}
.chip.active {
  background: #fff;
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 500;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  color: var(--ink-soft);
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.5;
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.q-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.q-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.q-type {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent);
  background: rgba(37, 99, 235, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.q-diff {
  font-size: 12px;
  color: var(--ink-soft);
}

.q-subject {
  font-size: 12px;
  color: var(--ink-soft);
}

.q-content {
  font-size: 15px;
  line-height: 1.6;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.q-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
}

.q-knowledge {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.k-tag {
  font-size: 12px;
  color: var(--ink-soft);
}
</style>


