<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Compass, Home } from 'lucide-vue-next'

const router = useRouter()

const canGoBack = computed(() => window.history.state.back != null)

const goBack = () => {
  if (canGoBack.value) {
    router.back()
    return
  }
  router.push('/')
}

const goHome = () => {
  router.push('/')
}
</script>

<template>
  <section class="not-found-page">
    <div class="ambient ambient-1"></div>
    <div class="ambient ambient-2"></div>

    <article class="not-found-card">
      <div class="status-pill">
        <Compass :size="14" />
        页面走丢了
      </div>

      <p class="code">404</p>
      <h1>当前页面不存在</h1>
      <p class="desc">
        链接可能已失效，或页面正在调整中。你可以返回上一步，
        或直接回到首页继续浏览。
      </p>

      <div class="actions">
        <button class="button--ghost action-btn" @click="goBack">
          <ArrowLeft :size="16" />
          {{ canGoBack ? '返回上一页' : '返回首页' }}
        </button>
        <button class="button action-btn" @click="goHome">
          <Home :size="16" />
          返回主页
        </button>
      </div>
    </article>
  </section>
</template>

<style scoped>
.not-found-page {
  position: relative;
  min-height: 100dvh;
  width: 100%;
  background:
    radial-gradient(circle at 82% 10%, rgba(15, 118, 110, 0.14), transparent 36%),
    radial-gradient(circle at 12% 92%, rgba(191, 111, 69, 0.12), transparent 40%),
    linear-gradient(160deg, #f8fbfd 0%, #f2f6fa 55%, #eef3f8 100%);
  padding: 24px 16px;
  overflow: hidden;
  display: grid;
  place-items: center;
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(28px);
  opacity: 0.55;
  pointer-events: none;
}

.ambient-1 {
  width: 220px;
  height: 220px;
  right: -72px;
  top: -74px;
  background: rgba(15, 118, 110, 0.2);
}

.ambient-2 {
  width: 220px;
  height: 220px;
  left: -84px;
  bottom: -84px;
  background: rgba(191, 111, 69, 0.2);
}

.not-found-card {
  position: relative;
  z-index: 1;
  width: min(560px, 100%);
  border-radius: 18px;
  border: 1px solid #e6edf5;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: rise 420ms ease-out both;
}

.status-pill {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #0f766e;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 118, 110, 0.26);
  background: rgba(15, 118, 110, 0.08);
}

.code {
  margin: 0;
  font-size: clamp(42px, 10vw, 76px);
  line-height: 0.95;
  letter-spacing: -0.06em;
  font-weight: 700;
  color: #102a43;
}

h1 {
  margin: 0;
  font-size: clamp(22px, 4.8vw, 32px);
  line-height: 1.15;
  letter-spacing: -0.03em;
  color: #102a43;
}

.desc {
  margin: 2px 0 0;
  font-size: 15px;
  line-height: 1.65;
  color: #486581;
}

.actions {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-btn {
  width: 100%;
  min-height: 46px;
  font-size: 14px;
  font-weight: 600;
}

@keyframes rise {
  from {
    transform: translateY(12px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .not-found-page {
    min-height: 100dvh;
    padding: 14px;
  }

  .not-found-card {
    padding: 16px;
    border-radius: 16px;
  }

  .actions {
    grid-template-columns: 1fr;
  }
}
</style>
