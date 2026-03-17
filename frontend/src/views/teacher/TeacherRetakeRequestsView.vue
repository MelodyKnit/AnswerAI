<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CheckCircle2, RotateCcw, XCircle } from 'lucide-vue-next'
import { useUiDialog } from '@/composables/useUiDialog'
import { getRetakeRequests, reviewRetakeRequest } from '@/api/teacher'

const requests = ref<any[]>([])
const isLoading = ref(true)
const activeStatus = ref<'pending' | 'all'>('pending')
const actionLoadingId = ref<number | null>(null)
const ui = useUiDialog()

const fetchRequests = async () => {
  try {
    isLoading.value = true
    const params = activeStatus.value === 'all' ? { page_size: 100 } : { status: activeStatus.value, page_size: 100 }
    const res = await getRetakeRequests(params)
    requests.value = (res as any).items || []
  } catch (error) {
    console.error('Failed to fetch retake requests', error)
  } finally {
    isLoading.value = false
  }
}

const switchStatus = (status: 'pending' | 'all') => {
  if (activeStatus.value === status) return
  activeStatus.value = status
  fetchRequests()
}

const handleAction = async (item: any, action: 'approve' | 'reject') => {
  const comment = (await ui.prompt(action === 'approve' ? '通过重考申请，可填写备注（可选）' : '驳回原因（可选）', {
    title: action === 'approve' ? '批准重考' : '驳回申请',
    confirmText: action === 'approve' ? '确认批准' : '确认驳回',
    defaultValue: '',
  })) || undefined
  try {
    actionLoadingId.value = Number(item.request_id)
    await reviewRetakeRequest({ request_id: Number(item.request_id), action, comment })
    await fetchRequests()
  } catch (error: any) {
    await ui.alert(error?.message || '操作失败，请稍后重试', { tone: 'error' })
  } finally {
    actionLoadingId.value = null
  }
}

const formatDateTime = (value?: string) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const statusText = (status?: string) => {
  if (status === 'approved') return '已批准'
  if (status === 'rejected') return '已驳回'
  if (status === 'consumed') return '已使用'
  return '待审批'
}

onMounted(() => {
  fetchRequests()
})
</script>

<template>
  <div class="retake-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">重考审批</h1>
      </div>
    </header>

    <div class="filter-tabs">
      <button class="tab-btn" :class="{ active: activeStatus === 'pending' }" @click="switchStatus('pending')">待审批</button>
      <button class="tab-btn" :class="{ active: activeStatus === 'all' }" @click="switchStatus('all')">全部申请</button>
    </div>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <div v-else-if="requests.length === 0" class="empty-state">
      <CheckCircle2 :size="48" class="empty-icon" />
      <p>当前没有重考申请。</p>
    </div>

    <div v-else class="request-list">
      <article v-for="item in requests" :key="item.request_id" class="request-card">
        <div class="request-head">
          <div>
            <h2>{{ item.student_name }} · {{ item.exam_title }}</h2>
            <p>申请时间：{{ formatDateTime(item.created_at) }}</p>
          </div>
          <span class="status-pill" :class="`status-${item.status || 'pending'}`">{{ statusText(item.status) }}</span>
        </div>

        <div class="reason-box">
          <span class="reason-label">申请理由</span>
          <p>{{ item.reason || '未填写' }}</p>
        </div>

        <div v-if="item.comment" class="comment-box">
          <span class="reason-label">审批备注</span>
          <p>{{ item.comment }}</p>
        </div>

        <div v-if="item.status === 'pending'" class="request-actions">
          <button class="btn-reject" :disabled="actionLoadingId === item.request_id" @click="handleAction(item, 'reject')">
            <XCircle :size="16" />
            驳回
          </button>
          <button class="btn-approve" :disabled="actionLoadingId === item.request_id" @click="handleAction(item, 'approve')">
            <RotateCcw :size="16" />
            批准重考
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.retake-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn,
.btn-ghost,
.btn-approve,
.btn-reject {
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
}

.tab-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  padding: 8px 12px;
}

.tab-btn.active {
  background: #eef6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.btn-ghost {
  border: 1px solid #dbe3ef;
  background: #fff;
  color: #475569;
  padding: 8px 12px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 220px;
  color: var(--ink-soft);
}

.empty-icon {
  color: #0f766e;
}

.request-list {
  display: grid;
  gap: 12px;
}

.request-card {
  border: 1px solid #dce5ef;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff, #fbfdff);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.request-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.request-head h2 {
  margin: 0;
  font-size: 16px;
  color: var(--ink);
}

.request-head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.status-pill {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}

.status-pending {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.12);
}

.status-approved,
.status-consumed {
  color: #047857;
  background: #ecfdf5;
}

.status-rejected {
  color: #b91c1c;
  background: #fef2f2;
}

.reason-box,
.comment-box {
  border: 1px solid #edf2f7;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.reason-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.reason-box p,
.comment-box p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.request-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-approve,
.btn-reject {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 12px;
}

.btn-approve {
  border: 1px solid #0f766e;
  background: #0f766e;
  color: #fff;
}

.btn-reject {
  border: 1px solid #fecaca;
  background: #fff5f5;
  color: #b91c1c;
}
</style>