<script setup lang="ts">
import { ArrowRight, Bot, Target, Network, Layers } from 'lucide-vue-next'

const features = [
  {
    title: '智能判卷与诊断',
    desc: '客观题主观题秒级批改，深层挖掘错因与知识盲点，告别机械阅卷。',
    icon: Target
  },
  {
    title: '苏格拉底AI辅导',
    desc: '不直接喂答案。通过有逻辑的连续追问，启发学生主动思考并找到解法。',
    icon: Bot
  },
  {
    title: '动态知识网络',
    desc: '基于每一次答题轨迹，实时推演并呈现概念掌握度，精准定位薄弱项。',
    icon: Network
  },
  {
    title: '数字教研工作台',
    desc: '为教师提供多维学情数据看板，辅助差异化教学布置，实现减负增效。',
    icon: Layers
  }
]
</script>

<template>
  <main class="landing-page">
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
        <div class="hero-badge">AI 驱动的智能教育引擎</div>
        <h1 class="hero-title">
          让每一次答题，<br/>
          都成为跨越的阶梯。
        </h1>
        <p class="hero-subtitle">
          抛弃盲目的题海战术。我们通过大模型技术重塑练习体验，提供精准诊断、启发式陪伴与全景学情追踪，把精力用在刀刃上。
        </p>

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

    <section class="features-section">
      <div class="features-container">
        <h2 class="section-heading">围绕核心痛点<br/>重新设计练考流程</h2>
        
        <div class="features-grid">
          <div 
            v-for="feat in features" 
            :key="feat.title" 
            class="feature-row"
          >
            <div class="feature-icon">
              <component :is="feat.icon" :size="24" />
            </div>
            <div class="feature-body">
              <h3>{{ feat.title }}</h3>
              <p>{{ feat.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="cta-section">
      <div class="cta-content">
        <h2>现在就开始使用</h2>
        <RouterLink to="/auth" class="button button--lg">
          登录或注册
          <ArrowRight :size="18" />
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.landing-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
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
  padding: 60px 20px 40px;
  display: flex;
  flex-direction: column;
  align-items: center; /* keep mobile centered if we want, or left config */
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.hero-badge {
  display: inline-block;
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
  font-size: 40px;
  line-height: 1.15;
  letter-spacing: -0.04em;
  color: var(--ink);
  margin-bottom: 20px;
}

.hero-subtitle {
  font-size: 16px;
  line-height: 1.6;
  color: var(--ink-soft);
  margin-bottom: 40px;
  max-width: 600px;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.features-section {
  padding: 60px 20px;
  background: linear-gradient(180deg, var(--bg) 0%, rgba(25, 20, 17, 0.02) 100%);
  border-top: 1px solid var(--line);
}

.features-container {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.section-heading {
  font-size: 28px;
  line-height: 1.25;
  letter-spacing: -0.02em;
  margin-bottom: 40px;
  color: var(--ink);
}

.features-grid {
  display: flex;
  flex-direction: column;
}

.feature-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  padding: 24px 0;
  border-top: 1px solid var(--line);
}

.feature-row:last-child {
  border-bottom: 1px solid var(--line);
}

.feature-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  color: var(--accent);
}

.feature-body h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 6px;
  letter-spacing: -0.01em;
}

.feature-body p {
  font-size: 15px;
  line-height: 1.6;
  color: var(--ink-soft);
}

.cta-section {
  padding: 80px 20px 100px;
  text-align: left;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.cta-section h2 {
  font-size: 28px;
  letter-spacing: -0.03em;
  margin-bottom: 24px;
  color: var(--ink);
}

@media (min-width: 768px) {
  .hero-section {
    padding: 100px 40px 60px;
  }
  
  .hero-title {
    font-size: 56px;
  }

  .hero-subtitle {
    font-size: 18px;
  }

  .hero-actions {
    flex-direction: row;
    align-items: center;
  }

  .features-section {
    padding: 80px 40px 100px;
  }

  .section-heading {
    font-size: 36px;
    margin-bottom: 48px;
  }

  .feature-row {
    padding: 32px 0;
    gap: 24px;
    align-items: flex-start;
  }
  
  .features-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px 60px;
  }

  .feature-row {
    display: grid;
    grid-template-columns: auto 1fr;
    padding: 0;
    gap: 24px;
    border: none !important;
    background: transparent;
  }

  .feature-icon {
    width: 48px;
    height: 48px;
    margin-bottom: 0;
    border: none;
    background: transparent;
    box-shadow: none;
  }

  .feature-body h3 {
    font-size: 20px;
  }

  .cta-section {
    padding: 100px 40px;
    align-items: center;
    text-align: center;
  }
}
</style>