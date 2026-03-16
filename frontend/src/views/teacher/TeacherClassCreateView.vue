<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Save } from 'lucide-vue-next'
import { createClass } from '@/api/teacher'

const router = useRouter()

const form = ref({
  name: '',
  grade_name: '',
  subject: ''
})

const CLASS_NAME_MAX = 60
const GRADE_NAME_MAX = 30
const SUBJECT_MAX = 30

const isSubmitting = ref(false)



const handleCreate = async () => {
  const payload = {
    name: form.value.name.trim(),
    grade_name: form.value.grade_name.trim(),
    subject: form.value.subject.trim(),
  }

  if (!payload.name || !payload.grade_name || !payload.subject) {
    alert('请填写完整信息')
    return
  }

  if (payload.name.length > CLASS_NAME_MAX || payload.grade_name.length > GRADE_NAME_MAX || payload.subject.length > SUBJECT_MAX) {
    alert('输入内容超出长度限制，请精简后再提交')
    return
  }
  
  try {
    isSubmitting.value = true
    await createClass(payload)
    
    // assuming it returns the new class in res.class or similar
    // we just go back to classes list
    router.replace('/app/teacher/classes')
  } catch (error) {
    console.error('Failed to create class', error)
    alert('创建班级失败')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="view-class-create">
    

    <div class="form-container">
      <div class="form-group">
        <label>班级名称</label>
        <input v-model="form.name" type="text" maxlength="60" placeholder="例如：三年二班" class="form-input" />
      </div>

      <div class="form-group">
        <label>所属年级</label>
        <input v-model="form.grade_name" type="text" maxlength="30" placeholder="如：八年级" class="form-input" />
      </div>

      <div class="form-group">
        <label>任教学科</label>
        <input v-model="form.subject" type="text" maxlength="30" placeholder="如：物理" class="form-input" />
      </div>
    </div>

    <footer class="bottom-action">
      <button
        class="button button--primary"
        :disabled="isSubmitting || !form.name"
        @click="handleCreate"
      >
        <Save :size="18" />
        {{ isSubmitting ? '提交中...' : '确认创建' }}
      </button>
    </footer>
  </div>
</template>

<style scoped>
.view-class-create {
  display: flex;
  flex-direction: column;
  padding-bottom: 80px; 
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