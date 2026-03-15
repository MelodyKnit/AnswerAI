<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Lock, Loader2, Save } from 'lucide-vue-next'
import { changePassword } from '@/api/auth'

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const saving = ref(false)
const msg = ref('')

const save = async () => {
  msg.value = ''

  if (!form.old_password || !form.new_password || !form.confirm_password) {
    msg.value = '请完整填写密码信息'
    return
  }

  if (form.new_password.length < 8) {
    msg.value = '新密码至少 8 位'
    return
  }

  if (form.new_password !== form.confirm_password) {
    msg.value = '两次输入的新密码不一致'
    return
  }

  try {
    saving.value = true
    await changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    })

    msg.value = '密码修改成功'
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
  } catch (error: any) {
    msg.value = error?.message || '密码修改失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="setting-page">
    <header class="head">
      <h1>账号与安全</h1>
      <p>定期更新密码，保障账号安全。</p>
    </header>

    <section class="card">
      <label class="field">
        <span>当前密码</span>
        <input v-model="form.old_password" type="password" placeholder="请输入当前密码" />
      </label>

      <label class="field">
        <span>新密码</span>
        <input v-model="form.new_password" type="password" placeholder="至少 8 位" />
      </label>

      <label class="field">
        <span>确认新密码</span>
        <input v-model="form.confirm_password" type="password" placeholder="再次输入新密码" />
      </label>

      <div class="tip">
        <Lock :size="14" />
        <span>建议使用字母和数字组合，避免与旧密码相同。</span>
      </div>

      <div class="actions">
        <button class="save-btn" :disabled="saving" @click="save">
          <Loader2 v-if="saving" :size="16" class="spin" />
          <Save v-else :size="16" />
          修改密码
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
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
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

.tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.actions {
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
</style>
