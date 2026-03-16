<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle2, ImageOff } from 'lucide-vue-next'
import { getQuestionDetail } from '@/api/teacher'
import ImageLightbox from '@/components/common/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const questionId = Number(route.params.id)

const question = ref<any | null>(null)
const isLoading = ref(true)
const errorText = ref('')
const isLightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('题目插图')

const apiBase = String(import.meta.env.VITE_API_URL || '/api/v1')

const getBackendOrigin = () => {
  if (/^https?:\/\//i.test(apiBase)) {
    try {
      return new URL(apiBase).origin
    } catch {
      return ''
    }
  }
  return ''
}

const normalizeAssetUrl = (rawUrl: string) => {
  const trimmed = rawUrl.trim()
  if (!trimmed) return ''
  if (/^(https?:)?\/\//i.test(trimmed) || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return trimmed
  }
  const backendOrigin = getBackendOrigin()
  if (trimmed.startsWith('/')) {
    return backendOrigin ? `${backendOrigin}${trimmed}` : trimmed
  }
  return backendOrigin ? `${backendOrigin}/${trimmed.replace(/^\/+/, '')}` : trimmed
}

const escapeHtml = (value: string) => {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderRichText = (value?: string) => {
  if (!value) return ''
  const escaped = escapeHtml(value)
  return escaped
    .replace(/!\[[^\]]*\]\(([^)]+)\)/g, (_, src) => `<img class="preview-rich-image" src="${normalizeAssetUrl(src)}" alt="题目插图" onerror="this.dataset.failed=1" />`)
    .replace(/\n/g, '<br />')
}

const questionTypeText = computed(() => {
  const type = question.value?.type
  if (type === 'single_choice') return '单选题'
  if (type === 'multiple_choice') return '多选题'
  if (type === 'judge') return '判断题'
  if (type === 'blank') return '填空题'
  return '主观题'
})

const answerText = computed(() => {
  const current = question.value
  if (!current) return '未设置'
  if (current.type === 'multiple_choice') {
    return Array.isArray(current.answer) ? current.answer.join('、') : String(current.answer || '')
  }
  if (current.type === 'blank') {
    return Array.isArray(current.answer) ? current.answer.join('；') : String(current.answer || '')
  }
  if (current.type === 'judge') {
    return String(current.answer || '') === 'TRUE' ? '正确' : '错误'
  }
  return Array.isArray(current.answer) ? String(current.answer[0] || '') : String(current.answer || '')
})

const difficultyText = computed(() => {
  const diff = Number(question.value?.difficulty ?? 0.5)
  if (diff <= 0.34) return '简单'
  if (diff <= 0.67) return '中等'
  return '困难'
})

const backToBank = () => {
  router.push('/app/teacher/questions')
}

const handleRichImageClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  const image = target?.closest('img') as HTMLImageElement | null
  if (!image) return
  event.preventDefault()
  event.stopPropagation()
  lightboxSrc.value = image.currentSrc || image.src
  lightboxAlt.value = image.alt || '题目插图'
  isLightboxOpen.value = true
}

onMounted(async () => {
  try {
    const res = await getQuestionDetail(questionId)
    question.value = (res as any)?.question || null
  } catch (error: any) {
    errorText.value = error?.message || '题目预览加载失败'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="question-preview-page">
    <header class="preview-topbar">
      <button class="back-btn" @click="backToBank">
        <ArrowLeft :size="18" />
        返回题库
      </button>
      <div class="topbar-meta" v-if="question">
        <span class="type-pill">{{ questionTypeText }}</span>
        <span class="meta-text">{{ question.subject }} · {{ difficultyText }}</span>
      </div>
    </header>

    <div v-if="isLoading" class="state-shell">正在加载题目预览...</div>
    <div v-else-if="errorText" class="state-shell">{{ errorText }}</div>
    <main v-else-if="question" class="preview-layout" @click.capture="handleRichImageClick">
      <section class="preview-hero">
        <h1>题目预览</h1>
      </section>

      <section class="preview-paper">
        <div class="paper-head">
          <div>
            <p class="paper-subject">{{ question.subject }}</p>
            <h2>{{ questionTypeText }}</h2>
          </div>
          <span class="score-badge">{{ question.score }} 分</span>
        </div>

        <article class="paper-card">
          <div class="paper-stem" v-html="renderRichText(question.stem)"></div>

          <div v-if="['single_choice', 'multiple_choice', 'judge'].includes(question.type)" class="option-list">
            <div v-for="opt in (question.options || [])" :key="opt.key" class="option-row">
              <span class="option-key">{{ opt.key }}</span>
              <div class="option-body" v-html="renderRichText(opt.content)"></div>
            </div>
          </div>

          <div v-if="question.type === 'blank'" class="answer-box">
            <span class="box-label">填空答案</span>
            <p>{{ answerText }}</p>
          </div>
        </article>
      </section>

      <aside class="preview-sidebar">
        <section class="side-card">
          <div class="side-title-row">
            <CheckCircle2 :size="16" />
            <h3>标准答案</h3>
          </div>
          <p class="answer-highlight">{{ answerText }}</p>
        </section>

        <section class="side-card" v-if="question.analysis">
          <div class="side-title-row">
            <ImageOff :size="16" />
            <h3>解析检查</h3>
          </div>
          <div class="analysis-content" v-html="renderRichText(question.analysis)"></div>
        </section>
      </aside>
    </main>

    <ImageLightbox v-model="isLightboxOpen" :src="lightboxSrc" :alt="lightboxAlt" />
  </div>
</template>

<style scoped>
.question-preview-page {
  min-height: 100%;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background:
    radial-gradient(circle at 100% -10%, rgba(15, 118, 110, 0.12), transparent 34%),
    linear-gradient(180deg, #f8fafc 0%, #f3f6fb 100%);
}

.preview-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.88);
  color: var(--ink);
  border-radius: 999px;
  padding: 8px 12px;
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-pill {
  font-size: 12px;
  color: var(--accent);
  background: rgba(37, 99, 235, 0.1);
  border-radius: 999px;
  padding: 4px 8px;
}

.meta-text {
  font-size: 12px;
  color: var(--ink-soft);
}

.state-shell {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  color: var(--ink-soft);
}

.preview-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  gap: 14px;
}

.preview-hero,
.preview-paper,
.preview-sidebar {
  min-width: 0;
}

.preview-hero {
  grid-column: 1 / -1;
  border: 1px solid #d9e2ee;
  border-radius: 18px;
  background: linear-gradient(135deg, #ffffff, #eef6ff);
  padding: 12px 16px;
  min-height: 0;
}

.preview-hero h1 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}

.preview-hero p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.6;
}

.hero-kicker {
  font-size: 12px;
  color: var(--accent);
}

.preview-paper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.paper-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.paper-subject {
  margin: 0 0 4px;
  color: var(--ink-soft);
  font-size: 12px;
}

.paper-head h2 {
  margin: 0;
  font-size: 22px;
}

.score-badge {
  border-radius: 999px;
  background: #e8f4ee;
  color: #16634f;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
}

.paper-card,
.side-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
}

.paper-stem,
.option-body,
.analysis-content {
  font-size: 15px;
  line-height: 1.75;
  color: var(--ink);
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.option-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border: 1px solid #dde5f0;
  border-radius: 12px;
  padding: 12px;
  background: #f9fbff;
}

.option-key {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.preview-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.side-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--ink);
}

.side-title-row h3 {
  margin: 0;
  font-size: 15px;
}

.answer-highlight {
  margin: 0;
  font-size: 20px;
  color: #16634f;
  font-weight: 700;
}

.answer-box {
  margin-top: 14px;
  border-top: 1px dashed var(--line);
  padding-top: 12px;
}

.box-label {
  font-size: 12px;
  color: var(--ink-soft);
}

.answer-box p {
  margin: 6px 0 0;
}

:deep(.preview-rich-image) {
  display: block;
  max-width: 100%;
  margin: 12px 0;
  border-radius: 12px;
  border: 1px solid #dbe4ef;
  background: #fff;
  cursor: zoom-in;
}

@media (max-width: 900px) {
  .preview-layout {
    grid-template-columns: 1fr;
  }
}
</style>