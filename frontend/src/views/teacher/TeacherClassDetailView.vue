<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, UserPlus, Download, X, Loader2, Trash2, BrainCircuit, Search } from 'lucide-vue-next'
import { getClassDetail, getClassStudents, inviteStudentToClass, removeStudentFromClass, getTeacherDashboardOverview } from '@/api/teacher'

const route = useRoute()
const router = useRouter()
const classId = Number(route.params.id)

const classDetail = ref<any>(null)
const students = ref<any[]>([])
const isLoading = ref(true)
const keyword = ref('')
const riskFilter = ref<'all' | 'high' | 'medium' | 'low' | 'unknown'>('all')

const showInviteModal = ref(false)
const inviteStudentIdInput = ref('')
const inviteLoading = ref(false)
const actionMessage = ref('')

const riskMap = ref<Record<number, 'high' | 'medium' | 'low'>>({})

const normalizeRiskLevel = (risk: unknown): 'high' | 'medium' | 'low' | 'unknown' => {
  const value = String(risk || '').trim().toLowerCase()
  if (value === 'high') return 'high'
  if (value === 'medium') return 'medium'
  if (value === 'low') return 'low'
  return 'unknown'
}

const getRiskLabel = (risk: 'high' | 'medium' | 'low' | 'unknown') => {
  if (risk === 'high') return '学习高危'
  if (risk === 'medium') return '学习预警'
  if (risk === 'low') return '持续关注'
  return '待评估'
}

const mergedStudents = computed(() => {
  return students.value.map((student) => {
    const mappedRisk = riskMap.value[Number(student.id)]
    const risk_level = normalizeRiskLevel(mappedRisk ?? student.risk_level)
    return {
      ...student,
      risk_level,
    }
  })
})

const filteredStudents = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return mergedStudents.value.filter((student) => {
    const riskOk = riskFilter.value === 'all' ? true : student.risk_level === riskFilter.value
    if (!riskOk) return false

    if (!query) return true

    const fields = [student.name, student.email, student.phone, String(student.id ?? '')]
      .map((item) => String(item || '').toLowerCase())
    return fields.some((item) => item.includes(query))
  }).sort((a, b) => {
    const rank = { high: 0, medium: 1, low: 2, unknown: 3 }
    return rank[a.risk_level as keyof typeof rank] - rank[b.risk_level as keyof typeof rank]
  })
})

const studentCountText = computed(() => `${filteredStudents.value.length} / ${students.value.length}`)

const fetchData = async () => {
  if (!Number.isFinite(classId) || classId <= 0) {
    actionMessage.value = '班级ID无效，已返回班级列表'
    router.replace('/app/teacher/classes')
    return
  }

  try {
    isLoading.value = true
    const [detailRes, studentsRes, overviewRes] = await Promise.all([
      getClassDetail(classId),
      getClassStudents({ class_id: classId, page_size: 100 }),
      getTeacherDashboardOverview(),
    ])
    classDetail.value = (detailRes as any).class
    students.value = (studentsRes as any).items || []

    const riskStudents = ((overviewRes as any)?.risk_students || []) as Array<any>
    const map: Record<number, 'high' | 'medium' | 'low'> = {}
    for (const item of riskStudents) {
      const sid = Number(item?.student_id)
      const risk = normalizeRiskLevel(item?.risk_level)
      if (Number.isFinite(sid) && risk !== 'unknown') {
        map[sid] = risk
      }
    }
    riskMap.value = map
  } catch (error: any) {
    actionMessage.value = error?.message || '加载班级详情失败'
    console.error('Failed to fetch class details', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchData()
})

const goBack = () => {
  router.back()
}

const goStudentProfile = (studentId: number) => {
  router.push(`/app/teacher/students/${studentId}`)
}

const goClassAnalysis = () => {
  router.push(`/app/teacher/classes/${classId}/analysis`)
}

const exportStudentsAsCsv = () => {
  actionMessage.value = ''

  if (!students.value.length) {
    actionMessage.value = '当前没有学生可导出'
    return
  }

  const headers = ['student_id', 'name', 'email', 'phone', 'grade_name']
  const rows = students.value.map((s) => [s.id ?? '', s.name ?? '', s.email ?? '', s.phone ?? '', s.grade_name ?? ''])

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `${classDetail.value?.name || 'class'}_students.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
  actionMessage.value = '学生名单已导出为 CSV'
}

const copyInviteCode = async () => {
  actionMessage.value = ''
  const code = String(classDetail.value?.invite_code || '').trim()
  if (!code) {
    actionMessage.value = '邀请码为空，无法复制'
    return
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(code)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = code
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(textarea)
      if (!ok) throw new Error('copy failed')
    }

    actionMessage.value = `邀请码 ${code} 已复制`
  } catch {
    actionMessage.value = '复制失败，请手动长按复制'
  }
}

const openInviteModal = () => {
  inviteStudentIdInput.value = ''
  actionMessage.value = ''
  showInviteModal.value = true
}

const closeInviteModal = () => {
  showInviteModal.value = false
}

const submitInvite = async () => {
  actionMessage.value = ''
  const studentId = Number(inviteStudentIdInput.value.trim())

  if (!Number.isInteger(studentId) || studentId <= 0) {
    actionMessage.value = '请输入有效的学生唯一 ID（正整数）'
    return
  }

  try {
    inviteLoading.value = true
    await inviteStudentToClass({ class_id: classId, student_id: studentId })
    actionMessage.value = `已邀请学生 #${studentId} 加入班级`
    closeInviteModal()
    await fetchData()
  } catch (error: any) {
    actionMessage.value = error?.message || '邀请失败，请检查学生ID是否正确'
  } finally {
    inviteLoading.value = false
  }
}

const removeStudent = async (student: any) => {
  actionMessage.value = ''
  const confirmed = window.confirm(`确认将 ${student.name} 移出班级吗？`)
  if (!confirmed) return

  try {
    await removeStudentFromClass({ class_id: classId, student_id: Number(student.id) })
    actionMessage.value = `已将 ${student.name} 移出班级`
    await fetchData()
  } catch (error: any) {
    actionMessage.value = error?.message || '移除失败，请稍后重试'
  }
}
</script>

<template>
  <div class="view-class-detail">
    <header class="detail-header">
      <button class="icon-button" @click="goBack" aria-label="返回">
        <ArrowLeft :size="24" />
      </button>
      <div v-if="classDetail" class="header-content">
        <h1 class="page-title">{{ classDetail.name }}</h1>
        <div class="tags">
          <span class="tag">{{ classDetail.grade_name }}</span>
          <span class="tag">{{ classDetail.subject }}</span>
        </div>
      </div>
      <button v-if="classDetail" class="analysis-header-button" @click="goClassAnalysis">
        学习分析
      </button>
    </header>

    <div v-if="isLoading" class="loading-state">加载中...</div>

    <template v-else-if="classDetail">
      <section class="overview-section">
        <div class="stat-card">
          <div class="stat-label">班级人数</div>
          <div class="stat-value">{{ classDetail.student_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">邀请码</div>
          <button class="stat-value highlight invite-copy-btn" @click="copyInviteCode" title="点击复制邀请码">
            {{ classDetail.invite_code }}
          </button>
        </div>
        <button class="analysis-entry-card" @click="goClassAnalysis">
          <div class="analysis-entry-copy">
            <span class="analysis-entry-kicker">AI 班级学习分析</span>
            <strong>查看班级学情趋势、风险分层与干预建议</strong>
            <span class="analysis-entry-meta">单独页面展示图表、重点学生和针对性教学动作</span>
          </div>
          <span class="analysis-entry-arrow">进入</span>
        </button>
      </section>

      <section class="students-section">
        <div class="section-header">
          <h2>学生名单 ({{ studentCountText }})</h2>
          <div class="actions">
            <button class="icon-button action-icon" @click="exportStudentsAsCsv" aria-label="导出 CSV">
              <Download :size="18" />
            </button>
            <button class="icon-button action-icon" @click="openInviteModal" aria-label="邀请学生">
              <UserPlus :size="18" />
            </button>
          </div>
        </div>

        <p v-if="actionMessage" class="action-message">{{ actionMessage }}</p>

        <div class="filters">
          <label class="search-wrap" aria-label="搜索学生">
            <Search :size="14" />
            <input
              v-model="keyword"
              type="text"
              placeholder="搜索姓名/ID/手机号/邮箱"
              class="search-input"
            />
          </label>

          <select v-model="riskFilter" class="risk-select" aria-label="风险筛选">
            <option value="all">全部风险</option>
            <option value="high">仅看高危</option>
            <option value="medium">仅看预警</option>
            <option value="low">仅看关注</option>
            <option value="unknown">仅看待评估</option>
          </select>
        </div>

        <div class="list-container" v-if="filteredStudents.length > 0">
          <div
            v-for="student in filteredStudents"
            :key="student.id"
            class="list-item"
            :class="[`risk-${student.risk_level}`]"
          >
            <span class="risk-ribbon" :class="[`risk-${student.risk_level}`]">{{ getRiskLabel(student.risk_level) }}</span>
            <div class="student-info">
              <div class="avatar">{{ student.name?.charAt(0) || '学' }}</div>
              <div class="student-text">
                <div class="name">{{ student.name }}</div>
                <div class="meta">ID: {{ student.id }}</div>
                <div class="phone" v-if="student.phone">{{ student.phone }}</div>
              </div>
            </div>
            <div class="row-actions">
              <button class="portrait-button" @click="goStudentProfile(Number(student.id))">
                <BrainCircuit :size="14" />
                <span>学习画像</span>
              </button>
              <button class="icon-button delete-icon" @click="removeStudent(student)" aria-label="移除学生">
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">没有符合筛选条件的学生</div>
      </section>
    </template>

    <div v-if="showInviteModal" class="modal-mask" @click.self="closeInviteModal">
      <div class="modal-card">
        <div class="modal-head">
          <h3>邀请学生加入班级</h3>
          <button class="icon-button" @click="closeInviteModal" aria-label="关闭">
            <X :size="16" />
          </button>
        </div>

        <label class="field">
          <span>学生唯一 ID</span>
          <input
            v-model="inviteStudentIdInput"
            type="text"
            placeholder="例如 1024"
            inputmode="numeric"
          />
        </label>

        <div class="modal-actions">
          <button class="btn btn-muted" @click="closeInviteModal">取消</button>
          <button class="btn btn-primary" :disabled="inviteLoading" @click="submitInvite">
            <Loader2 v-if="inviteLoading" :size="14" class="spin" />
            <span>{{ inviteLoading ? '邀请中...' : '确认邀请' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-class-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 2px;
}

.analysis-header-button {
  margin-left: auto;
  border: 1px solid rgba(60, 106, 88, 0.22);
  background: linear-gradient(135deg, #f8fcf9 0%, #edf6f1 100%);
  color: #33584a;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
}

.icon-button {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  transition: color 0.2s;
}

.icon-button:hover {
  color: var(--ink);
}

.action-icon {
  border: 1px solid var(--line);
  border-radius: 8px;
  width: 32px;
  height: 32px;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  font-size: 32px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin: 0;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--line);
  color: var(--ink);
  border-radius: 6px;
}

.loading-state,
.empty-state {
  display: flex;
  justify-content: center;
  padding: 48px 0;
  color: var(--ink-soft);
}

.overview-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.analysis-entry-card {
  grid-column: 1 / -1;
  border: 1px solid rgba(60, 106, 88, 0.16);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #fbfdfb 0%, #f0f7f3 100%);
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}

.analysis-entry-copy {
  display: grid;
  gap: 4px;
}

.analysis-entry-kicker {
  font-size: 12px;
  color: #5b7d70;
}

.analysis-entry-copy strong {
  color: var(--ink);
}

.analysis-entry-meta,
.analysis-entry-arrow {
  font-size: 12px;
  color: var(--ink-soft);
}

.stat-card {
  padding: 12px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  color: var(--ink-soft);
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.25;
  word-break: break-all;
}

.stat-value.highlight {
  color: #0f766e;
  font-size: 17px;
  letter-spacing: 0.02em;
}

.invite-copy-btn {
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.invite-copy-btn:active {
  opacity: 0.72;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}

.actions {
  display: flex;
  gap: 8px;
}

.action-message {
  margin: 0 0 10px;
  font-size: 12px;
  color: #0f766e;
}

.filters {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 8px;
  margin: 0 0 10px;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 10px;
  background: #fff;
  color: var(--ink-soft);
}

.search-input {
  width: 100%;
  border: none;
  outline: none;
  height: 36px;
  font-size: 13px;
  color: var(--ink);
  background: transparent;
}

.risk-select {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 10px;
  height: 36px;
  font-size: 13px;
  color: var(--ink);
  background: #fff;
}

.list-container {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
  display: flex;
  flex-direction: column;
}

.list-item {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 12px 12px;
  border-bottom: 1px solid var(--line);
}

.list-item:last-child {
  border-bottom: none;
}

.risk-ribbon {
  position: absolute;
  top: 0;
  left: 0;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  padding: 5px 10px 4px 8px;
  border-bottom-right-radius: 8px;
  letter-spacing: 0.02em;
}

.risk-ribbon.risk-high {
  color: #fff;
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
}

.risk-ribbon.risk-medium {
  color: #7c2d12;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
}

.risk-ribbon.risk-low {
  color: #075985;
  background: linear-gradient(135deg, #bfdbfe 0%, #93c5fd 100%);
}

.risk-ribbon.risk-unknown {
  color: #334155;
  background: #e2e8f0;
}

.list-item.risk-high {
  box-shadow: inset 3px 0 0 #ef4444;
}

.list-item.risk-medium {
  box-shadow: inset 3px 0 0 #f59e0b;
}

.list-item.risk-low {
  box-shadow: inset 3px 0 0 #60a5fa;
}

.student-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  background: rgba(37, 99, 235, 0.1);
}

.student-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}

.meta,
.phone {
  font-size: 11px;
  color: var(--ink-soft);
}

.delete-icon {
  color: #ef4444;
  border: 1px solid #fee2e2;
  border-radius: 8px;
  width: 30px;
  height: 30px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.portrait-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #cbdff6;
  background: linear-gradient(135deg, #eef7ff 0%, #f7fbff 100%);
  color: #1d4ed8;
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 600;
}

.portrait-button:hover {
  border-color: #93c5fd;
  background: linear-gradient(135deg, #e2f0ff 0%, #f0f7ff 100%);
}

.delete-icon:hover {
  color: #dc2626;
  background: #fff1f2;
}

@media (max-width: 768px) {
  .page-title {
    font-size: 28px;
  }

  .stat-value {
    font-size: 20px;
  }

  .stat-value.highlight {
    font-size: 20px;
  }

  .list-item {
    align-items: center;
  }

  .filters {
    grid-template-columns: 1fr;
  }
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}

.modal-card {
  width: min(460px, 100%);
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--line);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-head h3 {
  margin: 0;
  font-size: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 12px;
  color: var(--ink-soft);
}

.field input {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 14px;
  outline: none;
}

.field input:focus {
  border-color: #0f766e;
  box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.12);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-muted {
  background: #f1f5f9;
  color: #334155;
}

.btn-primary {
  background: #0f766e;
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.7;
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
