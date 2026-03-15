<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Play, Sparkles, Save } from 'lucide-vue-next'
import { createExam, getClasses, getQuestions, publishExam } from '@/api/teacher'
import { getSubjects } from '@/api/meta'

const router = useRouter()

const form = ref({
  title: '',
  instructions: '',
  subject: '',
  duration_minutes: 60,
  selected_class_id: undefined as number | undefined,
})

const subjects = ref<Array<{ id: number, name: string }>>([])
const classes = ref<Array<{ id: number, name: string }>>([])
const questionBank = ref<any[]>([])
const examQuestions = ref<Array<{ question_id: number, stem: string, type: string, score: number, difficulty: number }>>([])

const isQuestionSelectorOpen = ref(false)
const isAiAssembleOpen = ref(false)
const isQuestionsLoading = ref(false)
const isAiAssembling = ref(false)

const questionKeyword = ref('')
const questionTypeFilter = ref('all')
const tempSelectedQuestionIds = ref<number[]>([])

const aiCount = ref(5)
const aiType = ref('all')
const aiDifficultyMin = ref(0)
const aiDifficultyMax = ref(1)
const aiKeyword = ref('')

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

const filteredQuestionBank = computed(() => {
  const keyword = questionKeyword.value.trim().toLowerCase()
  return questionBank.value.filter((q) => {
    const keywordMatch = !keyword || String(q.stem || '').toLowerCase().includes(keyword)
    const typeMatch = questionTypeFilter.value === 'all' || q.type === questionTypeFilter.value
    const subjectMatch = !form.value.subject || q.subject === form.value.subject
    return keywordMatch && typeMatch && subjectMatch
  })
})

const selectedQuestionIdSet = computed(() => {
  return new Set(examQuestions.value.map((item) => item.question_id))
})

const goBack = () => {
  router.back()
}

const handleCreate = async (mode: 'draft' | 'publish' = 'draft') => {
  const title = form.value.title.trim()
  if (!title) {
    alert('请先填写考试名称')
    return
  }
  if (!form.value.subject) {
    alert('请先选择科目')
    return
  }
  if (Number(form.value.duration_minutes) <= 0) {
    alert('考试时长必须大于 0 分钟')
    return
  }

  try {
    submitMode.value = mode
    isSubmitting.value = true
    const now = new Date()
    const end = new Date(now.getTime() + Number(form.value.duration_minutes || 60) * 60 * 1000)

    const payload = {
      title,
      subject: form.value.subject,
      duration_minutes: Number(form.value.duration_minutes || 60),
      start_time: now.toISOString(),
      end_time: end.toISOString(),
      instructions: form.value.instructions || null,
      allow_review: true,
      random_question_order: false,
      class_ids: form.value.selected_class_id ? [form.value.selected_class_id] : [],
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
      if (mode === 'publish') {
        await publishExam(examId)
      }
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
  try {
    const [subjectRes, classRes] = await Promise.all([getSubjects(), getClasses({ page_size: 100 })])
    subjects.value = (subjectRes as any).items || []
    classes.value = (classRes as any).items || []
    if (!form.value.subject && subjects.value.length > 0) {
      form.value.subject = subjects.value[0].name
    }
  } catch (error) {
    console.error('Failed to load metadata for exam creation', error)
  }
}

onMounted(() => {
  fetchMeta()
})

const fetchQuestionBank = async () => {
  try {
    isQuestionsLoading.value = true
    const res = await getQuestions({
      page: 1,
      page_size: 100,
      subject: form.value.subject || undefined,
    })
    questionBank.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to load question bank', error)
  } finally {
    isQuestionsLoading.value = false
  }
}

const openQuestionSelector = async () => {
  if (!questionBank.value.length) {
    await fetchQuestionBank()
  }
  tempSelectedQuestionIds.value = examQuestions.value.map((item) => item.question_id)
  isQuestionSelectorOpen.value = true
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
      score: Number(q.score || 5),
      difficulty: Number(q.difficulty || 0.5),
    })
  })
  examQuestions.value = next
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
      score: Number(q.score || 5),
      difficulty: Number(q.difficulty || 0.5),
    }))

  examQuestions.value = [...preserved, ...appended]
  closeQuestionSelector()
}

const removeExamQuestion = (questionId: number) => {
  examQuestions.value = examQuestions.value.filter((item) => item.question_id !== questionId)
}

const openAiAssemble = async () => {
  if (!questionBank.value.length) {
    await fetchQuestionBank()
  }
  isAiAssembleOpen.value = true
}

const closeAiAssemble = () => {
  isAiAssembleOpen.value = false
}

const shuffle = <T,>(arr: T[]): T[] => {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

const runAiAssemble = async () => {
  if (!questionBank.value.length) {
    await fetchQuestionBank()
  }

  const min = Math.max(0, Math.min(1, Number(aiDifficultyMin.value || 0)))
  const max = Math.max(min, Math.min(1, Number(aiDifficultyMax.value || 1)))
  const count = Math.max(1, Math.min(50, Number(aiCount.value || 1)))
  const keyword = aiKeyword.value.trim().toLowerCase()
  const existing = selectedQuestionIdSet.value

  try {
    isAiAssembling.value = true
    const candidates = questionBank.value.filter((q) => {
      if (existing.has(q.id)) return false
      if (form.value.subject && q.subject !== form.value.subject) return false
      if (aiType.value !== 'all' && q.type !== aiType.value) return false
      const diff = Number(q.difficulty ?? 0.5)
      if (diff < min || diff > max) return false
      if (keyword && !String(q.stem || '').toLowerCase().includes(keyword)) return false
      return true
    })

    if (!candidates.length) {
      alert('未找到符合条件的题目，请放宽筛选条件')
      return
    }

    const picked = shuffle(candidates).slice(0, count)
    appendQuestionsToExam(picked)
    closeAiAssemble()
  } catch (error) {
    console.error('AI assemble failed', error)
    alert('智能组卷失败，请稍后重试')
  } finally {
    isAiAssembling.value = false
  }
}

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
            <option v-for="subject in subjects" :key="subject.id" :value="subject.name">{{ subject.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>关联班级（可选）</label>
          <select v-model="form.selected_class_id" class="form-input">
            <option :value="undefined">暂不选择</option>
            <option v-for="cls in classes" :key="cls.id" :value="cls.id">{{ cls.name }}</option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>时长 (分钟)</label>
          <input v-model="form.duration_minutes" type="number" class="form-input" />
        </div>
        <div class="form-group">
          <label>总分</label>
          <input type="text" class="form-input" :value="`${totalScore}（自动计算）`" readonly />
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
        <div class="dialog-grid">
          <label class="form-group">
            <span>题目数量</span>
            <input v-model.number="aiCount" class="form-input" type="number" min="1" max="50" />
          </label>
          <label class="form-group">
            <span>题型</span>
            <select v-model="aiType" class="form-input">
              <option v-for="option in questionTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label class="form-group">
            <span>难度下限</span>
            <input v-model.number="aiDifficultyMin" class="form-input" type="number" min="0" max="1" step="0.1" />
          </label>
          <label class="form-group">
            <span>难度上限</span>
            <input v-model.number="aiDifficultyMax" class="form-input" type="number" min="0" max="1" step="0.1" />
          </label>
          <label class="form-group dialog-full">
            <span>关键词（可选）</span>
            <input v-model="aiKeyword" class="form-input" type="text" placeholder="例如：函数、阅读理解" />
          </label>
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

@media (max-width: 768px) {
  .form-row {
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

  .question-side {
    align-items: stretch;
  }

  .score-input {
    width: 64px;
    align-self: flex-end;
  }
}
</style>


