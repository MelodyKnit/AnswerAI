<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Database, Filter, ImagePlus, Pencil, Plus, Search, Sparkles, Trash2, X } from 'lucide-vue-next'
import { createQuestion, deleteQuestion, generateQuestionsByAi, getQuestions, updateQuestion } from '@/api/teacher'
import { getQuestionTypes, getSubjects } from '@/api/meta'
import http from '@/lib/http'

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
const subjects = ref<Array<{ id: number, name: string }>>([])
const questionTypes = ref<Array<{ code: string, name: string }>>([])

const isLoading = ref(true)
const isSaving = ref(false)
const keyword = ref('')
const activeTypeFilter = ref('all')
const isEditorOpen = ref(false)
const editingQuestionId = ref<number | null>(null)

const isAiDialogOpen = ref(false)
const isAiGenerating = ref(false)
const aiRequirement = ref('')

const stemImageInput = ref<HTMLInputElement | null>(null)
const analysisImageInput = ref<HTMLInputElement | null>(null)
const optionImageInput = ref<HTMLInputElement | null>(null)
const currentOptionImageIndex = ref<number | null>(null)

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

const isChoiceQuestion = computed(() => ['single_choice', 'multiple_choice'].includes(form.value.type))

const uniqueSubjects = computed(() => {
  const subjectSet = new Set<string>()
  subjects.value.forEach((s) => subjectSet.add(s.name))
  questions.value.forEach((q) => {
    if (q.subject) {
      subjectSet.add(q.subject)
    }
  })
  return Array.from(subjectSet)
})

const fetchMeta = async () => {
  try {
    const [subjectRes, typeRes] = await Promise.all([getSubjects(), getQuestionTypes()])
    subjects.value = (subjectRes as any).items || []
    questionTypes.value = (typeRes as any).items || []
    if (!form.value.subject && uniqueSubjects.value.length > 0) {
      form.value.subject = uniqueSubjects.value[0]
    }
  } catch (error) {
    console.error('Failed to fetch question metadata', error)
  }
}

const fetchQuestions = async () => {
  try {
    isLoading.value = true
    const res = await getQuestions({
      keyword: keyword.value || undefined,
      type: activeTypeFilter.value !== 'all' ? activeTypeFilter.value : undefined,
    })
    questions.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to fetch questions', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await fetchMeta()
  await fetchQuestions()
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
  if (!form.value.subject || !form.value.type || !form.value.stem.trim()) {
    alert('请完善科目、题型和题干')
    return
  }

  if (form.value.type === 'blank') {
    const hasEmptyBlank = form.value.blankAnswers.some((item) => !item.content.trim())
    if (hasEmptyBlank || form.value.blankAnswers.length === 0) {
      alert('请填写所有填空答案')
      return
    }
  } else if (!form.value.answerText.trim()) {
    alert('请先选择或填写答案')
    return
  }

  const options = isChoiceQuestion.value
    ? form.value.options
      .map((opt) => ({ key: opt.key, content: opt.content.trim() }))
      .filter((opt) => opt.content)
    : []

  if (isChoiceQuestion.value && options.length < 2) {
    alert('选择题至少需要两个有效选项')
    return
  }

  const payload = {
    subject: form.value.subject,
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
    if (editingQuestionId.value) {
      await updateQuestion({ question_id: editingQuestionId.value, ...payload })
    } else {
      await createQuestion(payload)
    }
    closeEditor()
    await fetchQuestions()
  } catch (error) {
    console.error('Failed to save question', error)
    alert('保存题目失败，请稍后重试')
  } finally {
    isSaving.value = false
  }
}

const removeQuestion = async (questionId: number) => {
  if (!window.confirm('确认删除该题目？删除后无法恢复。')) {
    return
  }
  try {
    await deleteQuestion(questionId)
    await fetchQuestions()
  } catch (error) {
    console.error('Failed to delete question', error)
    alert('删除题目失败，请稍后重试')
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
    alert('图片上传失败，请稍后重试')
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
    alert('请先选择科目和题型')
    return
  }
  if (!aiRequirement.value.trim()) {
    alert('请输入 AI 出题要求')
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
      alert('AI 未生成题目，请调整要求后重试')
      return
    }
    applyGeneratedQuestion(generatedList[0])
    closeAiDialog()
  } catch (error) {
    console.error('AI generate failed', error)
    alert('AI 出题失败，请稍后重试')
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
    </header>

    <section v-if="isEditorOpen" class="editor-panel">
      <div class="editor-header">
        <h2>{{ editingQuestionId ? '编辑题目' : '新增题目' }}</h2>
        <button class="close-editor-btn" @click="closeEditor" aria-label="关闭编辑器">
          <X :size="18" />
        </button>
      </div>

      <div class="editor-grid">
        <label class="form-field">
          <span>科目</span>
          <div class="subject-input-wrapper">
            <input 
              v-model="form.subject" 
              class="form-input" 
              list="subject-list" 
              placeholder="请选择或输入科目" 
            />
            <datalist id="subject-list">
              <option v-for="sub in uniqueSubjects" :key="sub" :value="sub"></option>
            </datalist>
          </div>
        </label>

        <label class="form-field">
          <span>题型</span>
          <select v-model="form.type" class="form-input">
            <option v-for="item in questionTypes" :key="item.code" :value="item.code">{{ item.name }}</option>
          </select>
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

      <div class="editor-actions">
        <button class="button button--ghost" :disabled="isSaving" @click="closeEditor">取消</button>
        <button class="button" :disabled="isSaving" @click="submitEditor">{{ isSaving ? '保存中...' : '保存题目' }}</button>
      </div>

      <input ref="stemImageInput" class="hidden-file" type="file" accept="image/*" @change="onStemImageChange" />
      <input ref="analysisImageInput" class="hidden-file" type="file" accept="image/*" @change="onAnalysisImageChange" />
      <input ref="optionImageInput" class="hidden-file" type="file" accept="image/*" @change="onOptionImageChange" />
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
        <input type="text" placeholder="搜索题目内容、知识点..." class="search-input" v-model="keyword" @keyup.enter="fetchQuestions" />
      </div>
      <button class="icon-button filter-btn" @click="fetchQuestions">
        <Filter :size="18" />
      </button>
    </div>

    <div class="filter-chips">
      <span class="chip" :class="{ active: activeTypeFilter === 'all' }" @click="activeTypeFilter = 'all'; fetchQuestions()">全部</span>
      <span
        v-for="item in questionTypes"
        :key="item.code"
        class="chip"
        :class="{ active: activeTypeFilter === item.code }"
        @click="activeTypeFilter = item.code; fetchQuestions()"
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
            <span v-for="k in (q.knowledge_points || [])" :key="k.id" class="k-tag">#{{ k.name }}</span>
          </div>
          <div class="q-actions">
            <button class="button button--ghost button--small" @click="openEdit(q)">
              <Pencil :size="14" />
              编辑
            </button>
            <button class="button button--danger button--small" @click="removeQuestion(q.id)">
              <Trash2 :size="14" />
              删除
            </button>
          </div>
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

.editor-panel {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-header h2 {
  margin: 0;
  font-size: 16px;
  color: var(--ink);
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
}
.subject-input-wrapper .form-input {
  width: 100%;
  box-sizing: border-box;
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

  .q-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>


