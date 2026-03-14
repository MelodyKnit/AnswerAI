import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '../layouts/AppShell.vue'
import AuthView from '../views/auth/AuthView.vue'
import HomeView from '../views/marketing/HomeView.vue'
import StudentAiChatView from '../views/student/StudentAiChatView.vue'
import StudentDashboardView from '../views/student/StudentDashboardView.vue'
import StudentExamPrepView from '../views/student/StudentExamPrepView.vue'
import StudentExamsView from '../views/student/StudentExamsView.vue'
import StudentExamSessionView from '../views/student/StudentExamSessionView.vue'
import StudentGrowthView from '../views/student/StudentGrowthView.vue'
import StudentKnowledgeMapView from '../views/student/StudentKnowledgeMapView.vue'
import StudentQuestionDetailView from '../views/student/StudentQuestionDetailView.vue'
import StudentResultsOverviewView from '../views/student/StudentResultsOverviewView.vue'
import StudentStudyPlanView from '../views/student/StudentStudyPlanView.vue'
import DesignSystemView from '../views/system/DesignSystemView.vue'
import NotFoundView from '../views/system/NotFoundView.vue'
import TeacherDashboardView from '../views/teacher/TeacherDashboardView.vue'
import TeacherExamsView from '../views/teacher/TeacherExamsView.vue'
import TeacherExamCreateView from '../views/teacher/TeacherExamCreateView.vue'
import TeacherQuestionsView from '../views/teacher/TeacherQuestionsView.vue'
import TeacherReviewView from '../views/teacher/TeacherReviewView.vue'
import TeacherSettingsView from '../views/teacher/TeacherSettingsView.vue'
import TeacherClassCreateView from '../views/teacher/TeacherClassCreateView.vue'
import TeacherClassesView from '../views/teacher/TeacherClassesView.vue'
import TeacherClassDetailView from '../views/teacher/TeacherClassDetailView.vue'
import TeacherExamDetailView from '../views/teacher/TeacherExamDetailView.vue'

import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: {
        title: 'AI考试答题平台',
        subtitle: '从考试入口延伸到学情诊断、错因解释与教学决策的移动端体验基座。',
        section: 'marketing', hideNav: true },
    },
    {
      path: '/app',
      component: AppShell,
      children: [
        {
          path: 'auth',
          name: 'auth',
          component: AuthView,
          meta: {
            title: '身份登录与注册',
            subtitle: '教师与学生双角色统一入口，保留后续多步骤注册和验证码流程的空间。',
            section: 'auth', hideNav: true },
        },
        {
          path: 'student/dashboard',
          name: 'student-dashboard',
          component: StudentDashboardView,
          meta: {
            title: '学生学习中心',
            subtitle: '围绕最近考试、风险提醒、知识薄弱点与学习计划组织信息层级。',
            section: 'student',
          },
        },
        {
          path: 'student/exams',
          name: 'student-exams',
          component: StudentExamsView,
          meta: {
            title: '考试列表',
            subtitle: '按时间、状态和建议组织待考与历史考试。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/exams/:id/prep',
          name: 'student-exam-prep',
          component: StudentExamPrepView,
          meta: {
            title: '考试准备',
            subtitle: '设备自检、规则确认和答题前提醒。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/exams/:id/session/:sessionId',
          name: 'student-exam-session',
          component: StudentExamSessionView,
          meta: {
            title: '在线答题',
            subtitle: '题号导航、自动保存和 AI 结构提醒。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/results/:id',
          name: 'student-results-overview',
          component: StudentResultsOverviewView,
          meta: {
            title: '考试结果',
            subtitle: '先看总结、风险和下一步动作。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/results/:id/question/:questionId',
          name: 'student-results-question',
          component: StudentQuestionDetailView,
          meta: {
            title: '错题解析',
            subtitle: '聚焦单题失分原因与修正路径。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/ai-chat',
          name: 'student-ai-chat',
          component: StudentAiChatView,
          meta: {
            title: 'AI 错题对话',
            subtitle: '结合当前试题上下文连续追问。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/analytics/knowledge-map',
          name: 'student-knowledge-map',
          component: StudentKnowledgeMapView,
          meta: {
            title: '知识薄弱点地图',
            subtitle: '把考试结果转成可追踪的知识诊断。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/study-plan',
          name: 'student-study-plan',
          component: StudentStudyPlanView,
          meta: {
            title: 'AI 学习计划',
            subtitle: '按优先级把分析结果变成具体任务。',
            section: 'student', hideNav: true },
        },
        {
          path: 'student/growth',
          name: 'student-growth',
          component: StudentGrowthView,
          meta: {
            title: '成长档案',
            subtitle: '查看长期分数、知识点和失误类型变化。',
            section: 'student', hideNav: true },
        },
                {
          path: 'teacher/dashboard',
          name: 'teacher-dashboard',
          component: TeacherDashboardView,
          meta: {
            title: '教师教学工作台',
            subtitle: '让考试管理、班级诊断与教学洞察在手机端也能快速浏览和决策。',
            section: 'teacher',
          },
        },
        {
          path: 'teacher/classes',
          name: 'teacher-classes',
          component: TeacherClassesView,
          meta: { title: '我的班级', section: 'teacher' }
        },
                {
          path: 'teacher/classes/create',
          name: 'teacher-class-create',
          component: TeacherClassCreateView,
          meta: { title: '创建班级', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/classes/:id',
          name: 'teacher-class-detail',
          component: TeacherClassDetailView,
          meta: { title: '班级详情', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/exams',
          name: 'teacher-exams',
          component: TeacherExamsView,
          meta: { title: '考试管理', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/exams/create',
          name: 'teacher-exam-create',
          component: TeacherExamCreateView,
          meta: { title: '创建考试', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/exams/:id',
          name: 'teacher-exam-detail',
          component: TeacherExamDetailView,
          meta: { title: '考试详情', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/questions',
          name: 'teacher-questions',
          component: TeacherQuestionsView,
          meta: { title: '题库管理', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/review',
          name: 'teacher-review',
          component: TeacherReviewView,
          meta: { title: '阅卷任务', section: 'teacher' , hideNav: true }
        },
        {
          path: 'teacher/settings',
          name: 'teacher-settings',
          component: TeacherSettingsView,
          meta: { title: '设置', section: 'teacher' }
        },
          {
            path: 'system/foundation',
          name: 'design-foundation',
          component: DesignSystemView,
          meta: {
            title: '设计与页面基础',
            subtitle: '沉淀后续页面开发的视觉语言、布局骨架与模块切分规范。',
            section: 'system', hideNav: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
      meta: {
        title: '页面不存在',
        subtitle: '当前访问的页面未配置，可返回首页或进入基础框架页继续开发。',
        section: 'system', hideNav: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Load user data if token exists but user doesn't
  if (authStore.token && !authStore.user) {
    await authStore.fetchUser()
  }

  // Define public routes
  const publicRoutes = ['home', 'auth', 'not-found', 'design-foundation']

  if (!publicRoutes.includes(to.name as string) && !authStore.token) {
    next({ name: 'auth' })
  } else {
    next()
  }
})

export default router


