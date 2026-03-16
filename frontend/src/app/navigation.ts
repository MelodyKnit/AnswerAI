import {
  Bot,
  ChartColumnBig,
  ClipboardList,
  BookOpenText,
  GraduationCap,
  House,
  LayoutDashboard,
  LibraryBig,
  PanelsTopLeft,
  type LucideIcon,
} from 'lucide-vue-next'

export interface NavigationItem {
  label: string
  to: string
  matchPrefix: string
  icon: LucideIcon
}

export const primaryNavigation: NavigationItem[] = [
  {
    label: '首页',
    to: '/',
    matchPrefix: '/',
    icon: House,
  },
  {
    label: '登录',
    to: '/auth',
    matchPrefix: '/auth',
    icon: PanelsTopLeft,
  },
  {
    label: '学生',
    to: '/app/student/dashboard',
    matchPrefix: '/app/student',
    icon: GraduationCap,
  },
  {
    label: '教师',
    to: '/app/teacher/dashboard',
    matchPrefix: '/app/teacher',
    icon: LayoutDashboard,
  },
  {
    label: '基础',
    to: '/app/system/foundation',
    matchPrefix: '/app/system',
    icon: BookOpenText,
  },
]

export const studentNavigation: NavigationItem[] = [
  {
    label: '概览',
    to: '/app/student/dashboard',
    matchPrefix: '/app/student/dashboard',
    icon: House,
  },
  {
    label: '考试',
    to: '/app/student/exams',
    matchPrefix: '/app/student/exams',
    icon: ClipboardList,
  },
  {
    label: '分析',
    to: '/app/student/results/overview',
    matchPrefix: '/app/student/results',
    icon: ChartColumnBig,
  },
  {
    label: '计划',
    to: '/app/student/study-plan',
    matchPrefix: '/app/student/study-plan',
    icon: LibraryBig,
  },
]

export const studentQuickLinks: NavigationItem[] = [
  {
    label: '考前',
    to: '/app/student/exams/prep',
    matchPrefix: '/app/student/exams/prep',
    icon: ClipboardList,
  },
  {
    label: '答题',
    to: '/app/student/exams/session',
    matchPrefix: '/app/student/exams/session',
    icon: BookOpenText,
  },
  {
    label: '错题',
    to: '/app/student/results/question',
    matchPrefix: '/app/student/results/question',
    icon: ChartColumnBig,
  },
  {
    label: 'AI辅导',
    to: '/app/student/ai-chat',
    matchPrefix: '/app/student/ai-chat',
    icon: Bot,
  },
]

export const sectionLabels: Record<string, string> = {
  marketing: '产品首页',
  auth: '账户入口',
  student: '学生端',
  teacher: '教师端',
  system: '基础框架',
}