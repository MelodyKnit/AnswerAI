<script setup lang="ts">
import { ArrowRight, Bot } from 'lucide-vue-next'
import heroBg from '@/assets/bg1.png'

const pageBackgroundStyle = {
  backgroundImage: `linear-gradient(rgba(246, 248, 251, 0.74), rgba(246, 248, 251, 0.74)), url(${heroBg})`,
}
</script>

<template>
  <main class="landing-page" :style="pageBackgroundStyle">
    <header class="landing-topbar">
      <div class="landing-brand">
        <Bot :size="20"/>
        <strong>AI Answer</strong>
      </div>
      <RouterLink class="button--ghost button--sm" to="/auth">
        登录系统
      </RouterLink>
    </header>

    <section class="hero-section">
      <div class="hero-content">
        <div class="hero-badge">AI 个性化学习诊断</div>
        <h1 class="hero-title">
          《工程图学》<br/>
          个性化学习平台
        </h1>
        <div class="hero-actions">
          <RouterLink to="/app/student/dashboard" class="button button--lg">
            学生端体验
            <ArrowRight :size="18" />
          </RouterLink>
          <RouterLink to="/app/teacher/dashboard" class="button--ghost button--lg">
            进入教师控制台
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.landing-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}

.landing-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
}

.landing-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.button--sm {
  min-height: 36px;
  padding: 0 16px;
  font-size: 14px;
}

.button--lg {
  min-height: 54px;
  padding: 0 24px;
  font-size: 16px;
}

.hero-section {
  flex: 1;
  padding: 24px 20px;
  display: flex;
  justify-content: center;
  align-items: center; /* keep mobile centered if we want, or left config */
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  margin-bottom: 5em;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero-badge {
  display: inline-block;
  align-self: flex-start;
  margin-top: -10px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  color: var(--accent-strong);
  background: var(--accent-soft);
  margin-bottom: 24px;
  border: 1px solid rgba(15, 118, 110, 0.2);
}

.hero-title {
  text-align: center;
  font-size: 40px;
  line-height: 1.15;
  letter-spacing: -0.04em;
  color: var(--ink);
  margin-bottom: 20px;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  align-items: center;
}

@media (min-width: 768px) {
  .hero-section {
    padding: 32px 40px;
  }
  
  .hero-title {
    font-size: 56px;
  }

  .hero-actions {
    flex-direction: row;
    align-items: center;
    justify-content: center;
  }
}
</style>