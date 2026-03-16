<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Save } from 'lucide-vue-next'
import { getClassDetail, updateClass } from '@/api/teacher'

const route = useRoute()
const router = useRouter()
const classId = Number(route.params.id)

const form = ref({
  name: '',
  grade_name: '',
  subject: ''
})

const CLASS_NAME_MAX = 60
const GRADE_NAME_MAX = 30
const SUBJECT_MAX = 30

const isLoading = ref(true)
const isSubmitting = ref(false)

const fetchDetail = async () => {
  if (!Number.isFinite(classId) || classId <= 0) {
    alert('班级ID无效')
    router.replace('/app/teacher/classes')
    return
  }

  try {
    isLoading.value = true
    const res = await getClassDetail(classId)
    const detail = (res as any).class || {}
    form.value = {
      name: String(detail.name || ''),
      grade_name: String(detail.grade_name || ''),
      subject: String(detail.subject || ''),
    }
  } catch (error) {
    console.error('Failed to load class detail', error)
    alert('加载班级信息失败')
    router.replace(`/app/teacher/classes/${classId}`)
  } finally {
    isLoading.value = false
  }
}

const handleUpdate = async () => {
  const payload = {
    class_id: classId,
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
    await updateClass(payload)
    router.replace(`/app/teacher/classes/${classId}`)
  } catch (error) {
    console.error('Failed to update class', error)
    alert('更新班级失败')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="view-class-edit">
    <div v-if="isLoading" class="loading-state">加载中...</div>

    <template v-else>
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
          @click="handleUpdate"
        >
          <Save :size="18" />
          {{ isSubmitting ? '提交中...' : '确认修改' }}
        </button>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.view-class-edit {
  display: flex;
  flex-direction: column;
  padding-bottom: 80px;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 48px 0;
  color: var(--ink-soft);
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
