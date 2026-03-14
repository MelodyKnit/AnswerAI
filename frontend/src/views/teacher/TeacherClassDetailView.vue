<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, UserPlus, Settings2, Download } from 'lucide-vue-next'
import { getClassDetail, getClassStudents } from '@/api/teacher'

const route = useRoute()
const router = useRouter()
const classId = Number(route.params.id)

const classDetail = ref<any>(null)
const students = ref<any[]>([])
const isLoading = ref(true)

const fetchData = async () => {
  try {
    isLoading.value = true
    const [detailRes, studentsRes] = await Promise.all([
      getClassDetail(classId),
      getClassStudents({ class_id: classId })
    ])
    classDetail.value = (detailRes as any).class
    students.value = (studentsRes as any).items || []
  } catch (error) {
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
    </header>

    <div v-if="isLoading" class="loading-state">
      加载中...
    </div>

    <template v-else-if="classDetail">
      <!-- Overview stats -->
      <section class="overview-section">
        <div class="stat-card">
          <div class="stat-label">班级人数</div>
          <div class="stat-value">{{ classDetail.student_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">邀请码</div>
          <div class="stat-value highlight">{{ classDetail.invite_code }}</div>
        </div>
      </section>

      <!-- Students List -->
      <section class="students-section">
        <div class="section-header">
          <h2>学生名单 ({{ students.length }})</h2>
          <div class="actions">
            <button class="icon-button"><Download :size="18" /></button>
            <button class="icon-button"><UserPlus :size="18" /></button>
          </div>
        </div>

        <div class="list-container" v-if="students.length > 0">
          <div v-for="student in students" :key="student.id" class="list-item">
            <div class="student-info">
              <div class="avatar">{{ student.name.charAt(0) }}</div>
              <div class="student-text">
                <div class="name">{{ student.name }}</div>
                <div class="phone" v-if="student.phone">{{ student.phone }}</div>
              </div>
            </div>
            <div class="student-actions">
              <button class="icon-button"><Settings2 :size="16" /></button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          无学生加入
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.view-class-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 8px;
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

.header-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--line);
  color: var(--ink);
  border-radius: 4px;
}

.loading-state, .empty-state {
  display: flex;
  justify-content: center;
  padding: 48px 0;
  color: var(--ink-soft);
}

.overview-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  padding: 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--ink-soft);
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
}

.stat-value.highlight {
  color: var(--accent);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.actions {
  display: flex;
  gap: 12px;
}

.list-container {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #fff;
  display: flex;
  flex-direction: column;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--line);
}

.list-item:last-child {
  border-bottom: none;
}

.student-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  color: var(--accent);
  background: rgba(37, 99, 235, 0.1); /* brand-blue tint */
}

.student-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.name {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.phone {
  font-size: 12px;
  color: var(--ink-soft);
}
</style>


