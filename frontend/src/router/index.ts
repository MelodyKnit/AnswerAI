import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import AppShell from '../layouts/AppShell.vue'
import AuthView from '../views/auth/AuthView.vue'
import HomeView from '../views/marketing/HomeView.vue'
import StudentAiChatView from '../views/student/StudentAiChatView.vue'
import StudentDashboardView from '../views/student/StudentDashboardView.vue'
import StudentExamPrepView from '../views/student/StudentExamPrepView.vue'
import StudentExamsView from '../views/student/StudentExamsView.vue'
import StudentExamSessionView from '../views/student/StudentExamSessionView.vue'
import StudentGrowthView from '../views/student/StudentGrowthView.vue'
import StudentProfileView from '../views/student/StudentProfileView.vue'
import StudentSettingsProfileView from '../views/student/StudentSettingsProfileView.vue'
import StudentKnowledgeMapView from '../views/student/StudentKnowledgeMapView.vue'
import StudentQuestionDetailView from '../views/student/StudentQuestionDetailView.vue'
import StudentResultsOverviewView from '../views/student/StudentResultsOverviewView.vue'
import StudentStudyPlanView from '../views/student/StudentStudyPlanView.vue'
import StudentStudyTaskSessionView from '../views/student/StudentStudyTaskSessionView.vue'
import DesignSystemView from '../views/system/DesignSystemView.vue'
import NotFoundView from '../views/system/NotFoundView.vue'
import TeacherDashboardView from '../views/teacher/TeacherDashboardView.vue'
import TeacherExamsView from '../views/teacher/TeacherExamsView.vue'
import TeacherExamCreateView from '../views/teacher/TeacherExamCreateView.vue'
import TeacherQuestionsView from '../views/teacher/TeacherQuestionsView.vue'
import TeacherQuestionPreviewView from '../views/teacher/TeacherQuestionPreviewView.vue'
import TeacherAnalyticsView from '../views/teacher/TeacherAnalyticsView.vue'
import TeacherReviewView from '../views/teacher/TeacherReviewView.vue'
import TeacherRetakeRequestsView from '../views/teacher/TeacherRetakeRequestsView.vue'
import TeacherSettingsView from '../views/teacher/TeacherSettingsView.vue'
import TeacherSettingsProfileView from '../views/teacher/TeacherSettingsProfileView.vue'
import TeacherSettingsNotificationsView from '../views/teacher/TeacherSettingsNotificationsView.vue'
import TeacherSettingsSecurityView from '../views/teacher/TeacherSettingsSecurityView.vue'
import TeacherFeedbackManageView from '../views/teacher/TeacherFeedbackManageView.vue'
import TeacherClassAnalysisView from '../views/teacher/TeacherClassAnalysisView.vue'
import TeacherClassCreateView from '../views/teacher/TeacherClassCreateView.vue'
import TeacherClassDetailView from '../views/teacher/TeacherClassDetailView.vue'
import TeacherClassEditView from '../views/teacher/TeacherClassEditView.vue'
import TeacherClassesView from '../views/teacher/TeacherClassesView.vue'
import TeacherExamDetailView from '../views/teacher/TeacherExamDetailView.vue'
import TeacherStudentProfileView from '../views/teacher/TeacherStudentProfileView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/auth',
      name: 'auth',
      component: AuthView,
      meta: { requiresGuest: true },
    },
    {
      path: '/app',
      component: AppShell,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: () => {
            const auth = useAuthStore()
            return auth.user?.role === 'teacher' ? '/app/teacher/dashboard' : '/app/student/dashboard'
          },
        },
        {
          path: 'student/dashboard',
          name: 'student-dashboard',
          component: StudentDashboardView,
          meta: { title: '学生学习中心', section: 'student' }
        },
        {
          path: 'student/exams',
          name: 'student-exams',
          component: StudentExamsView,
          meta: { title: '考试列表', section: 'student', hideNav: true }
        },
        {
          path: 'student/exams/:id/prep',
          name: 'student-exam-prep',
          component: StudentExamPrepView,
          meta: { title: '考试准备', section: 'student', hideNav: true }
        },
        {
          path: 'student/exams/:id/session/:sessionId',
          name: 'student-exam-session',
          component: StudentExamSessionView,
          meta: { title: '在线答题', section: 'student', hideNav: true }
        },
        {
          path: 'student/results/:id',
          name: 'student-results-overview',
          component: StudentResultsOverviewView,
          meta: { title: '考试结果', section: 'student', hideNav: true }
        },
        {
          path: 'student/results/:id/question/:questionId',
          name: 'student-results-question',
          component: StudentQuestionDetailView,
          meta: { title: '错题解析', section: 'student', hideNav: true }
        },
        {
          path: 'student/ai-chat',
          name: 'student-ai-chat',
          component: StudentAiChatView,
          meta: { title: 'AI 错题对话', section: 'student', hideNav: true }
        },
        {
          path: 'student/analytics/knowledge-map',
          name: 'student-knowledge-map',
          component: StudentKnowledgeMapView,
          meta: { title: '知识薄弱点地图', section: 'student', hideNav: true }
        },
        {
          path: 'student/study-plan',
          name: 'student-study-plan',
          component: StudentStudyPlanView,
          meta: { title: 'AI 学习计划', section: 'student' }
        },
        {
          path: 'student/study-plan/tasks/:taskId',
          name: 'student-study-task-session',
          component: StudentStudyTaskSessionView,
          meta: { title: '任务复习', section: 'student', hideNav: true }
        },
        {
          path: 'student/growth',
          name: 'student-growth',
          component: StudentGrowthView,
          meta: { title: '成长档案', section: 'student' }
        },
          {
            path: 'student/profile',
            name: 'student-profile',
            component: StudentProfileView,
            meta: { title: '我的档案', section: 'student' }
          },
        {
          path: 'student/settings/profile',
          name: 'student-settings-profile',
          component: StudentSettingsProfileView,
          meta: { title: '个人资料', section: 'student', hideNav: true }
        },
        {
          path: 'teacher/dashboard',
          name: 'teacher-dashboard',
          component: TeacherDashboardView,
          meta: { title: '教师教学工作台', section: 'teacher' }
        },
        {
          path: 'teacher/classes',
          name: 'teacher-classes',
          component: TeacherClassesView,
          meta: { title: '班级管理', section: 'teacher' }
        },
        {
          path: 'teacher/classes/create',
          name: 'teacher-class-create',
          component: TeacherClassCreateView,
          meta: { title: '创建班级', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/classes/:id/analysis',
          name: 'teacher-class-analysis',
          component: TeacherClassAnalysisView,
          meta: { title: '班级学习分析', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/classes/:id/edit',
          name: 'teacher-class-edit',
          component: TeacherClassEditView,
          meta: { title: '修改班级', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/classes/:id',
          name: 'teacher-class-detail',
          component: TeacherClassDetailView,
          meta: { title: '班级详情', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/students/:id',
          name: 'teacher-student-profile',
          component: TeacherStudentProfileView,
          meta: { title: '学生学习画像', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/exams',
          name: 'teacher-exams',
          component: TeacherExamsView,
          meta: { title: '考试管理', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/exams/create',
          name: 'teacher-exam-create',
          component: TeacherExamCreateView,
          meta: { title: '组织测验', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/exams/:id',
          name: 'teacher-exam-detail',
          component: TeacherExamDetailView,
          meta: { title: '测验详情与分析', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/review',
          name: 'teacher-review-tasks',
          component: TeacherReviewView,
          meta: { title: '阅卷任务', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/retake-requests',
          name: 'teacher-retake-requests',
          component: TeacherRetakeRequestsView,
          meta: { title: '重考审批', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/analytics',
          name: 'teacher-analytics',
          component: TeacherAnalyticsView,
          meta: { title: '学情分析', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/exams/:id/review',
          name: 'teacher-review',
          component: TeacherReviewView,
          meta: { title: '人工复核', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/questions',
          name: 'teacher-questions',
          component: TeacherQuestionsView,
          meta: { title: '试题库', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/questions/:id/preview',
          name: 'teacher-question-preview',
          component: TeacherQuestionPreviewView,
          meta: { title: '题目预览', section: 'teacher', hideNav: true }
        },
        {
          path: 'teacher/settings',
          name: 'teacher-settings',
          component: TeacherSettingsView,
          meta: { title: '设置', section: 'teacher' },
          children: [
            {
              path: 'profile',
              name: 'teacher-settings-profile',
              component: TeacherSettingsProfileView,
            },
            {
              path: 'notifications',
              name: 'teacher-settings-notifications',
              component: TeacherSettingsNotificationsView,
            },
            {
              path: 'security',
              name: 'teacher-settings-security',
              component: TeacherSettingsSecurityView,
            },
          ],
        },
        {
          path: 'teacher/feedback',
          name: 'teacher-feedback-manage',
          component: TeacherFeedbackManageView,
          meta: { title: '反馈管理', section: 'teacher', hideNav: true }
        },
      ],
    },
    {
      path: '/design',
      name: 'design-system',
      component: DesignSystemView,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (authStore.token && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      // handled by store/http interceptors
    }
  }

  if (to.meta.requiresAuth && !authStore.token) {
    next({ name: 'auth' })
  } else if (to.meta.requiresAuth && to.meta.section === 'teacher' && authStore.user?.role !== 'teacher') {
    next('/app/student/dashboard')
  } else if (to.meta.requiresAuth && to.meta.section === 'student' && authStore.user?.role !== 'student') {
    next('/app/teacher/dashboard')
  } else if (to.meta.requiresGuest && authStore.token) {
    const defaultRoute = authStore.user?.role === 'teacher' ? '/app/teacher/dashboard' : '/app/student/dashboard'
    next(defaultRoute)
  } else {
    next()
  }
})

export default router

