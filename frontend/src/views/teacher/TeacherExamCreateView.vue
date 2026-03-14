<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Sparkles, Save } from 'lucide-vue-next'
import { createExam, getClasses } from '@/api/teacher'
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

const isSubmitting = ref(false)

const goBack = () => {
  router.back()
}

const handleCreate = async () => {
  try {
    isSubmitting.value = true
    const now = new Date()
    const end = new Date(now.getTime() + Number(form.value.duration_minutes || 60) * 60 * 1000)

    const payload = {
      title: form.value.title,
      subject: form.value.subject,
      duration_minutes: Number(form.value.duration_minutes || 60),
      start_time: now.toISOString(),
      end_time: end.toISOString(),
      instructions: form.value.instructions || null,
      allow_review: true,
      random_question_order: false,
      class_ids: form.value.selected_class_id ? [form.value.selected_class_id] : [],
      question_items: [],
    }

    const res = await createExam(payload)
    const examId = (res as any).exam?.id
    if (examId) {
      router.replace(`/app/teacher/exams/${examId}`)
    } else {
      router.back()
    }
  } catch (error) {
    console.error('Failed to create exam', error)
  } finally {
    isSubmitting.value = false
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
          <input type="number" class="form-input" value="将根据试题自动计算" disabled />
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
          <p>尚未添加任何试题</p>
          <div class="actions">
            <button type="button" class="button button--ghost button--small">从题库选择</button>
            <button type="button" class="button button--ghost button--small">
              <Sparkles :size="14" /> AI 智能组卷
            </button>
          </div>
        </div>
      </div>
    </div>

    <footer class="bottom-action">
      <button 
        class="button button--primary" 
        :disabled="isSubmitting || !form.title"
        @click="handleCreate"
      >
        <Save :size="18" />
        {{ isSubmitting ? '保存中...' : '保存为草稿' }}
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
  display: flex;
  gap: 16px;
}

.form-row > .form-group {
  flex: 1;
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
</style>


