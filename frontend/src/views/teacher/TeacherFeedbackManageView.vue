<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Filter, Image as ImageIcon, MessageSquareWarning, RefreshCw, Search } from 'lucide-vue-next'
import ImageLightbox from '@/components/common/ImageLightbox.vue'
import { getTeacherFeedbackList, type TeacherFeedbackItem } from '@/api/teacher'

type Category = 'all' | 'bug' | 'product' | 'design' | 'other'

const loading = ref(true)
const refreshing = ref(false)
const keyword = ref('')
const category = ref<Category>('all')
const items = ref<TeacherFeedbackItem[]>([])
const total = ref(0)
const summary = ref({ bug: 0, product: 0, design: 0, other: 0 })

const isLightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('反馈截图')

const categoryOptions: Array<{ value: Category; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'bug', label: 'BUG反馈' },
  { value: 'product', label: '软件反馈' },
  { value: 'design', label: '设计建议' },
  { value: 'other', label: '其他' },
]

const categoryTextMap: Record<string, string> = {
  bug: 'BUG反馈',
  product: '软件反馈',
  design: '设计建议',
  other: '其他',
}

const categoryClass = (value: string) => `cat-${value || 'other'}`
const categoryText = (value: string) => categoryTextMap[value] || '其他'

const formatDateTime = (value: string) => {
  const time = new Date(value)
  if (Number.isNaN(time.getTime())) return '--'
  const y = time.getFullYear()
  const m = String(time.getMonth() + 1).padStart(2, '0')
  const d = String(time.getDate()).padStart(2, '0')
  const hh = String(time.getHours()).padStart(2, '0')
  const mm = String(time.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const totalImageCount = computed(() => items.value.reduce((sum, row) => sum + row.images.length, 0))

const fetchFeedback = async (silent = false) => {
  if (silent) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  try {
    const res = await getTeacherFeedbackList({
      category: category.value === 'all' ? undefined : (category.value as 'bug' | 'product' | 'design' | 'other'),
      keyword: keyword.value.trim() || undefined,
      page: 1,
      page_size: 50,
    })
    items.value = res?.items || []
    total.value = Number(res?.total || 0)
    summary.value = {
      bug: Number(res?.summary?.bug || 0),
      product: Number(res?.summary?.product || 0),
      design: Number(res?.summary?.design || 0),
      other: Number(res?.summary?.other || 0),
    }
  } catch (error) {
    console.error('load feedback failed', error)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const applyFilter = async () => {
  await fetchFeedback(true)
}

const openImage = (url: string) => {
  lightboxSrc.value = url
  lightboxAlt.value = '反馈截图'
  isLightboxOpen.value = true
}

onMounted(async () => {
  await fetchFeedback()
})
</script>

<template>
  <div class="feedback-view">
    <header class="head">
      <h1>反馈管理</h1>
      <p>集中查看教师与学生提交的问题、建议与截图证据。</p>
    </header>

    <section class="summary-grid">
      <article class="summary-card">
        <p>反馈总数</p>
        <strong>{{ total }}</strong>
      </article>
      <article class="summary-card">
        <p>截图总数</p>
        <strong>{{ totalImageCount }}</strong>
      </article>
      <article class="summary-card">
        <p>BUG反馈</p>
        <strong>{{ summary.bug }}</strong>
      </article>
      <article class="summary-card">
        <p>设计建议</p>
        <strong>{{ summary.design }}</strong>
      </article>
    </section>

    <section class="toolbar">
      <div class="filter-row">
        <label class="select-wrap">
          <Filter :size="14" />
          <select v-model="category" @change="applyFilter">
            <option v-for="item in categoryOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>

        <label class="search-wrap">
          <Search :size="14" />
          <input v-model="keyword" type="text" placeholder="搜索描述、页面路径、反馈人" @keyup.enter="applyFilter" />
        </label>
      </div>

      <button class="refresh-btn" :disabled="loading || refreshing" @click="fetchFeedback(true)">
        <RefreshCw :size="14" :class="{ spinning: refreshing }" />
        刷新
      </button>
    </section>

    <section v-if="loading" class="state-box">正在加载反馈...</section>
    <section v-else-if="!items.length" class="state-box">当前暂无符合条件的反馈</section>

    <section v-else class="list-wrap">
      <article v-for="item in items" :key="item.id" class="feedback-card">
        <div class="card-head">
          <span class="category-pill" :class="categoryClass(item.category)">{{ categoryText(item.category) }}</span>
          <span class="created-at">{{ formatDateTime(item.created_at) }}</span>
        </div>

        <p class="content">{{ item.content || '（无文字描述）' }}</p>

        <div class="meta-row">
          <span class="meta-pill">反馈人：{{ item.client_name || '匿名' }}</span>
          <span class="meta-pill">角色：{{ item.client_role || '--' }}</span>
          <span v-if="item.page_path" class="meta-pill">页面：{{ item.page_path }}</span>
        </div>

        <div v-if="item.images.length" class="image-row">
          <button
            v-for="(url, index) in item.images"
            :key="`${item.id}-${index}`"
            class="image-btn"
            type="button"
            @click="openImage(url)"
          >
            <img :src="url" alt="反馈截图" />
            <span>
              <ImageIcon :size="12" />
              查看截图
            </span>
          </button>
        </div>
        <div v-else class="no-image">
          <MessageSquareWarning :size="14" />
          未附截图
        </div>
      </article>
    </section>

    <ImageLightbox v-model="isLightboxOpen" :src="lightboxSrc" :alt="lightboxAlt" />
  </div>
</template>

<style scoped>
.feedback-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.head h1 {
  margin: 0;
  font-size: 28px;
}

.head p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #5d6d7f;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.summary-card {
  border: 1px solid #dce6ef;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  display: grid;
  gap: 4px;
}

.summary-card p {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.summary-card strong {
  font-size: 22px;
  color: #0f172a;
}

.toolbar {
  border: 1px solid #dce6ef;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.select-wrap,
.search-wrap {
  border: 1px solid #d5dee8;
  border-radius: 10px;
  background: #f8fafc;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  color: #64748b;
}

.select-wrap select,
.search-wrap input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: #0f172a;
}

.refresh-btn {
  align-self: flex-end;
  border: 1px solid #d5dee8;
  border-radius: 9px;
  background: #fff;
  color: #334155;
  height: 34px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}

.spinning {
  animation: spin 0.9s linear infinite;
}

.state-box {
  border: 1px solid #dce6ef;
  border-radius: 12px;
  background: #fff;
  padding: 18px 14px;
  color: #526070;
  font-size: 13px;
}

.list-wrap {
  display: grid;
  gap: 10px;
}

.feedback-card {
  border: 1px solid #dce6ef;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.category-pill {
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 11px;
  color: #fff;
}

.category-pill.cat-bug {
  background: #dc2626;
}

.category-pill.cat-product {
  background: #2563eb;
}

.category-pill.cat-design {
  background: #0f766e;
}

.category-pill.cat-other {
  background: #64748b;
}

.created-at {
  font-size: 12px;
  color: #64748b;
}

.content {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: #0f172a;
  white-space: pre-wrap;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-pill {
  border: 1px solid #dce5ef;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  color: #4a5d75;
  background: #f8fafc;
}

.image-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.image-btn {
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
  padding: 0;
  text-align: left;
}

.image-btn img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.image-btn span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 6px 8px;
  border-top: 1px solid #e4ebf2;
  font-size: 11px;
  color: #475569;
}

.no-image {
  border: 1px dashed #d7e1eb;
  border-radius: 10px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .image-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
