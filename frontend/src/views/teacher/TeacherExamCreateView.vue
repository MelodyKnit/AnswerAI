<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Play, Sparkles, Save } from 'lucide-vue-next'
import { assembleExamByAi, createExam, getClasses, getExams, getQuestionSubjects, getQuestions } from '@/api/teacher'

const router = useRouter()
const ALL_SUBJECT_VALUE = '__all__'
const EXAM_CREATE_META_CACHE_KEY = 'teacher_exam_create_meta_v1'

const roundToNextQuarter = (date = new Date()) => {
  const next = new Date(date)
  next.setSeconds(0, 0)
  const minutes = next.getMinutes()
  next.setMinutes(minutes + (15 - (minutes % 15 || 15)) % 15)
  return next
}

const formatDateTimeLocal = (date: Date) => {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  const hours = `${date.getHours()}`.padStart(2, '0')
  const minutes = `${date.getMinutes()}`.padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

const toIsoFromLocal = (value: string) => {
  const dt = new Date(value)
  return dt.toISOString()
}

const defaultStart = roundToNextQuarter(new Date())
const defaultEnd = new Date(defaultStart.getTime() + 24 * 60 * 60 * 1000)

const form = ref({
  title: '',
  instructions: '',
  subject: ALL_SUBJECT_VALUE,
  duration_minutes: 60,
  total_score: 100,
  start_time: formatDateTimeLocal(defaultStart),
  end_time: formatDateTimeLocal(defaultEnd),
  selected_class_ids: [] as number[],
})

const subjects = ref<string[]>([])
const classes = ref<Array<{ id: number, name: string, subject?: string }>>([])
const questionBank = ref<any[]>([])
const examQuestions = ref<Array<{ question_id: number, stem: string, type: string, score: number, difficulty: number }>>([])
const questionBankSubject = ref<string | null>(null)

const isQuestionSelectorOpen = ref(false)
const isAiAssembleOpen = ref(false)
const isQuestionsLoading = ref(false)
const isAiAssembling = ref(false)

const questionKeyword = ref('')
const questionTypeFilter = ref('all')
const tempSelectedQuestionIds = ref<number[]>([])

const aiRequirement = ref('')

const isSubmitting = ref(false)
const submitMode = ref<'draft' | 'publish' | null>(null)

const questionTypeOptions = [
  { value: 'all', label: '全部题型' },
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'judge', label: '判断题' },
  { value: 'blank', label: '填空题' },
  { value: 'essay', label: '简答题' },
]

const totalScore = computed(() => {
  return examQuestions.value.reduce((sum, item) => sum + Number(item.score || 0), 0)
})

const questionTypeWeightMap: Record<string, number> = {
  judge: 0.9,
  single_choice: 1,
  blank: 1.1,
  multiple_choice: 1.25,
  essay: 1.65,
  material: 1.85,
}

const filteredClasses = computed(() => {
  const activeSubject = getActiveSubject()
  if (!activeSubject) return classes.value
  const matched = classes.value.filter((item) => !item.subject || item.subject === activeSubject)
  return matched.length ? matched : classes.value
})

const selectedClassCount = computed(() => form.value.selected_class_ids.length)

const timeRangeText = computed(() => {
  if (!form.value.start_time || !form.value.end_time) return '请设置考试开放时间范围'
  const start = new Date(form.value.start_time)
  const end = new Date(form.value.end_time)
  const diffMinutes = Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000))
  if (diffMinutes < 60) return `考试开放 ${diffMinutes} 分钟`
  if (diffMinutes < 24 * 60) return `考试开放 ${Math.round(diffMinutes / 60)} 小时`
  return `考试开放 ${Math.round((diffMinutes / 60 / 24) * 10) / 10} 天`
})

const isTimeRangeValid = computed(() => {
  if (!form.value.start_time || !form.value.end_time) return false
  return new Date(form.value.end_time).getTime() > new Date(form.value.start_time).getTime()
})

const redistributeQuestionScores = () => {
  const items = examQuestions.value
  const targetTotal = Math.max(0, Math.round(Number(form.value.total_score || 0)))
  if (!items.length || targetTotal <= 0) {
    examQuestions.value = items.map((item) => ({ ...item, score: 0 }))
    return
  }

  const count = items.length
  const safeTarget = Math.max(targetTotal, count)
  const weights = items.map((item) => {
    const typeWeight = questionTypeWeightMap[item.type] ?? 1.1
    const difficulty = Math.max(0, Math.min(1, Number(item.difficulty || 0.5)))
    return Math.max(0.8, typeWeight * (1 + difficulty * 0.45))
  })
  const totalWeight = weights.reduce((sum, current) => sum + current, 0)
  const baseScores = new Array(count).fill(1)
  let remain = safeTarget - count
  const rawExtras = weights.map((weight) => (remain > 0 ? (weight / totalWeight) * remain : 0))
  const floors = rawExtras.map((value) => Math.floor(value))
  remain -= floors.reduce((sum, value) => sum + value, 0)

  const rankedRemainders = rawExtras
    .map((value, index) => ({ index, fraction: value - floors[index] }))
    .sort((left, right) => right.fraction - left.fraction)

  const finalScores = baseScores.map((base, index) => base + floors[index])
  for (let index = 0; index < remain; index += 1) {
    const current = rankedRemainders[index % rankedRemainders.length]
    finalScores[current.index] += 1
  }

  examQuestions.value = items.map((item, index) => ({
    ...item,
    score: finalScores[index],
  }))
}

const getActiveSubject = () => {
  return form.value.subject && form.value.subject !== ALL_SUBJECT_VALUE ? form.value.subject : undefined
}

const syncSubjectSelection = (nextSubjects: string[]) => {
  if (nextSubjects.length > 0) {
    if (!nextSubjects.includes(form.value.subject)) {
      form.value.subject = nextSubjects[0]
    }
    return
  }

  form.value.subject = ALL_SUBJECT_VALUE
}

const getSubjectsFromClasses = (items: Array<{ subject?: string }>) => {
  return Array.from(new Set(items.map((item) => item.subject).filter((item): item is string => Boolean(item))))
}

const hydrateMetaCache = () => {
  try {
    const raw = localStorage.getItem(EXAM_CREATE_META_CACHE_KEY)
    if (!raw) {
      return
    }

    const parsed = JSON.parse(raw) as {
      subjects?: string[]
      classes?: Array<{ id: number, name: string, subject?: string }>
    }
    const cachedClasses = Array.isArray(parsed.classes) ? parsed.classes : []
    const cachedSubjects = Array.isArray(parsed.subjects) ? parsed.subjects : getSubjectsFromClasses(cachedClasses)

    if (cachedClasses.length > 0) {
      classes.value = cachedClasses
    }
    if (cachedSubjects.length > 0) {
      subjects.value = cachedSubjects
      syncSubjectSelection(cachedSubjects)
    }
  } catch (error) {
    console.warn('Failed to read exam creation metadata cache', error)
  }
}

const persistMetaCache = () => {
  try {
    localStorage.setItem(EXAM_CREATE_META_CACHE_KEY, JSON.stringify({
      subjects: subjects.value,
      classes: classes.value,
    }))
  } catch (error) {
    console.warn('Failed to cache exam creation metadata', error)
  }
}

const filteredQuestionBank = computed(() => {
  const keyword = questionKeyword.value.trim().toLowerCase()
  return questionBank.value.filter((q) => {
    const keywordMatch = !keyword || String(q.stem || '').toLowerCase().includes(keyword)
    const typeMatch = questionTypeFilter.value === 'all' || q.type === questionTypeFilter.value
    const subjectMatch = form.value.subject === ALL_SUBJECT_VALUE || q.subject === form.value.subject
    return keywordMatch && typeMatch && subjectMatch
  })
})

const goBack = () => {
  router.back()
}

const handleCreate = async (mode: 'draft' | 'publish' = 'draft') => {
  if (isSubmitting.value) {
    return
  }

  const title = form.value.title.trim()
  if (!title) {
    alert('请先填写考试名称')
    return
  }
  if (!form.value.subject || form.value.subject === ALL_SUBJECT_VALUE) {
    alert('请先选择科目')
    return
  }
  if (Number(form.value.duration_minutes) <= 0) {
    alert('考试时长必须大于 0 分钟')
    return
  }

  if (!isTimeRangeValid.value) {
    alert('请设置正确的考试开放时间范围')
    return
  }

  if (mode === 'publish' && form.value.selected_class_ids.length === 0) {
    alert('创建并发布时至少要关联一个班级')
    return
  }

  if (mode === 'publish' && examQuestions.value.length === 0) {
    alert('创建并发布前请至少添加一道试题')
    return
  }

  submitMode.value = mode
  isSubmitting.value = true

  try {
    const existed = await getExams({ keyword: title, page: 1, page_size: 100 })
    const hasDuplicate = ((existed as any)?.items || []).some((item: any) => String(item?.title || '').trim() === title)
    if (hasDuplicate) {
      alert(`您已创建过同名考试「${title}」，请使用不同名称`)
      isSubmitting.value = false
      submitMode.value = null
      return
    }
  } catch (error) {
    console.error('Failed to precheck duplicate exam title', error)
  }

  try {
    const payload = {
      title,
      subject: form.value.subject,
      duration_minutes: Number(form.value.duration_minutes || 60),
      start_time: toIsoFromLocal(form.value.start_time),
      end_time: toIsoFromLocal(form.value.end_time),
      instructions: form.value.instructions || null,
      publish_now: mode === 'publish',
      allow_review: true,
      random_question_order: false,
      class_ids: form.value.selected_class_ids,
      question_items: examQuestions.value.map((item, index) => ({
        question_id: item.question_id,
        score: Number(item.score || 0),
        order_no: index + 1,
        section_name: null,
      })),
    }

    const res = await createExam(payload)
    const examId = (res as any).exam?.id
    if (examId) {
      alert(mode === 'publish' ? '考试已创建并发布' : '考试草稿已保存')
      router.replace(`/app/teacher/exams/${examId}`)
    } else {
      alert('创建成功，但未拿到考试ID，请刷新后查看考试列表')
    }
  } catch (error) {
    console.error('Failed to create exam', error)
    const err = error as any
    const detail = err?.response?.data?.detail
    const message = typeof detail === 'string' ? detail : (err?.message || '创建失败，请稍后重试')
    alert(message)
  } finally {
    isSubmitting.value = false
    submitMode.value = null
  }
}

const fetchMeta = async () => {
  hydrateMetaCache()

  const [subjectRes, classRes] = await Promise.allSettled([
    getQuestionSubjects(),
    getClasses({ page_size: 100 }),
  ])

  if (subjectRes.status === 'fulfilled') {
    subjects.value = (((subjectRes.value as any)?.items || []) as string[]).filter(Boolean)
  } else {
    console.warn('Failed to load question subjects for exam creation', subjectRes.reason)
  }

  if (classRes.status === 'fulfilled') {
    classes.value = ((classRes.value as any)?.items || []) as Array<{ id: number, name: string, subject?: string }>
  } else {
    console.warn('Failed to load classes for exam creation', classRes.reason)
  }

  if (subjects.value.length === 0 && classes.value.length > 0) {
    subjects.value = getSubjectsFromClasses(classes.value)
  }

  syncSubjectSelection(subjects.value)

  if (subjects.value.length > 0 || classes.value.length > 0) {
    persistMetaCache()
  }

  if (subjectRes.status === 'rejected' && classRes.status === 'rejected' && subjects.value.length === 0 && classes.value.length === 0) {
    console.error('Failed to load metadata for exam creation')
  }
}

onMounted(() => {
  fetchMeta()
})

const fetchQuestionBank = async () => {
  const activeSubject = getActiveSubject() || null
  if (questionBank.value.length > 0 && questionBankSubject.value === activeSubject) {
    return
  }

  try {
    isQuestionsLoading.value = true
    const res = await getQuestions({
      page: 1,
      page_size: 100,
      subject: activeSubject || undefined,
    })
    questionBank.value = (res as any).items || []
    questionBankSubject.value = activeSubject
  } catch (error) {
    console.error('Failed to load question bank', error)
  } finally {
    isQuestionsLoading.value = false
  }
}

const openQuestionSelector = () => {
  tempSelectedQuestionIds.value = examQuestions.value.map((item) => item.question_id)
  isQuestionSelectorOpen.value = true
  void fetchQuestionBank()
}

const closeQuestionSelector = () => {
  isQuestionSelectorOpen.value = false
}

const toggleTempSelection = (questionId: number) => {
  if (tempSelectedQuestionIds.value.includes(questionId)) {
    tempSelectedQuestionIds.value = tempSelectedQuestionIds.value.filter((id) => id !== questionId)
    return
  }
  tempSelectedQuestionIds.value = [...tempSelectedQuestionIds.value, questionId]
}

const appendQuestionsToExam = (questions: any[]) => {
  const existing = new Set(examQuestions.value.map((item) => item.question_id))
  const next = [...examQuestions.value]
  questions.forEach((q) => {
    if (existing.has(q.id)) {
      return
    }
    next.push({
      question_id: q.id,
      stem: q.stem || '',
      type: q.type || '',
      score: 0,
      difficulty: Number(q.difficulty || 0.5),
    })
  })
  examQuestions.value = next
  redistributeQuestionScores()
}

const confirmQuestionSelection = () => {
  const picked = questionBank.value.filter((q) => tempSelectedQuestionIds.value.includes(q.id))
  const preserved = examQuestions.value.filter((item) => tempSelectedQuestionIds.value.includes(item.question_id))
  const preservedIds = new Set(preserved.map((item) => item.question_id))

  const appended = picked
    .filter((q) => !preservedIds.has(q.id))
    .map((q) => ({
      question_id: q.id,
      stem: q.stem || '',
      type: q.type || '',
      score: 0,
      difficulty: Number(q.difficulty || 0.5),
    }))

  examQuestions.value = [...preserved, ...appended]
  redistributeQuestionScores()
  closeQuestionSelector()
}

const removeExamQuestion = (questionId: number) => {
  examQuestions.value = examQuestions.value.filter((item) => item.question_id !== questionId)
  redistributeQuestionScores()
}

const openAiAssemble = () => {
  isAiAssembleOpen.value = true
}

const closeAiAssemble = () => {
  isAiAssembleOpen.value = false
}

const runAiAssemble = async () => {
  const requirement = aiRequirement.value.trim()
  if (!form.value.subject || form.value.subject === ALL_SUBJECT_VALUE) {
    alert('请先选择具体科目，再使用 AI 智能组卷')
    return
  }
  if (!requirement) {
    alert('请先描述想要的试卷结构')
    return
  }

  try {
    isAiAssembling.value = true
    const res = await assembleExamByAi({
      subject: form.value.subject,
      requirement,
      exclude_question_ids: examQuestions.value.map((item) => item.question_id),
    })

    const picked = (res as any)?.questions || []
    if (!picked.length) {
      const unmet = (res as any)?.unmet_requirements || []
      if (unmet.length) {
        alert('题库中没有足够匹配的题目，请调整描述后重试')
        return
      }
      alert('未找到符合条件的题目，请换一种更明确的描述')
      return
    }
    appendQuestionsToExam(picked)
    if (!questionBank.value.length) {
      questionBank.value = picked
    } else {
      const existingIds = new Set(questionBank.value.map((item) => item.id))
      questionBank.value = [...questionBank.value, ...picked.filter((item: any) => !existingIds.has(item.id))]
    }
    alert((res as any)?.summary || `已加入 ${picked.length} 道题目`)
    closeAiAssemble()
  } catch (error) {
    console.error('AI assemble failed', error)
    const err = error as any
    alert(err?.message || '智能组卷失败，请稍后重试')
  } finally {
    isAiAssembling.value = false
  }
}

watch(
  () => form.value.subject,
  () => {
    questionBank.value = []
    questionBankSubject.value = null
    form.value.selected_class_ids = form.value.selected_class_ids.filter((classId) => classes.value.some((item) => item.id === classId))
  }
)

watch(
  () => form.value.total_score,
  () => {
    redistributeQuestionScores()
  }
)

const getTypeLabel = (type: string) => {
  const hit = questionTypeOptions.find((item) => item.value === type)
  return hit?.label || type
}
</script>

<template>
  <div class="view-exam-create">
    <header class="page-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="24" />
      </button>
      <h1 class="page-title">创建考试</h1>
      <button class="icon-button" aria-label="AI助手">
        <Sparkles :size="20" class="ai-icon" />
      </button>
    </header>

    <div class="form-container">
      <div class="form-group">
        <label>考试名称</label>
        <input v-model="form.title" type="text" placeholder="例如：八年级物理期中测试" class="form-input" />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>科目</label>
          <select v-model="form.subject" class="form-input">
            <option :value="ALL_SUBJECT_VALUE">全部科目</option>
            <option v-for="subject in subjects" :key="subject" :value="subject">{{ subject }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>总分上限</label>
          <input v-model.number="form.total_score" type="number" min="1" class="form-input" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>考试时长 (分钟)</label>
          <input v-model="form.duration_minutes" type="number" min="1" class="form-input" />
        </div>
        <div class="form-group">
          <label>当前总分</label>
          <input type="text" class="form-input" :value="`${totalScore}（按题目自动估算）`" readonly />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>开始时间</label>
          <input v-model="form.start_time" type="datetime-local" class="form-input" />
        </div>
        <div class="form-group">
          <label>截止时间</label>
          <input v-model="form.end_time" type="datetime-local" class="form-input" />
        </div>
      </div>

      <div class="range-hint-box" :class="{ 'range-hint-box--invalid': !isTimeRangeValid }">
        <span>{{ timeRangeText }}</span>
        <strong>系统会在该时间范围内开放本场考试，单次作答时长为 {{ form.duration_minutes }} 分钟。</strong>
      </div>

      <div class="form-group">
        <label>关联班级（可多选，可先不选）</label>
        <div class="class-pick-box">
          <div v-if="filteredClasses.length" class="class-pick-grid">
            <label v-for="cls in filteredClasses" :key="cls.id" class="class-pick-item">
              <input type="checkbox" :value="cls.id" v-model="form.selected_class_ids" />
              <div>
                <strong>{{ cls.name }}</strong>
                <small v-if="cls.subject">{{ cls.subject }}</small>
              </div>
            </label>
          </div>
          <p v-else class="class-pick-empty">当前还没有可管理班级。你仍然可以先创建考试草稿，之后在考试详情页手动关联班级再发布。</p>
          <p class="class-pick-hint">当前已选择 {{ selectedClassCount }} 个班级。若暂未绑定，系统仍允许保存草稿，但不会允许直接发布。</p>
        </div>
      </div>

      <div class="form-group">
        <label>考试说明/描述</label>
        <textarea v-model="form.instructions" rows="3" placeholder="考生注意事项等..." class="form-input"></textarea>
      </div>

      <!-- Dummy placeholder for adding questions -->
      <div class="form-group">
        <label>试题组成</label>
        <div class="add-questions">
          <div class="score-summary-bar">
            <div>
              <span>目标总分</span>
              <strong>{{ Math.round(Number(form.total_score || 0)) }} 分</strong>
            </div>
            <div>
              <span>当前合计</span>
              <strong>{{ totalScore }} 分</strong>
            </div>
            <button type="button" class="button button--ghost button--small" @click="redistributeQuestionScores" :disabled="examQuestions.length === 0">
              按算法重新估分
            </button>
          </div>
          <template v-if="examQuestions.length === 0">
            <p>尚未添加任何试题</p>
          </template>
          <template v-else>
            <div class="selected-questions">
              <div v-for="(item, index) in examQuestions" :key="item.question_id" class="selected-question-item">
                <div class="question-main">
                  <span class="q-index">{{ index + 1 }}.</span>
                  <div class="q-content-wrap">
                    <p class="q-stem">{{ item.stem || '题干为空' }}</p>
                    <div class="q-meta-line">
                      <span>{{ getTypeLabel(item.type) }}</span>
                      <span>难度 {{ item.difficulty }}</span>
                        <span>算法估分 {{ item.score }}</span>
                    </div>
                  </div>
                </div>
                <div class="question-side">
                  <input v-model.number="item.score" type="number" class="score-input" min="1" max="100" />
                  <button type="button" class="remove-link" @click="removeExamQuestion(item.question_id)">移除</button>
                </div>
              </div>
            </div>
          </template>
          <div class="actions">
            <button type="button" class="button button--ghost button--small" @click="openQuestionSelector">从题库选择</button>
            <button type="button" class="button button--ghost button--small" @click="openAiAssemble">
              <Sparkles :size="14" /> AI 智能组卷
            </button>
          </div>
        </div>
      </div>
    </div>

    <section v-if="isQuestionSelectorOpen" class="dialog-mask" @click.self="closeQuestionSelector">
      <div class="dialog-card question-dialog">
        <div class="dialog-header">
          <h3>从题库选择</h3>
          <button class="icon-button" @click="closeQuestionSelector" aria-label="关闭">
            <ArrowLeft :size="18" />
          </button>
        </div>
        <div class="dialog-filters">
          <input v-model="questionKeyword" class="form-input" type="text" placeholder="搜索题干关键词" />
          <select v-model="questionTypeFilter" class="form-input">
            <option v-for="option in questionTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div class="dialog-list">
          <p v-if="isQuestionsLoading" class="dialog-empty">加载题库中...</p>
          <p v-else-if="filteredQuestionBank.length === 0" class="dialog-empty">暂无匹配题目</p>
          <label v-for="q in filteredQuestionBank" :key="q.id" class="pick-item">
            <input
              type="checkbox"
              :checked="tempSelectedQuestionIds.includes(q.id)"
              @change="toggleTempSelection(q.id)"
            />
            <div class="pick-main">
              <p class="pick-stem">{{ q.stem }}</p>
              <div class="pick-meta">
                <span>{{ getTypeLabel(q.type) }}</span>
                <span>分值 {{ q.score }}</span>
                <span>难度 {{ q.difficulty }}</span>
              </div>
            </div>
          </label>
        </div>
        <div class="dialog-actions">
          <button class="button button--ghost" @click="closeQuestionSelector">取消</button>
          <button class="button" @click="confirmQuestionSelection">确定加入（{{ tempSelectedQuestionIds.length }}）</button>
        </div>
      </div>
    </section>

    <section v-if="isAiAssembleOpen" class="dialog-mask" @click.self="closeAiAssemble">
      <div class="dialog-card">
        <div class="dialog-header">
          <h3>AI 智能组卷</h3>
          <button class="icon-button" @click="closeAiAssemble" aria-label="关闭">
            <ArrowLeft :size="18" />
          </button>
        </div>
        <div class="dialog-grid ai-dialog-grid">
          <label class="form-group dialog-full">
            <span>直接描述你想出的卷子</span>
            <textarea
              v-model="aiRequirement"
              class="form-input ai-requirement-input"
              rows="5"
              placeholder="例如：我想出一份工程制图试卷，10道选择题加10道判断题，优先考察三视图、剖视图、尺寸标注。"
            ></textarea>
          </label>
          <div class="ai-hint-box dialog-full">
            <span>你可以这样说：</span>
            <p>10道工程制图选择题，加10道判断题，重点考三视图和剖视图。</p>
            <p>我要一份函数基础卷，8道单选题，4道填空题，关键词是一次函数、图像。</p>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="button button--ghost" :disabled="isAiAssembling" @click="closeAiAssemble">取消</button>
          <button class="button" :disabled="isAiAssembling" @click="runAiAssemble">
            {{ isAiAssembling ? '组卷中...' : '生成并加入试卷' }}
          </button>
        </div>
      </div>
    </section>

    <footer class="bottom-action">
      <button
        class="button button--ghost"
        :disabled="isSubmitting"
        @click="handleCreate('draft')"
      >
        <Save :size="18" />
        {{ isSubmitting && submitMode === 'draft' ? '保存中...' : '保存为草稿' }}
      </button>
      <button
        class="button button--primary"
        :disabled="isSubmitting"
        @click="handleCreate('publish')"
        :title="selectedClassCount === 0 ? '请先至少关联一个班级，或先保存草稿后在详情页绑定班级再发布' : ''"
      >
        <Play :size="18" />
        {{ isSubmitting && submitMode === 'publish' ? '发布中...' : '创建并发布' }}
      </button>
    </footer>
  </div>
</template>

<style scoped>
.view-exam-create {
  display: flex;
  flex-direction: column;
  padding-bottom: 80px; /* space for bottom bar */
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.icon-button {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  margin: -8px;
}

.ai-icon {
  color: #8b5cf6; /* purple for AI */
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-row > .form-group {
  flex: 1;
  min-width: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-soft);
}

.range-hint-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #dbe5f0;
  background: #f8fbff;
}

.range-hint-box span {
  font-size: 12px;
  color: #1d4ed8;
  font-weight: 700;
}

.range-hint-box strong {
  font-size: 12px;
  line-height: 1.6;
  color: #516274;
}

.range-hint-box--invalid {
  border-color: #fecaca;
  background: #fff7f7;
}

.range-hint-box--invalid span {
  color: #b91c1c;
}

.class-pick-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 14px;
  padding: 14px;
}

.class-pick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.class-pick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #dce5ef;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fbfdff;
}

.class-pick-item strong {
  display: block;
  font-size: 13px;
  color: var(--ink);
}

.class-pick-item small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ink-soft);
}

.class-pick-hint,
.class-pick-empty {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-soft);
}

.score-summary-bar {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 10px;
  align-items: center;
  border: 1px solid #dce7f4;
  border-radius: 12px;
  background: #f8fbff;
  padding: 10px 12px;
}

.score-summary-bar span {
  display: block;
  font-size: 11px;
  color: var(--ink-soft);
}

.score-summary-bar strong {
  font-size: 18px;
  color: var(--ink);
}

.form-input {
  padding: 12px 16px;
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
  font-size: 15px;
  color: var(--ink);
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: var(--accent);
}

.add-questions {
  border: 1px dashed var(--line);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  background: #fafafa;
}

.add-questions p {
  font-size: 14px;
  color: var(--ink-soft);
}

.selected-questions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selected-question-item {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.question-main {
  display: flex;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.q-index {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.5;
}

.q-content-wrap {
  min-width: 0;
}

.q-stem {
  margin: 0;
  font-size: 13px;
  color: var(--ink);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.q-meta-line {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-soft);
}

.question-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.score-input {
  width: 72px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
}

.remove-link {
  border: none;
  background: none;
  font-size: 12px;
  color: #c2410c;
  cursor: pointer;
}

.add-questions .actions {
  display: flex;
  gap: 12px;
}

.bottom-action {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  background: #fff;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: stretch;
}

.bottom-action .button {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
  z-index: 1000;
}

.dialog-card {
  width: min(620px, 100%);
  max-height: 86vh;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
}

.question-dialog {
  width: min(760px, 100%);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
}

.dialog-header h3 {
  margin: 0;
  font-size: 16px;
}

.dialog-filters {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
}

.dialog-list {
  padding: 10px 14px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 52vh;
}

.dialog-empty {
  margin: 12px 0;
  text-align: center;
  color: var(--ink-soft);
  font-size: 13px;
}

.pick-item {
  display: flex;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
}

.pick-main {
  min-width: 0;
  flex: 1;
}

.pick-stem {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pick-meta {
  margin-top: 6px;
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: var(--ink-soft);
}

.dialog-grid {
  padding: 12px 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.ai-dialog-grid {
  gap: 10px;
}

.ai-requirement-input {
  min-height: 132px;
  resize: vertical;
}

.ai-requirement-input::placeholder {
  color: color-mix(in srgb, var(--ink-soft) 72%, white 28%);
  line-height: 1.55;
}

.ai-hint-box {
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--line) 82%, white 18%);
  border-radius: 12px;
  background: color-mix(in srgb, var(--line) 18%, white 82%);
}

.ai-hint-box span {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: color-mix(in srgb, var(--ink-soft) 82%, white 18%);
}

.ai-hint-box p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: color-mix(in srgb, var(--ink-soft) 88%, white 12%);
}

.ai-hint-box p + p {
  margin-top: 8px;
}

.dialog-full {
  grid-column: 1 / -1;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 14px;
  border-top: 1px solid var(--line);
}

@media (max-width: 520px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .class-pick-grid,
  .score-summary-bar {
    grid-template-columns: 1fr;
  }

  .add-questions .actions {
    width: 100%;
    flex-direction: column;
  }

  .add-questions .actions .button {
    width: 100%;
    justify-content: center;
  }

  .dialog-filters,
  .dialog-grid {
    grid-template-columns: 1fr;
  }

  .ai-hint-box {
    padding: 10px 12px;
  }

  .question-side {
    align-items: stretch;
  }

  .score-input {
    width: 64px;
    align-self: flex-end;
  }
}
</style>


