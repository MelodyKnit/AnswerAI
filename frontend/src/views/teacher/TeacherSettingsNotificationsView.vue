<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Loader2, Save } from 'lucide-vue-next'

const form = reactive({
  examReminder: localStorage.getItem('settings.notify.examReminder') !== '0',
  reviewUpdate: localStorage.getItem('settings.notify.reviewUpdate') !== '0',
  weakPointPush: localStorage.getItem('settings.notify.weakPointPush') !== '0',
})

const saving = ref(false)
const msg = ref('')

const save = async () => {
  msg.value = ''
  saving.value = true

  try {
    localStorage.setItem('settings.notify.examReminder', form.examReminder ? '1' : '0')
    localStorage.setItem('settings.notify.reviewUpdate', form.reviewUpdate ? '1' : '0')
    localStorage.setItem('settings.notify.weakPointPush', form.weakPointPush ? '1' : '0')
    msg.value = '通知偏好已保存'
  } finally {
    setTimeout(() => {
      saving.value = false
    }, 220)
  }
}
</script>

<template>
  <div class="setting-page">
    <header class="head">
      <h1>消息通知</h1>
      <p>配置你希望接收的教学提醒类型。</p>
    </header>

    <section class="card">
      <label class="switch-row">
        <div>
          <h3>考试提醒</h3>
          <p>考试开始前和结束后接收提醒</p>
        </div>
        <input v-model="form.examReminder" type="checkbox" class="switch" />
      </label>

      <label class="switch-row">
        <div>
          <h3>阅卷动态</h3>
          <p>出现新待阅主观题时通知我</p>
        </div>
        <input v-model="form.reviewUpdate" type="checkbox" class="switch" />
      </label>

      <label class="switch-row">
        <div>
          <h3>薄弱点推送</h3>
          <p>推送班级共性薄弱点与复习建议</p>
        </div>
        <input v-model="form.weakPointPush" type="checkbox" class="switch" />
      </label>

      <div class="actions">
        <button class="save-btn" :disabled="saving" @click="save">
          <Loader2 v-if="saving" :size="16" class="spin" />
          <Save v-else :size="16" />
          保存通知偏好
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
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #edf2f8;
  border-radius: 10px;
  padding: 10px;
}

.switch-row h3 {
  margin: 0;
  font-size: 14px;
}

.switch-row p {
  margin: 3px 0 0;
  font-size: 12px;
  color: #64748b;
}

.switch {
  width: 40px;
  height: 22px;
  accent-color: #0f766e;
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
