<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronDown, Database, Eye, Filter, ImagePlus, Pencil, Plus, Search, Sparkles, Trash2, X } from 'lucide-vue-next'
import { createQuestion, deleteQuestion, generateQuestionsByAi, getQuestionSubjects, getQuestions, updateQuestion } from '@/api/teacher'
import { getQuestionTypes } from '@/api/meta'
import http from '@/lib/http'
import { useRouter } from 'vue-router'
import { useUiDialog } from '@/composables/useUiDialog'

type OptionInput = {
  key: string
  content: string
}

type BlankAnswer = {
  id: number
  content: string
}

type FormState = {
  subject: string
  type: string
  stem: string
  options: OptionInput[]
  blankAnswers: BlankAnswer[]
  answerText: string
  analysis: string
  score: number
  difficulty: number
}

const DEFAULT_OPTIONS: OptionInput[] = [
  { key: 'A', content: '' },
  { key: 'B', content: '' },
  { key: 'C', content: '' },
  { key: 'D', content: '' },
]

const questions = ref<any[]>([])
const subjects = ref<string[]>([])
const questionTypes = ref<Array<{ code: string, name: string }>>([])

const isLoading = ref(true)
const isLoadingMore = ref(false)
const isSaving = ref(false)
const keyword = ref('')
const activeTypeFilter = ref('all')
const activeSubjectFilter = ref('all')
const isEditorOpen = ref(false)
const editingQuestionId = ref<number | null>(null)
const currentPage = ref(1)
const pageSize = 24
const totalQuestions = ref(0)
const loadMoreAnchor = ref<HTMLElement | null>(null)
let loadMoreObserver: IntersectionObserver | null = null

const isAiDialogOpen = ref(false)
const isAiGenerating = ref(false)
const aiRequirement = ref('')

const stemImageInput = ref<HTMLInputElement | null>(null)
const analysisImageInput = ref<HTMLInputElement | null>(null)
const optionImageInput = ref<HTMLInputElement | null>(null)
const currentOptionImageIndex = ref<number | null>(null)
const router = useRouter()
const ui = useUiDialog()

const uploadImage = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/upload/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

const createDefaultForm = (): FormState => ({
  subject: '',
  type: 'single_choice',
  stem: '',
  options: DEFAULT_OPTIONS.map((item) => ({ ...item })),
  blankAnswers: [{ id: 1, content: '' }],
  answerText: '',
  analysis: '',
  score: 5,
  difficulty: 0.5,
})

const form = ref<FormState>(createDefaultForm())
const subjectMenuOpen = ref(false)
const typeMenuOpen = ref(false)
const subjectFilterMenuOpen = ref(false)

const isChoiceQuestion = computed(() => ['single_choice', 'multiple_choice'].includes(form.value.type))
const hasMoreQuestions = computed(() => questions.value.length < totalQuestions.value)
const loadedSummary = computed(() => {
  if (!totalQuestions.value) return '暂无题目'
  return `已加载 ${questions.value.length} / ${totalQuestions.value} 题`
})

const uniqueSubjects = computed(() => {
  return subjects.value
})

const currentTypeLabel = computed(() => {
  const current = questionTypes.value.find((item) => item.code === form.value.type)
  return current?.name || '请选择题型'
})

const subjectFilterOptions = computed(() => {
  return ['all', ...uniqueSubjects.value]
})

const currentSubjectFilterLabel = computed(() => {
  if (activeSubjectFilter.value === 'all') {
    return '全部科目'
  }
  return activeSubjectFilter.value
})

const filteredSubjectOptions = computed(() => {
  const keyword = form.value.subject.trim().toLowerCase()
  const source = Array.from(
    new Set(uniqueSubjects.value.map((name) => String(name || '').trim()).filter(Boolean)),
  )
  if (!keyword) {
    return source
  }
  const startsWith = source.filter((name) => name.toLowerCase().startsWith(keyword))
  const includes = source.filter(
    (name) => !name.toLowerCase().startsWith(keyword) && name.toLowerCase().includes(keyword),
  )
  const rest = source.filter(
    (name) => !name.toLowerCase().startsWith(keyword) && !name.toLowerCase().includes(keyword),
  )
  return [...startsWith, ...includes, ...rest]
})

const onSubjectInput = () => {
  subjectMenuOpen.value = true
}

const closeSubjectMenuLater = () => {
  window.setTimeout(() => {
    subjectMenuOpen.value = false
  }, 120)
}

const chooseSubject = (name: string) => {
  form.value.subject = name
  subjectMenuOpen.value = false
}

const closeTypeMenuLater = () => {
  window.setTimeout(() => {
    typeMenuOpen.value = false
  }, 120)
}

const chooseType = (code: string) => {
  form.value.type = code
  typeMenuOpen.value = false
}

const closeSubjectFilterMenuLater = () => {
  window.setTimeout(() => {
    subjectFilterMenuOpen.value = false
  }, 120)
}

const chooseSubjectFilter = (subject: string) => {
  activeSubjectFilter.value = subject
  subjectFilterMenuOpen.value = false
}

const fetchQuestionSubjects = async () => {
  try {
    const res = await getQuestionSubjects()
    const items = ((res as any).items || []) as string[]
    subjects.value = items.filter((name) => typeof name === 'string' && name.trim().length > 0)

    if (activeSubjectFilter.value !== 'all' && !subjects.value.includes(activeSubjectFilter.value)) {
      activeSubjectFilter.value = 'all'
    }
    if (!form.value.subject && subjects.value.length > 0) {
      form.value.subject = subjects.value[0]
    }
  } catch (error) {
    console.error('Failed to fetch question subjects', error)
    subjects.value = []
  }
}

const fetchMeta = async () => {
  try {
    const [typeRes] = await Promise.all([getQuestionTypes()])
    questionTypes.value = (typeRes as any).items || []
    await fetchQuestionSubjects()
  } catch (error) {
    console.error('Failed to fetch question metadata', error)
  }
}

const fetchQuestions = async (reset = true) => {
  const targetPage = reset ? 1 : currentPage.value + 1
  try {
    if (reset) {
      isLoading.value = true
    } else {
      isLoadingMore.value = true
    }
    const res = await getQuestions({
      page: targetPage,
      page_size: pageSize,
      subject: activeSubjectFilter.value !== 'all' ? activeSubjectFilter.value : undefined,
      keyword: keyword.value || undefined,
      type: activeTypeFilter.value !== 'all' ? activeTypeFilter.value : undefined,
    })
    const items = (res as any).items || []
    totalQuestions.value = Number((res as any).total || 0)
    currentPage.value = targetPage
    questions.value = reset ? items : [...questions.value, ...items]
  } catch (error) {
    console.error('Failed to fetch questions', error)
  } finally {
    isLoading.value = false
    isLoadingMore.value = false
  }
}

const loadMoreQuestions = async () => {
  if (isLoading.value || isLoadingMore.value || !hasMoreQuestions.value) return
  await fetchQuestions(false)
}

const syncLoadMoreObserver = async () => {
  await nextTick()
  if (loadMoreObserver) {
    loadMoreObserver.disconnect()
    loadMoreObserver = null
  }
  if (!loadMoreAnchor.value) return
  loadMoreObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadMoreQuestions()
      }
    },
    { rootMargin: '180px 0px' },
  )
  loadMoreObserver.observe(loadMoreAnchor.value)
}

onMounted(async () => {
  await fetchMeta()
  await fetchQuestions(true)
  await syncLoadMoreObserver()
})

onBeforeUnmount(() => {
  loadMoreObserver?.disconnect()
})

watch([activeTypeFilter, activeSubjectFilter], async () => {
  await fetchQuestions(true)
  await syncLoadMoreObserver()
})

watch(loadMoreAnchor, async () => {
  await syncLoadMoreObserver()
})

watch(
  () => form.value.type,
  (type) => {
    if (['single_choice', 'multiple_choice'].includes(type) && form.value.options.length < 2) {
      form.value.options = DEFAULT_OPTIONS.map((item) => ({ ...item }))
    }
    if (type === 'blank' && form.value.blankAnswers.length === 0) {
      form.value.blankAnswers = [{ id: 1, content: '' }]
    }
    if (type === 'judge' && !['TRUE', 'FALSE'].includes(form.value.answerText)) {
      form.value.answerText = ''
    }
  }
)

const getQType = (type: string) => {
  const fromMeta = questionTypes.value.find((item) => item.code === type)
  if (fromMeta) {
    return fromMeta.name
  }
  const map: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    judge: '判断题',
    blank: '填空题',
    essay: '简答题',
    material: '材料题',
  }
  return map[type] || type
}

const getDifficulty = (diff: number) => {
  if (diff <= 0.34) return '简单'
  if (diff <= 0.67) return '中等'
  return '困难'
}

const openPreview = (question: any) => {
  router.push(`/app/teacher/questions/${question.id}/preview`)
}

const resetForm = () => {
  form.value = createDefaultForm()
  form.value.subject = uniqueSubjects.value[0] || '默认科目'
  form.value.type = questionTypes.value[0]?.code || 'single_choice'
}

const openCreate = () => {
  editingQuestionId.value = null
  resetForm()
  isEditorOpen.value = true
}

const normalizeAnswerText = (type: string, answer: any): string => {
  if (type === 'multiple_choice') {
    return Array.isArray(answer) ? answer.map((x) => String(x).toUpperCase()).join(',') : String(answer || '')
  }
  if (type === 'blank') {
    return ''
  }
  if (Array.isArray(answer)) {
    return String(answer[0] || '')
  }
  return String(answer || '')
}

const openEdit = (question: any) => {
  editingQuestionId.value = question.id
  const parsedOptions: OptionInput[] = Array.isArray(question.options) && question.options.length > 0
    ? question.options.map((item: any, idx: number) => ({
      key: String(item.key || String.fromCharCode(65 + idx)).toUpperCase(),
      content: String(item.content || ''),
    }))
    : DEFAULT_OPTIONS.map((item) => ({ ...item }))

  const parsedBlanks: BlankAnswer[] = question.type === 'blank'
    ? (Array.isArray(question.answer) && question.answer.length > 0
      ? question.answer.map((ans: any, i: number) => ({ id: i + 1, content: String(ans || '') }))
      : [{ id: 1, content: typeof question.answer === 'string' ? question.answer : '' }])
    : [{ id: 1, content: '' }]

  form.value = {
    subject: question.subject || uniqueSubjects.value[0] || '',
    type: question.type || 'single_choice',
    stem: question.stem || '',
    options: parsedOptions,
    blankAnswers: parsedBlanks,
    answerText: normalizeAnswerText(question.type || 'single_choice', question.answer),
    analysis: question.analysis || '',
    score: Number(question.score || 5),
    difficulty: Number(question.difficulty ?? 0.5),
  }
  isEditorOpen.value = true
}

const closeEditor = () => {
  isEditorOpen.value = false
  editingQuestionId.value = null
}

const addOption = () => {
  if (form.value.options.length >= 8) return
  const key = String.fromCharCode(65 + form.value.options.length)
  form.value.options.push({ key, content: '' })
}

const removeOption = (index: number) => {
  if (form.value.options.length <= 2) return
  form.value.options.splice(index, 1)
  form.value.options.forEach((opt, idx) => {
    opt.key = String.fromCharCode(65 + idx)
  })
  if (form.value.type === 'multiple_choice') {
    const selected = getMultipleChoiceSelected().filter((k) => form.value.options.some((o) => o.key === k))
    form.value.answerText = selected.join(',')
  }
  if (form.value.type === 'single_choice' && form.value.answerText && !form.value.options.some((o) => o.key === form.value.answerText)) {
    form.value.answerText = ''
  }
}

const addBlank = () => {
  if (form.value.blankAnswers.length >= 10) return
  form.value.blankAnswers.push({ id: form.value.blankAnswers.length + 1, content: '' })
}

const removeBlank = (index: number) => {
  if (form.value.blankAnswers.length <= 1) return
  form.value.blankAnswers.splice(index, 1)
  form.value.blankAnswers.forEach((item, idx) => {
    item.id = idx + 1
  })
}

const adjustNumber = (field: 'score' | 'difficulty', delta: number, min: number, max: number) => {
  let val = Number(form.value[field]) || 0
  val += delta
  val = Math.max(min, Math.min(max, val))
  if (field === 'difficulty') {
    val = Math.round(val * 100) / 100
  }
  form.value[field] = val
}

const getMultipleChoiceSelected = (): string[] => {
  return form.value.answerText
    .split(',')
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean)
}

const isChoiceSelected = (key: string): boolean => {
  if (form.value.type === 'single_choice') {
    return form.value.answerText === key
  }
  if (form.value.type === 'multiple_choice') {
    return getMultipleChoiceSelected().includes(key)
  }
  return false
}

const toggleChoiceAnswer = (key: string) => {
  if (form.value.type === 'single_choice') {
    form.value.answerText = key
    return
  }
  if (form.value.type === 'multiple_choice') {
    const selected = getMultipleChoiceSelected()
    const exists = selected.includes(key)
    const next = exists ? selected.filter((x) => x !== key) : [...selected, key]
    form.value.answerText = next.join(',')
  }
}

const setJudgeAnswer = (value: 'TRUE' | 'FALSE') => {
  form.value.answerText = value
}

const buildAnswer = () => {
  if (form.value.type === 'blank') {
    return form.value.blankAnswers.map((ans) => ans.content.trim())
  }
  if (form.value.type === 'multiple_choice') {
    return getMultipleChoiceSelected()
  }
  return form.value.answerText.trim().toUpperCase()
}

const submitEditor = async () => {
  const normalizedSubject = form.value.subject.trim()
  if (!normalizedSubject || !form.value.type || !form.value.stem.trim()) {
    await ui.alert('请完善科目、题型和题干', { tone: 'warning' })
    return
  }
  form.value.subject = normalizedSubject

  if (form.value.type === 'blank') {
    const hasEmptyBlank = form.value.blankAnswers.some((item) => !item.content.trim())
    if (hasEmptyBlank || form.value.blankAnswers.length === 0) {
      await ui.alert('请填写所有填空答案', { tone: 'warning' })
      return
    }
  } else if (!form.value.answerText.trim()) {
    await ui.alert('请先选择或填写答案', { tone: 'warning' })
    return
  }

  const options = isChoiceQuestion.value
    ? form.value.options
      .map((opt) => ({ key: opt.key, content: opt.content.trim() }))
      .filter((opt) => opt.content)
    : []

  if (isChoiceQuestion.value && options.length < 2) {
    await ui.alert('选择题至少需要两个有效选项', { tone: 'warning' })
    return
  }

  const payload = {
    subject: normalizedSubject,
    type: form.value.type,
    stem: form.value.stem.trim(),
    options,
    answer: buildAnswer(),
    analysis: form.value.analysis.trim() || null,
    score: Number(form.value.score),
    difficulty: Number(form.value.difficulty),
    knowledge_point_ids: [],
    ability_tags: [],
  }

  try {
    isSaving.value = true
    const isEditing = Boolean(editingQuestionId.value)
    if (editingQuestionId.value) {
      await updateQuestion({ question_id: editingQuestionId.value, ...payload })
    } else {
      await createQuestion(payload)
    }
    await fetchQuestionSubjects()
    await fetchQuestions(true)
    await syncLoadMoreObserver()

    if (isEditing) {
      ui.toast('修改成功', 'success')
    } else {
      ui.toast('新增成功', 'success')
      closeEditor()
    }
  } catch (error) {
    console.error('Failed to save question', error)
    const message = (error as any)?.message ? String((error as any).message) : '保存题目失败，请稍后重试'
    ui.toast(`保存失败：${message}`, 'error', 3600)
  } finally {
    isSaving.value = false
  }
}

const removeQuestion = async (questionId: number) => {
  const confirmed = await ui.confirm('确认删除该题目？删除后无法恢复。', {
    title: '删除题目',
    confirmText: '确认删除',
    tone: 'warning',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteQuestion(questionId)
    await fetchQuestionSubjects()
    await fetchQuestions(true)
    await syncLoadMoreObserver()
  } catch (error) {
    console.error('Failed to delete question', error)
    await ui.alert('删除题目失败，请稍后重试', { tone: 'error' })
  }
}

const appendMarkdownImage = (target: 'stem' | 'analysis', imageUrl: string) => {
  const markdown = `![图片](${imageUrl})`
  form.value[target] = form.value[target].trim() ? `${form.value[target]}\n${markdown}` : markdown
}

const appendOptionMarkdownImage = (index: number, imageUrl: string) => {
  const markdown = `![图片](${imageUrl})`
  const current = form.value.options[index].content || ''
  form.value.options[index].content = current.trim() ? `${current}\n${markdown}` : markdown
}

const doUploadAndInsert = async (
  file: File,
  target: 'stem' | 'analysis' | 'option',
  optionIndex?: number
) => {
  try {
    const res = await uploadImage(file)
    const imageUrl = (res as any).url
    if (!imageUrl) {
      throw new Error('上传失败，未返回地址')
    }
    if (target === 'option') {
      if (typeof optionIndex === 'number') {
        appendOptionMarkdownImage(optionIndex, imageUrl)
      }
      return
    }
    appendMarkdownImage(target, imageUrl)
  } catch (error) {
    console.error('Upload image failed', error)
    await ui.alert('图片上传失败，请稍后重试', { tone: 'error' })
  }
}

const triggerStemImage = () => stemImageInput.value?.click()
const triggerAnalysisImage = () => analysisImageInput.value?.click()
const triggerOptionImage = (index: number) => {
  currentOptionImageIndex.value = index
  optionImageInput.value?.click()
}

const onStemImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    await doUploadAndInsert(file, 'stem')
  }
  input.value = ''
}

const onAnalysisImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    await doUploadAndInsert(file, 'analysis')
  }
  input.value = ''
}

const onOptionImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  const optionIndex = currentOptionImageIndex.value
  if (file && optionIndex !== null) {
    await doUploadAndInsert(file, 'option', optionIndex)
  }
  currentOptionImageIndex.value = null
  input.value = ''
}

const onStemPaste = async (event: ClipboardEvent) => {
  const items = event.clipboardData?.items || []
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        event.preventDefault()
        await doUploadAndInsert(file, 'stem')
        return
      }
    }
  }
}

const openAiDialog = () => {
  isAiDialogOpen.value = true
}

const closeAiDialog = () => {
  isAiDialogOpen.value = false
  aiRequirement.value = ''
}

const applyGeneratedQuestion = (generated: any) => {
  if (!generated) {
    return
  }

  form.value.type = generated.type || form.value.type
  form.value.stem = generated.stem || form.value.stem
  form.value.analysis = generated.analysis || form.value.analysis

  if (Array.isArray(generated.options) && generated.options.length > 0) {
    form.value.options = generated.options.map((item: any, idx: number) => ({
      key: String(item.key || String.fromCharCode(65 + idx)).toUpperCase(),
      content: String(item.content || ''),
    }))
  }

  if (generated.type === 'blank') {
    const arr = Array.isArray(generated.answer) ? generated.answer : [generated.answer]
    form.value.blankAnswers = arr.map((item: any, idx: number) => ({ id: idx + 1, content: String(item || '') }))
    form.value.answerText = ''
  } else if (generated.type === 'multiple_choice') {
    const arr = Array.isArray(generated.answer) ? generated.answer : String(generated.answer || '').split(',')
    form.value.answerText = arr.map((x: any) => String(x).trim().toUpperCase()).filter(Boolean).join(',')
  } else {
    form.value.answerText = Array.isArray(generated.answer)
      ? String(generated.answer[0] || '')
      : String(generated.answer || '')
  }
}

const generateByAiAndApply = async () => {
  if (!form.value.subject || !form.value.type) {
    await ui.alert('请先选择科目和题型', { tone: 'warning' })
    return
  }
  if (!aiRequirement.value.trim()) {
    await ui.alert('请输入 AI 出题要求', { tone: 'warning' })
    return
  }

  try {
    isAiGenerating.value = true
    const res = await generateQuestionsByAi({
      subject: form.value.subject,
      grade_name: null,
      question_type: form.value.type,
      requirement: aiRequirement.value.trim(),
      knowledge_points: [],
      difficulty: Number(form.value.difficulty),
      count: 1,
      with_analysis: true,
    })
    const generatedList = (res as any).questions || []
    if (!generatedList.length) {
      await ui.alert('AI 未生成题目，请调整要求后重试', { tone: 'warning' })
      return
    }
    applyGeneratedQuestion(generatedList[0])
    closeAiDialog()
  } catch (error) {
    console.error('AI generate failed', error)
    await ui.alert('AI 出题失败，请稍后重试', { tone: 'error' })
  } finally {
    isAiGenerating.value = false
  }
}
</script>

<template>
  <div class="view-questions">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">题库中心</h1>
        <div class="header-actions">
          <button class="ai-btn" aria-label="AI智能出题" @click="openAiDialog">
            <Sparkles :size="16" />
          </button>
          <button class="button button--small" @click="openCreate">
            <Plus :size="16" />
            <span>录入试题</span>
          </button>
        </div>
      </div>
      <p class="page-desc">管理您的专属题库，支持 AI 辅助出题与解析。</p>
      <p class="page-stat">{{ loadedSummary }}</p>
    </header>

    <section v-if="isEditorOpen" class="editor-mask" @click.self="closeEditor">
      <div class="editor-panel">
        <div class="editor-header">
          <div>
            <h2>{{ editingQuestionId ? '编辑题目' : '新增题目' }}</h2>
            <p class="editor-subtitle">使用独立编辑卡片录入题干、答案、解析与插图，保存后自动刷新题库。</p>
          </div>
          <button class="close-editor-btn" @click="closeEditor" aria-label="关闭编辑器">
            <X :size="18" />
          </button>
        </div>

        <div class="editor-grid">
        <label class="form-field">
          <span>科目</span>
          <div class="subject-combobox" @focusout="closeSubjectMenuLater">
            <div class="subject-input-wrapper">
              <input
                v-model="form.subject"
                class="form-input"
                placeholder="请选择或输入科目"
                @focus="subjectMenuOpen = true"
                @input="onSubjectInput"
              />
              <button
                type="button"
                class="subject-toggle"
                aria-label="展开科目列表"
                @mousedown.prevent="subjectMenuOpen = !subjectMenuOpen"
              >
                <ChevronDown :size="16" :class="{ 'is-open': subjectMenuOpen }" />
              </button>
            </div>
            <div v-if="subjectMenuOpen" class="subject-menu">
              <button
                v-for="sub in filteredSubjectOptions"
                :key="sub"
                type="button"
                class="subject-menu-item"
                @mousedown.prevent="chooseSubject(sub)"
              >
                {{ sub }}
              </button>
              <p v-if="filteredSubjectOptions.length === 0" class="subject-menu-empty">
                暂无匹配项，直接保存可创建新科目
              </p>
            </div>
          </div>
        </label>

        <label class="form-field">
          <span>题型</span>
          <div class="dropdown" @focusout="closeTypeMenuLater">
            <button
              type="button"
              class="form-input dropdown-trigger"
              @mousedown.prevent="typeMenuOpen = !typeMenuOpen"
            >
              <span>{{ currentTypeLabel }}</span>
              <ChevronDown :size="16" :class="{ 'is-open': typeMenuOpen }" />
            </button>
            <div v-if="typeMenuOpen" class="dropdown-menu">
              <button
                v-for="item in questionTypes"
                :key="item.code"
                type="button"
                class="dropdown-item"
                :class="{ active: form.type === item.code }"
                @mousedown.prevent="chooseType(item.code)"
              >
                {{ item.name }}
              </button>
            </div>
          </div>
        </label>

        <label class="form-field field-full">
          <div class="field-label-actions">
            <span>题干</span>
            <div class="field-actions">
              <button class="mini-action" type="button" @click="openAiDialog">
                <Sparkles :size="14" /> AI 生成
              </button>
              <button class="mini-action" type="button" @click="triggerStemImage">
                <ImagePlus :size="14" /> 插图
              </button>
            </div>
          </div>
          <textarea
            v-model="form.stem"
            class="form-input"
            rows="4"
            placeholder="请输入题目内容"
            @paste="onStemPaste"
          ></textarea>
        </label>

        <div v-if="isChoiceQuestion" class="form-field field-full options-field">
          <div class="options-header">
            <span>选项设置</span>
            <button class="button button--small button--ghost" @click="addOption" :disabled="form.options.length >= 8">
              <Plus :size="14" /> 添加选项
            </button>
          </div>
          <div class="options-list">
            <div v-for="(opt, index) in form.options" :key="opt.key" class="option-item">
              <span class="option-key">{{ opt.key }}.</span>
              <input v-model="opt.content" type="text" class="form-input" placeholder="请输入选项内容" />
              <button class="icon-mini" type="button" @click="triggerOptionImage(index)" title="给选项插图">
                <ImagePlus :size="14" />
              </button>
              <button class="delete-btn" type="button" @click="removeOption(index)" :disabled="form.options.length <= 2" title="删除该选项">
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>

        <div v-if="isChoiceQuestion" class="form-field field-full">
          <span>答案选择{{ form.type === 'multiple_choice' ? '（可多选）' : '' }}</span>
          <div class="choice-answer-grid">
            <button
              v-for="opt in form.options"
              :key="`answer-${opt.key}`"
              type="button"
              class="answer-chip"
              :class="{ active: isChoiceSelected(opt.key) }"
              @click="toggleChoiceAnswer(opt.key)"
            >
              {{ opt.key }}
            </button>
          </div>
          <p class="answer-hint">当前答案：{{ form.answerText || '未选择' }}</p>
        </div>

        <div v-else-if="form.type === 'blank'" class="form-field field-full options-field">
          <div class="options-header">
            <span>填空项设置</span>
            <button class="button button--small button--ghost" @click="addBlank" :disabled="form.blankAnswers.length >= 10">
              <Plus :size="14" /> 添加一空
            </button>
          </div>
          <div class="options-list">
            <div v-for="(ans, index) in form.blankAnswers" :key="ans.id" class="option-item">
              <span class="option-key blank-key">空 {{ ans.id }}</span>
              <input v-model="ans.content" type="text" class="form-input" placeholder="请输入该空的答案" />
              <button class="delete-btn" type="button" @click="removeBlank(index)" :disabled="form.blankAnswers.length <= 1" title="删除该空">
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="form.type === 'judge'" class="form-field">
          <span>答案</span>
          <div class="judge-actions">
            <button
              type="button"
              class="judge-btn"
              :class="{ active: form.answerText === 'TRUE' }"
              @click="setJudgeAnswer('TRUE')"
            >正确</button>
            <button
              type="button"
              class="judge-btn"
              :class="{ active: form.answerText === 'FALSE' }"
              @click="setJudgeAnswer('FALSE')"
            >错误</button>
          </div>
        </div>

        <label v-else class="form-field">
          <span>答案</span>
          <input v-model="form.answerText" class="form-input" type="text" placeholder="请输入答案" />
        </label>

        <label class="form-field">
          <span>分值</span>
          <div class="stepper">
            <button type="button" class="step-btn" @click="adjustNumber('score', -1, 1, 100)">-</button>
            <input v-model.number="form.score" class="form-input no-spin" type="number" min="1" step="1" />
            <button type="button" class="step-btn" @click="adjustNumber('score', 1, 1, 100)">+</button>
          </div>
        </label>

        <label class="form-field">
          <span>难度（0-1）</span>
          <div class="stepper">
            <button type="button" class="step-btn" @click="adjustNumber('difficulty', -0.1, 0, 1)">-</button>
            <input v-model.number="form.difficulty" class="form-input no-spin" type="number" min="0" max="1" step="0.01" />
            <button type="button" class="step-btn" @click="adjustNumber('difficulty', 0.1, 0, 1)">+</button>
          </div>
        </label>

        <label class="form-field field-full">
          <div class="field-label-actions">
            <span>解析（可选）</span>
            <button class="mini-action" type="button" @click="triggerAnalysisImage">
              <ImagePlus :size="14" /> 插图
            </button>
          </div>
          <textarea v-model="form.analysis" class="form-input" rows="3" placeholder="输入答案解析"></textarea>
        </label>
        </div>

        <div class="editor-actions sticky-actions">
          <button class="button button--ghost" :disabled="isSaving" @click="closeEditor">取消</button>
          <button class="button" :disabled="isSaving" @click="submitEditor">{{ isSaving ? '保存中...' : '保存题目' }}</button>
        </div>

        <input ref="stemImageInput" class="hidden-file" type="file" accept="image/*" @change="onStemImageChange" />
        <input ref="analysisImageInput" class="hidden-file" type="file" accept="image/*" @change="onAnalysisImageChange" />
        <input ref="optionImageInput" class="hidden-file" type="file" accept="image/*" @change="onOptionImageChange" />
      </div>
    </section>

    <section v-if="isAiDialogOpen" class="ai-dialog-mask" @click.self="closeAiDialog">
      <div class="ai-dialog">
        <div class="ai-dialog-header">
          <h3>AI 智能出题</h3>
          <button class="close-editor-btn" @click="closeAiDialog"><X :size="18" /></button>
        </div>
        <p class="ai-dialog-desc">输入要求后，AI 结果会覆盖到当前编辑表单。</p>
        <textarea
          v-model="aiRequirement"
          class="form-input"
          rows="4"
          placeholder="例如：生成一道初二数学单选题，考察一次函数图像，难度中等，附详细解析"
        ></textarea>
        <div class="editor-actions">
          <button class="button button--ghost" :disabled="isAiGenerating" @click="closeAiDialog">取消</button>
          <button class="button" :disabled="isAiGenerating" @click="generateByAiAndApply">
            {{ isAiGenerating ? '生成中...' : '生成并应用' }}
          </button>
        </div>
      </div>
    </section>

    <div class="search-section">
      <div class="search-bar">
        <Search :size="16" class="search-icon" />
        <input type="text" placeholder="搜索题目内容、知识点..." class="search-input" v-model="keyword" @keyup.enter="fetchQuestions(true)" />
      </div>
      <div class="subject-filter-wrap" @focusout="closeSubjectFilterMenuLater">
        <button
          type="button"
          class="subject-filter-select dropdown-trigger"
          @mousedown.prevent="subjectFilterMenuOpen = !subjectFilterMenuOpen"
        >
          <span>{{ currentSubjectFilterLabel }}</span>
          <ChevronDown :size="16" :class="{ 'is-open': subjectFilterMenuOpen }" />
        </button>
        <div v-if="subjectFilterMenuOpen" class="dropdown-menu subject-filter-menu">
          <button
            v-for="sub in subjectFilterOptions"
            :key="sub"
            type="button"
            class="dropdown-item"
            :class="{ active: activeSubjectFilter === sub }"
            @mousedown.prevent="chooseSubjectFilter(sub)"
          >
            {{ sub === 'all' ? '全部科目' : sub }}
          </button>
        </div>
      </div>
      <button class="icon-button filter-btn" @click="fetchQuestions(true)">
        <Filter :size="18" />
      </button>
    </div>

    <div class="filter-chips">
      <span class="chip" :class="{ active: activeTypeFilter === 'all' }" @click="activeTypeFilter = 'all'">全部</span>
      <span
        v-for="item in questionTypes"
        :key="item.code"
        class="chip"
        :class="{ active: activeTypeFilter === item.code }"
        @click="activeTypeFilter = item.code"
      >
        {{ item.name }}
      </span>
    </div>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <div v-else-if="questions.length === 0" class="empty-state">
      <Database :size="48" class="empty-icon" />
      <p>题库空空如也</p>
      <button class="button button--primary" style="margin-top: 12px;" @click="openCreate">
        <Plus :size="16" style="margin-right: 6px"/> 录入第一道试题
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
            <span v-if="Array.isArray(q.knowledge_points) && q.knowledge_points.length === 0" class="k-tag">暂无知识点</span>
            <span v-for="point in q.knowledge_points || []" :key="point.id" class="k-tag"># {{ point.name }}</span>
          </div>
          <div class="q-actions">
            <button class="button button--small button--ghost" @click="openPreview(q)">
              <Eye :size="14" />
              <span>预览</span>
            </button>
            <button class="button button--small button--ghost" @click="openEdit(q)">
              <Pencil :size="14" />
              <span>编辑</span>
            </button>
            <button class="button button--small button--danger" @click="removeQuestion(q.id)">
              <Trash2 :size="14" />
              <span>删除</span>
            </button>
          </div>
        </div>
      </div>

      <div ref="loadMoreAnchor" class="load-more-zone">
        <span v-if="isLoadingMore">正在加载更多题目...</span>
        <button v-else-if="hasMoreQuestions" class="button button--ghost load-more-btn" @click="loadMoreQuestions">
          加载更多
        </button>
        <span v-else>已经到底了</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-questions {
  --bg: #f6f8fb;
  --line: #dbe4f0;
  --ink: #162033;
  --ink-soft: #66758c;
  --accent: #2563eb;
  --border-hover: #c7d5ea;
  --radius-md: 14px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.button:hover {
  filter: brightness(0.98);
}

.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button--small {
  min-height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

.button--ghost {
  background: #fff;
  border-color: var(--line);
  color: var(--ink);
}

.button--primary {
  background: var(--accent);
  color: #fff;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.editor-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.42);
}

.editor-panel {
  width: min(960px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 20px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--ink);
}

.editor-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--ink-soft);
}

.close-editor-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full, 50%);
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.2s;
  margin-right: -8px; /* Offset to align with the right edge better if needed */
}

.close-editor-btn:hover {
  background: var(--bg);
  color: var(--ink);
}

.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field-label-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-actions {
  display: flex;
  gap: 8px;
}

.mini-action {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.mini-action:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.field-full {
  grid-column: 1 / -1;
}

.subject-input-wrapper {
  width: 100%;
  position: relative;
}
.subject-input-wrapper .form-input {
  width: 100%;
  box-sizing: border-box;
  padding-right: 40px;
}

.subject-combobox {
  position: relative;
}

.subject-toggle {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.subject-toggle:hover {
  background: var(--bg);
  color: var(--ink);
}

.subject-toggle .is-open {
  transform: rotate(180deg);
}

.subject-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 14px 26px rgba(15, 23, 42, 0.12);
  padding: 6px;
}

.subject-menu-item {
  width: 100%;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ink);
  text-align: left;
  font-size: 14px;
  padding: 8px 10px;
  cursor: pointer;
}

.subject-menu-item:hover {
  background: #eff6ff;
  color: var(--accent);
}

.subject-menu-empty {
  margin: 6px;
  font-size: 12px;
  color: var(--ink-soft);
}

.dropdown {
  position: relative;
}

.dropdown-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
}

.dropdown-trigger .is-open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  z-index: 22;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 14px 26px rgba(15, 23, 42, 0.12);
  padding: 6px;
}

.dropdown-item {
  width: 100%;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ink);
  text-align: left;
  font-size: 14px;
  padding: 8px 10px;
  cursor: pointer;
}

.dropdown-item:hover,
.dropdown-item.active {
  background: #eff6ff;
  color: var(--accent);
}

.options-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.options-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.options-header span {
  font-weight: 500;
  color: var(--ink);
  font-size: 13px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-key {
  font-weight: 600;
  color: var(--ink);
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.blank-key {
  width: 38px;
  font-size: 13px;
  text-align: right;
  padding-right: 4px;
}

.option-item .form-input {
  flex: 1;
}

.icon-mini {
  border: 1px solid var(--line);
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #fff;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.icon-mini:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-btn:hover:not(:disabled) {
  border-color: var(--status-danger, #ef4444);
  color: var(--status-danger, #ef4444);
  background: rgba(239, 68, 68, 0.05);
}

.delete-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: var(--bg);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field span {
  font-size: 12px;
  color: var(--ink-soft);
}

.field-full {
  grid-column: 1 / -1;
}

.form-input {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
  color: var(--ink);
  background: #fff;
}

.form-input:focus {
  border-color: var(--accent);
}

.stepper {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #fff;
  height: 40px; /* matches typical form-input height */
}

.stepper .form-input {
  border: none;
  border-radius: 0;
  text-align: center;
  flex: 1;
  width: 0;
  padding: 0;
}

.stepper .form-input:focus {
  border-color: transparent;
  outline: none;
}

.step-btn {
  background: var(--bg);
  border: none;
  border-left: 1px solid var(--line);
  border-right: 1px solid var(--line);
  color: var(--ink);
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.2s;
}

.step-btn:first-child {
  border-left: none;
  border-right: 1px solid var(--line);
}

.step-btn:last-child {
  border-right: none;
  border-left: 1px solid var(--line);
}

.step-btn:hover {
  background: var(--line);
}

.step-btn:active {
  background: var(--border-hover);
}

.no-spin::-webkit-inner-spin-button,
.no-spin::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.no-spin {
  appearance: textfield;
  -moz-appearance: textfield;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.choice-answer-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.answer-chip {
  width: 40px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink-soft);
  cursor: pointer;
  font-weight: 600;
}

.answer-chip.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(37, 99, 235, 0.08);
}

.answer-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
}

.judge-actions {
  display: flex;
  gap: 8px;
}

.judge-btn {
  flex: 1;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  border-radius: 8px;
  height: 38px;
  cursor: pointer;
}

.judge-btn.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(37, 99, 235, 0.08);
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-stat {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
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

.ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(20, 184, 166, 0.42);
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.1), rgba(20, 184, 166, 0.24));
  color: #0f766e;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(15, 118, 110, 0.16);
}

.ai-btn:hover {
  border-color: rgba(15, 118, 110, 0.6);
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.16), rgba(20, 184, 166, 0.3));
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.16);
}

.ai-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(15, 118, 110, 0.2);
}

.ai-btn:focus-visible {
  outline: 2px solid rgba(15, 118, 110, 0.35);
  outline-offset: 1px;
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

.subject-filter-select {
  min-width: 132px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--ink);
  padding: 0 12px;
  font-size: 14px;
  min-height: 42px;
}

.subject-filter-wrap {
  position: relative;
  min-width: 132px;
}

.subject-filter-wrap .subject-filter-select {
  width: 100%;
}

.subject-filter-menu {
  z-index: 18;
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

.load-more-zone {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 72px;
  color: var(--ink-soft);
  font-size: 13px;
}

.load-more-btn {
  min-width: 132px;
}

.sticky-actions {
  position: sticky;
  bottom: 0;
  padding-top: 10px;
  background: linear-gradient(180deg, rgba(255,255,255,0.5), #fff 36%);
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

.q-actions {
  display: flex;
  gap: 8px;
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

.button--danger {
  background: #fff1f2;
  color: #b91c1c;
  border: 1px solid #fecdd3;
}

.button--danger:hover {
  background: #ffe4e6;
}

.hidden-file {
  display: none;
}

.ai-dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.ai-dialog {
  width: min(560px, 100%);
  background: #fff;
  border-radius: 14px;
  border: 1px solid var(--line);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-dialog-header h3 {
  margin: 0;
  color: var(--ink);
}

.ai-dialog-desc {
  margin: 0;
  font-size: 13px;
  color: var(--ink-soft);
}

@media (max-width: 768px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .editor-mask {
    padding: 8px;
    align-items: stretch;
  }

  .editor-panel {
    width: 100%;
    max-height: 100vh;
    border-radius: 16px;
  }

  .search-section {
    flex-wrap: wrap;
  }

  .subject-filter-select {
    flex: 1 1 140px;
    min-height: 42px;
  }

  .q-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>


