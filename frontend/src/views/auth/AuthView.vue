<script setup lang="ts">
import { ref } from 'vue'
import { Bot, ArrowLeft } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const activeMode = ref<'login' | 'register'>('login')
const activeRole = ref<'student' | 'teacher'>('student')
const errorMsg = ref('')
const isLoading = ref(false)

const form = ref({
  name: '',
  username: '',
  loginId: '',
  email: '',
  password: '',
  confirmPassword: '',
  code: ''
})

const usernameRegex = /^(?=.*[A-Za-z])[A-Za-z0-9]+$/

const handleSubmit = async () => {
  errorMsg.value = ''

  if (activeMode.value === 'register') {
    if (!usernameRegex.test(form.value.username)) {
      errorMsg.value = '用户名必须为英文或英文+数字组合'
      return
    }
    if (form.value.password !== form.value.confirmPassword) {
      errorMsg.value = '两次输入密码不一致'
      return
    }
  }

  isLoading.value = true
  try {
    if (activeMode.value === 'login') {
      await authStore.login({
        login_id: form.value.loginId,
        password: form.value.password
      })
    } else {
      const normalizedCode = form.value.code.trim()
      await authStore.register({
        role: activeRole.value,
        name: form.value.name,
        username: form.value.username,
        email: form.value.email,
        password: form.value.password,
        confirm_password: form.value.confirmPassword,
        ...(activeRole.value === 'student'
          ? (normalizedCode ? { class_code: normalizedCode } : {})
          : (normalizedCode ? { teacher_invite_code: normalizedCode } : {}))
      })
    }
    
    if (authStore.user?.role === 'teacher') {
      router.push('/app/teacher/dashboard')
    } else {
      router.push('/app/student/dashboard')
    }
  } catch (err: any) {
    errorMsg.value = err.message || '请求失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <header class="auth-header">
      <button @click="router.back()" class="back-btn">
        <ArrowLeft :size="18" />
        <span class="sr-only">返回</span>
      </button>
      <div class="brand">
        <Bot :size="20" />
        <strong>AI Answer</strong>
      </div>
      <!-- Spacer for flex-between alignment -->
      <div style="width: 38px"></div> 
    </header>

    <main class="auth-main">
      <div class="auth-content">
        <div class="auth-headings">
          <h1>{{ activeMode === 'login' ? '欢迎回来' : '创建新账号' }}</h1>
          <p>{{ activeMode === 'login' ? '登录您的账号，继续无缝的个性化学习与管理体验。' : '加入系统，开启 AI 驱动的学习之旅。' }}</p>
        </div>

        <div class="role-selector">
          <button 
            type="button"
            class="role-btn" 
            :class="{ 'role-btn--active': activeRole === 'student' }"
            @click="activeRole = 'student'"
          >
            我是学生
          </button>
          <button 
            type="button"
            class="role-btn" 
            :class="{ 'role-btn--active': activeRole === 'teacher' }"
            @click="activeRole = 'teacher'"
          >
            我是教师
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="auth-form">
          <div class="form-group" v-if="activeMode === 'register'">
            <label for="name">真实姓名</label>
            <input 
              id="name"
              type="text" 
              placeholder="请输入您的姓名" 
              v-model="form.name" 
              required 
            />
          </div>

          <div class="form-group" v-if="activeMode === 'login'">
            <label for="login-id">登录账号</label>
            <input
              id="login-id"
              type="text"
              placeholder="请输入登录账号"
              v-model="form.loginId"
              required
            />
          </div>

          <div class="form-group" v-if="activeMode === 'register'">
            <label for="username">用户名</label>
            <input
              id="username"
              type="text"
              placeholder="仅英文或英文+数字，如 student01"
              v-model="form.username"
              required
              pattern="^(?=.*[A-Za-z])[A-Za-z0-9]+$"
            />
          </div>

          <div class="form-group" v-if="activeMode === 'register'">
            <label for="email">邮箱地址</label>
            <input 
              id="email"
              type="email" 
              placeholder="name@example.com" 
              v-model="form.email" 
              required 
            />
          </div>

          <div class="form-group">
            <div class="label-row">
              <label for="password">密码</label>
              <a href="#" v-if="activeMode === 'login'" class="forgot-link">忘记密码？</a>
            </div>
            <input
              id="password"
              type="password"
              placeholder="最少8位密码"
              v-model="form.password"
              minlength="8"
              required
            />
          </div>

          <div class="form-group" v-if="activeMode === 'register'">
            <label for="confirm-password">确认密码</label>
            <input
              id="confirm-password"
              type="password"
              placeholder="再次输入密码"
              v-model="form.confirmPassword"
              minlength="8"
              required
            />
          </div>

          <div class="form-group" v-if="activeRole === 'student' && activeMode === 'register'">
            <label for="class-code">班级邀请码 <span>(选填)</span></label>
            <input 
              id="class-code"
              type="text" 
              placeholder="输入教师提供的班级码" 
              v-model="form.code" 
            />
          </div>

          <div class="form-group" v-if="activeRole === 'teacher' && activeMode === 'register'">
            <label for="school-code">组织机构代码 <span>(选填)</span></label>
            <input 
              id="school-code"
              type="text" 
              placeholder="输入学校或机构的专有代码" 
              v-model="form.code" 
            />
          </div>

          <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

          <button type="submit" class="button submit-btn" :disabled="isLoading">
            {{ isLoading ? '请稍候...' : (activeMode === 'login' ? '登 录' : '注 册 账 号') }}
          </button>
        </form>

        <div class="auth-footer">
          <template v-if="activeMode === 'login'">
            <span>还没有账号？</span>
            <button type="button" class="text-btn" @click="activeMode = 'register'">立即注册</button>
          </template>
          <template v-else>
            <span>已经有账号了？</span>
            <button type="button" class="text-btn" @click="activeMode = 'login'">直接登录</button>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg);
}

.auth-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  transition: background-color 0.2s;
}

.back-btn:hover {
  background: rgba(25, 20, 17, 0.04);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
}

.brand strong {
  font-weight: 600;
  letter-spacing: -0.02em;
  font-size: 16px;
}

.auth-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 24px;
}

.auth-content {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.auth-headings h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--ink);
  margin-bottom: 12px;
}

.auth-headings p {
  font-size: 15px;
  line-height: 1.5;
  color: var(--ink-soft);
}

.role-selector {
  display: flex;
  background: rgba(25, 20, 17, 0.04);
  padding: 4px;
  border-radius: 999px;
  gap: 4px;
}

.role-btn {
  flex: 1;
  padding: 10px 0;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.role-btn--active {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 2px 8px rgba(25, 20, 17, 0.06);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.form-group label span {
  font-weight: 400;
  color: var(--ink-soft);
}

.forgot-link {
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.form-group input {
  width: 100%;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--line-strong, #e5e5e5);
  background: #fff;
  font-size: 15px;
  color: var(--ink);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input::placeholder {
  color: #a3a3a3;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.submit-btn {
  margin-top: 12px;
  width: 100%;
  min-height: 52px;
  font-size: 16px;
  font-weight: 600;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error-msg {
  color: #dc2626;
  font-size: 14px;
  text-align: center;
  background: #fef2f2;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #fecaca;
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  color: var(--ink-soft);
}

.text-btn {
  background: none;
  border: none;
  color: var(--ink);
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  font-size: inherit;
}

.text-btn:hover {
  text-decoration: underline;
}

@media (min-width: 768px) {
  .auth-main {
    padding-top: 80px;
  }

  .auth-headings h1 {
    font-size: 32px;
  }
}
</style>