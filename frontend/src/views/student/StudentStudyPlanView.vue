<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen, Clock3, Target, Sparkles } from 'lucide-vue-next'
import http from '@/lib/http'
import { mapStudyTaskTypeLabel } from '@/utils/studyTask'

const router = useRouter()
const tasks = ref<any[]>([])
const ignoredTasks = ref<any[]>([])
const showIgnored = ref(false)
const aiOverview = ref<any>(null)
const aiActions = ref<string[]>([])
const taskLoading = ref(false)

const refreshTasks = async () => {
  const res: any = await http.get('/student/study-tasks')
  tasks.value = res?.tasks || []
  ignoredTasks.value = res?.ignored_tasks || []
  aiOverview.value = res?.ai_overview || null
  aiActions.value = res?.ai_actions || []
}

const formatDate = (dateString: string) => {
  if (!dateString) return '未知时间'
  const d = new Date(dateString)
  if (Number.isNaN(d.getTime())) return '未知时间'
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

const getPriorityText = (priority: number) => {
  if (priority <= 1) return '高优先'
  if (priority === 2) return '中优先'
  return '常规'
}

const getStatusText = (status?: string) => {
  if (status === 'completed') return '已完成'
  if (status === 'ignored') return '已忽略'
  if (status === 'in_progress') return '进行中'
  return '待开始'
}

const getStartButtonText = (task: any) => {
  if (task.status === 'in_progress') return '继续复习'
  if (task.status === 'completed') return '再次复习'
  return '开始复习'
}

const openTask = async (task: any) => {
  await router.push(`/app/student/study-plan/tasks/${task.id}`)
}

const ignoreTask = async (task: any) => {
  const ok = window.confirm(`确认忽略任务「${task.title}」？你之后仍可通过新计划重新生成。`)
  if (!ok) return
  try {
    taskLoading.value = true
    await http.post('/student/study-tasks/action', { task_id: task.id, action: 'ignore' })
    await refreshTasks()
  } catch (error) {
    console.error('忽略任务失败', error)
    alert('忽略失败，请稍后重试')
  } finally {
    taskLoading.value = false
  }
}

const deleteTask = async (task: any) => {
  const ok = window.confirm(`确认删除任务「${task.title}」？删除后不可恢复。`)
  if (!ok) return
  try {
    taskLoading.value = true
    await http.post('/student/study-tasks/action', { task_id: task.id, action: 'delete' })
    await refreshTasks()
  } catch (error) {
    console.error('删除任务失败', error)
    alert('删除失败，请稍后重试')
  } finally {
    taskLoading.value = false
  }
}

const restoreIgnoredTask = async (task: any) => {
  try {
    taskLoading.value = true
    await http.post('/student/study-tasks/action', { task_id: task.id, action: 'unignore' })
    await refreshTasks()
  } catch (error) {
    console.error('取消忽略失败', error)
    alert('取消忽略失败，请稍后重试')
  } finally {
    taskLoading.value = false
  }
}

onMounted(async () => {
  try {
    await refreshTasks()
  } catch (error) {
    console.error('获取学习任务失败', error)
  }
})
</script>

<template>
  <div class="study-plan-view">
    <header class="hero">
      <div class="hero-row">
        <span class="hero-chip">
          <Sparkles :size="14" />
          AI 智能复习
        </span>
      </div>
      <h1>学习计划</h1>
      <p>基于最近测验表现，为你动态编排最有价值的复习任务。</p>
    </header>

    <section v-if="aiOverview" class="ai-panel">
      <article class="ai-score-card">
        <p class="ai-kicker">AI 学习准备度</p>
        <div class="ai-score-row">
          <p class="ai-score">{{ aiOverview.readiness_score }}</p>
          <p class="ai-score-unit">/100</p>
        </div>
        <p class="ai-summary">{{ aiOverview.summary }}</p>
      </article>

      <article class="ai-metrics">
        <div class="metric-cell">
          <span>待推进任务</span>
          <strong>{{ aiOverview.active_task_count }}</strong>
        </div>
        <div class="metric-cell">
          <span>预计总时长</span>
          <strong>{{ aiOverview.total_minutes }} 分钟</strong>
        </div>
        <div class="metric-cell">
          <span>建议学习轮次</span>
          <strong>{{ aiOverview.suggested_session_minutes }} 分钟/轮</strong>
        </div>
        <div class="metric-cell">
          <span>预计完成周期</span>
          <strong>{{ aiOverview.estimated_completion_days || 1 }} 天</strong>
        </div>
      </article>

      <article class="ai-actions" v-if="aiActions.length">
        <h3>AI 今日行动建议</h3>
        <ul>
          <li v-for="(tip, idx) in aiActions" :key="idx">{{ tip }}</li>
        </ul>
      </article>
    </section>

    <section v-if="tasks.length" class="task-list">
      <article v-for="task in tasks" :key="task.id" class="task-card">
        <div class="card-head">
          <h2>{{ task.title }}</h2>
          <span class="priority" :class="{ high: task.priority <= 1, medium: task.priority === 2 }">
            {{ getPriorityText(task.priority) }}
          </span>
        </div>

        <p class="task-desc">{{ task.content || '按优先顺序完成相关知识点的复习。' }}</p>

        <div class="meta-grid">
          <div class="meta-item">
            <Target :size="14" />
            <span>{{ task.task_type_label || mapStudyTaskTypeLabel(task.task_type) }}</span>
          </div>
          <div class="meta-item">
            <Clock3 :size="14" />
            <span>{{ task.estimated_minutes || 20 }} 分钟</span>
          </div>
          <div class="meta-item">
            <BookOpen :size="14" />
            <span>{{ getStatusText(task.status) }}</span>
          </div>
          <div class="meta-item">
            <span>创建于 {{ formatDate(task.created_at) }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button class="subtle-btn" :disabled="taskLoading" @click="ignoreTask(task)">忽略</button>
          <button class="danger-btn" :disabled="taskLoading" @click="deleteTask(task)">删除</button>
          <button class="start-btn" @click="openTask(task)">{{ getStartButtonText(task) }}</button>
        </div>
      </article>
    </section>

    <section v-if="ignoredTasks.length" class="ignored-section">
      <button class="ignored-toggle" @click="showIgnored = !showIgnored">
        <span>已忽略任务（{{ ignoredTasks.length }}）</span>
        <span>{{ showIgnored ? '收起' : '展开' }}</span>
      </button>

      <div v-if="showIgnored" class="ignored-list">
        <article v-for="task in ignoredTasks" :key="`ignored-${task.id}`" class="ignored-card">
          <div class="ignored-head">
            <h3>{{ task.title }}</h3>
            <span class="ignored-tag">已忽略</span>
          </div>
          <p>{{ task.content || '该任务已被忽略。' }}</p>
          <div class="ignored-meta">
            <span>{{ task.task_type_label || mapStudyTaskTypeLabel(task.task_type) }}</span>
            <span>{{ task.estimated_minutes || 20 }} 分钟</span>
            <span>忽略于 {{ formatDate(task.ignored_at || task.created_at) }}</span>
          </div>
          <div class="ignored-actions">
            <button class="subtle-btn" :disabled="taskLoading" @click="restoreIgnoredTask(task)">取消忽略</button>
            <button class="danger-btn" :disabled="taskLoading" @click="deleteTask(task)">删除</button>
          </div>
        </article>
      </div>
    </section>

    <section v-if="!tasks.length" class="empty-state">
      <div class="empty-card">
        <h3>当前没有待完成任务</h3>
        <p>继续保持，完成下一场考试后会自动生成新的复习计划。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.study-plan-view {
  --paper: #ecf3ef;
  --ink-900: #16231c;
  --ink-600: #4f6458;
  --line-soft: #cddad2;
  --brand: #0f766e;
  --brand-soft: #dff2ea;
  --warning: #b45309;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100% + 48px);
  width: calc(100% + 32px);
  margin: -24px -16px;
  padding: calc(14px + 24px) 16px calc(18px + env(safe-area-inset-bottom));
  background:
    radial-gradient(125% 46% at 104% -8%, rgba(15, 118, 110, 0.26), rgba(15, 118, 110, 0) 58%),
    radial-gradient(90% 38% at -6% 18%, rgba(37, 99, 235, 0.12), rgba(37, 99, 235, 0) 66%),
    linear-gradient(180deg, #f5faf8 0%, var(--paper) 46%, #e7efea 100%);
}

.hero {
  padding: 18px 16px;
  border: 1px solid #bfd3c8;
  border-radius: 16px;
  background: linear-gradient(165deg, rgba(246, 251, 248, 0.92), rgba(231, 243, 236, 0.92));
  box-shadow: 0 10px 24px rgba(22, 40, 32, 0.07);
  backdrop-filter: blur(6px);
}

.hero-row {
  display: flex;
  justify-content: flex-start;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--brand);
  background: var(--brand-soft);
  border: 1px solid #c8dfd2;
  border-radius: 999px;
  padding: 3px 10px;
}

.hero h1 {
  margin: 10px 0 6px;
  font-size: 31px;
  line-height: 1.06;
  letter-spacing: -0.02em;
  color: var(--ink-900);
}

.hero p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--ink-600);
}

.task-list {
  display: grid;
  gap: 12px;
}

.ai-panel {
  display: grid;
  gap: 10px;
}

.ai-score-card {
  background: linear-gradient(160deg, rgba(243, 251, 247, 0.95) 0%, rgba(227, 243, 234, 0.92) 100%);
  border: 1px solid #c8dfd2;
  border-radius: 14px;
  padding: 14px;
}

.ai-kicker {
  margin: 0;
  font-size: 12px;
  color: #486252;
}

.ai-score-row {
  margin-top: 4px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.ai-score {
  margin: 0;
  font-size: 36px;
  line-height: 1;
  color: #165a42;
  font-weight: 700;
}

.ai-score-unit {
  margin: 0;
  font-size: 14px;
  color: #4f6e5f;
}

.ai-summary {
  margin: 8px 0 0;
  color: #3b5648;
  font-size: 13px;
  line-height: 1.5;
}

.ai-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.metric-cell {
  border: 1px solid #d2e0d8;
  border-radius: 10px;
  background: rgba(246, 250, 248, 0.9);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.metric-cell span {
  font-size: 12px;
  color: #607466;
}

.metric-cell strong {
  font-size: 14px;
  color: #203025;
}

.ai-actions {
  border: 1px solid #ccdfd2;
  border-radius: 12px;
  background: rgba(245, 250, 247, 0.88);
  padding: 12px;
}

.ai-actions h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #1f3025;
}

.ai-actions ul {
  margin: 0;
  padding: 0 0 0 16px;
  display: grid;
  gap: 6px;
  color: #4f6256;
  font-size: 13px;
  line-height: 1.45;
}

.task-card {
  background: linear-gradient(160deg, rgba(250, 253, 251, 0.95), rgba(239, 247, 242, 0.92));
  border: 1px solid #cddbd3;
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 8px 20px rgba(24, 42, 35, 0.06);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.card-head h2 {
  margin: 0;
  font-size: 17px;
  line-height: 1.35;
  color: var(--ink-900);
}

.priority {
  flex-shrink: 0;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1;
  padding: 5px 8px;
  color: #6d4a12;
  background: #fdf2e8;
  border: 1px solid #f3d3b8;
}

.priority.high {
  color: #8c2d10;
  background: #fcebe8;
  border-color: #f2c3bb;
}

.priority.medium {
  color: var(--warning);
  background: #fff4ea;
  border-color: #f8dcc4;
}

.task-desc {
  margin: 0;
  color: var(--ink-600);
  font-size: 14px;
  line-height: 1.6;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: rgba(243, 248, 245, 0.92);
  border: 1px solid #d7e3dc;
  border-radius: 10px;
  padding: 10px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-600);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.subtle-btn {
  border: 1px solid #c9d8cf;
  background: #fff;
  color: #466155;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 12px;
}

.danger-btn {
  border: 1px solid #efc5c5;
  background: #fff5f5;
  color: #b42318;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 12px;
}

.start-btn {
  border: 1px solid #195b43;
  background: linear-gradient(180deg, #1f7a59, #1d6b4f);
  color: #fff;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 14px;
  letter-spacing: 0.01em;
  box-shadow: 0 8px 14px rgba(29, 107, 79, 0.2);
}

.ignored-section {
  display: grid;
  gap: 8px;
}

.ignored-toggle {
  width: 100%;
  border: 1px solid #cedad3;
  background: rgba(243, 249, 246, 0.92);
  color: #335245;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
}

.ignored-list {
  display: grid;
  gap: 8px;
}

.ignored-card {
  border: 1px solid #d2ddd6;
  border-radius: 12px;
  background: rgba(248, 251, 249, 0.9);
  padding: 10px;
}

.ignored-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.ignored-head h3 {
  margin: 0;
  font-size: 14px;
  color: #2f4036;
}

.ignored-tag {
  font-size: 11px;
  color: #4c6358;
  background: #edf3ef;
  border: 1px solid #d2ddd5;
  border-radius: 999px;
  padding: 3px 8px;
}

.ignored-card p {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: #5a6f62;
}

.ignored-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #627568;
}

.ignored-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.empty-state {
  padding-top: 8px;
}

.empty-card {
  background: #fff;
  border: 1px dashed #ccd6cc;
  border-radius: 14px;
  padding: 26px 16px;
  text-align: center;
}

.empty-card h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: var(--ink-900);
}

.empty-card p {
  background: rgba(246, 251, 248, 0.88);
  border: 1px dashed #bfcdc2;
  color: var(--ink-600);
}
</style>


@media (min-width: 768px) {
  .study-plan-view {
    width: calc(100% + 64px);
    margin: -40px -32px;
    min-height: calc(100% + 80px);
    padding: calc(16px + 40px) 32px calc(24px + env(safe-area-inset-bottom));
  }
}
