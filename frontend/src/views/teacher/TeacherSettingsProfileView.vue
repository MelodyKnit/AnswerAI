<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Loader2, Save } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { updateProfile } from '@/api/auth'

const authStore = useAuthStore()

const form = reactive({
  name: authStore.user?.name || '',
  phone: authStore.user?.phone || '',
  school_name: authStore.user?.school_name || '',
  grade_name: authStore.user?.grade_name || '',
  avatar_url: authStore.user?.avatar_url || '',
})

const saving = ref(false)
const msg = ref('')

const saveProfile = async () => {
  msg.value = ''
  if (!form.name.trim()) {
    msg.value = '姓名不能为空'
    return
  }

  try {
    saving.value = true
    const res: any = await updateProfile({
      name: form.name.trim(),
      phone: form.phone.trim() || undefined,
      school_name: form.school_name.trim() || undefined,
      grade_name: form.grade_name.trim() || undefined,
      avatar_url: form.avatar_url.trim() || undefined,
    })
    authStore.setUser(res.user)
    msg.value = '个人资料已保存'
  } catch (error: any) {
    msg.value = error?.message || '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="setting-page">
    <header class="head">
      <h1>个人资料</h1>
      <p>更新教师基本信息与展示资料。</p>
    </header>

    <section class="card">
      <div class="field-grid">
        <label class="field">
          <span>姓名</span>
          <input v-model="form.name" type="text" placeholder="请输入姓名" />
        </label>
        <label class="field">
          <span>手机号</span>
          <input v-model="form.phone" type="text" placeholder="可选" />
        </label>
        <label class="field">
          <span>学校</span>
          <input v-model="form.school_name" type="text" placeholder="可选" />
        </label>
        <label class="field">
          <span>年级</span>
          <input v-model="form.grade_name" type="text" placeholder="可选" />
        </label>
        <label class="field field-full">
          <span>头像地址</span>
          <input v-model="form.avatar_url" type="text" placeholder="可选：填入 URL" />
        </label>
      </div>

      <div class="actions">
        <button class="save-btn" :disabled="saving" @click="saveProfile">
          <Loader2 v-if="saving" :size="16" class="spin" />
          <Save v-else :size="16" />
          保存资料
        </button>
        <span v-if="msg" class="msg">{{ msg }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.setting-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.head h1 {
  margin: 0;
  font-size: 24px;
}

.head p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #556278;
}

.card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 12px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-full {
  grid-column: span 2;
}

.field span {
  font-size: 12px;
  color: #64748b;
}

.field input {
  border: 1px solid #d8e0ea;
  border-radius: 9px;
  padding: 8px 10px;
  font-size: 14px;
  background: #fbfdff;
}

.actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.save-btn {
  border: none;
  border-radius: 10px;
  background: #0f766e;
  color: #fff;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.msg {
  font-size: 12px;
  color: #475569;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .field-grid {
    grid-template-columns: 1fr;
  }

  .field-full {
    grid-column: auto;
  }
}
</style>
