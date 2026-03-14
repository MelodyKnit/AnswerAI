<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, AlertTriangle, Zap } from 'lucide-vue-next'
import http from '@/lib/http'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const resultData = ref<any>(null)
const loading = ref(true)
const errorMsg = ref('')

onMounted(async () => {
  try {
    const res = await http.get('/student/results/overview', { params: { exam_id: examId } })
    resultData.value = res.data.data
  } catch (error: any) {
    errorMsg.value = error.response?.data?.message || '无法获取成绩信息'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="view-results">
    <header class="top-nav">
      <button class="icon-button" @click="router.push('/app/student/exams')">
        <ArrowLeft :size="24" />
      </button>
      <span class="nav-title">成绩概览</span>
      <div style="width: 24px"></div>
    </header>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="errorMsg" class="error-state">
      <AlertTriangle :size="40" class="error-icon" />
      <p>{{ errorMsg }}</p>
      <button class="button" @click="router.back()" style="margin-top: 16px;">返回</button>
    </div>
    
    <div v-else-if="resultData" class="results-content">
      <!-- Score Summary -->
      <section class="score-card">
        <div class="score-main">
          <div class="score-value">{{ resultData.score_summary.total_score }}<span class="unit">分</span></div>
          <div class="score-label">总得分</div>
        </div>
        <div class="score-details">
          <div class="detail-item">
            <span class="label">客观题</span>
            <span class="value">{{ resultData.score_summary.objective_score }}</span>
          </div>
          <div class="divider"></div>
          <div class="detail-item">
            <span class="label">主观题</span>
            <span class="value">{{ resultData.score_summary.subjective_score }}</span>
          </div>
          <div class="divider"></div>
          <div class="detail-item">
            <span class="label">班级排名</span>
            <span class="value">{{ resultData.ranking_summary.ranking_in_class || '-' }}</span>
          </div>
        </div>
      </section>

      <!-- AI Insights -->
      <section class="insight-section" v-if="resultData.ai_summary">
        <div class="section-header">
          <Zap :size="18" class="accent-icon"/>
          <h2>AI 试卷分析</h2>
        </div>
        <div class="insight-box">
          <p>{{ resultData.ai_summary }}</p>
        </div>
      </section>

      <!-- Risk Alerts -->
      <section class="risk-section" v-if="resultData.risk_alerts?.length">
        <div class="section-header">
          <AlertTriangle :size="18" class="warning-icon"/>
          <h2>风险预警</h2>
        </div>
        <div class="risk-list">
          <div v-for="(risk, idx) in resultData.risk_alerts" :key="idx" class="risk-item">
            {{ risk }}
          </div>
        </div>
      </section>

      <!-- Action -->
      <div class="actions">
        <button class="button button-large button-block">查看错题解析</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-results {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
  padding: 16px;
  max-width: 480px;
  margin: 0 auto;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 24px;
}

.icon-button {
  background: none;
  border: none;
  color: var(--ink);
  padding: 4px;
}

.nav-title {
  font-size: 17px;
  font-weight: 500;
  color: var(--ink);
}

.results-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.score-card {
  background: linear-gradient(135deg, var(--accent) 0%, #0d9488 100%);
  color: #fff;
  border-radius: var(--radius-lg);
  padding: 32px 20px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.2);
}

.score-main {
  text-align: center;
}

.score-value {
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.unit {
  font-size: 20px;
  font-weight: 500;
  margin-left: 4px;
  opacity: 0.9;
}

.score-label {
  font-size: 15px;
  opacity: 0.9;
  margin-top: 8px;
}

.score-details {
  display: flex;
  width: 100%;
  justify-content: space-between;
  background: rgba(255,255,255,0.1);
  padding: 16px;
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
}

.detail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.detail-item .label {
  font-size: 12px;
  opacity: 0.8;
}

.detail-item .value {
  font-size: 18px;
  font-weight: 600;
}

.divider {
  width: 1px;
  background: rgba(255,255,255,0.2);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.accent-icon {
  color: var(--accent);
}

.warning-icon {
  color: #f59e0b;
}

.insight-box {
  background: var(--accent-light);
  padding: 16px;
  border-radius: var(--radius-md);
  color: var(--ink);
  font-size: 14px;
  line-height: 1.6;
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  background: #fef3c7;
  color: #92400e;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.actions {
  margin-top: 16px;
  padding-bottom: 32px;
}

.button-block {
  width: 100%;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--ink-soft);
}

.error-icon {
  color: #ef4444;
  margin-bottom: 16px;
}
</style>
