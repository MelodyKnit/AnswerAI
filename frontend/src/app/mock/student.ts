export interface StudentExam {
  id: number
  title: string
  subject: string
  timeLabel: string
  duration: string
  questionCount: number
  totalScore: number
  status: 'upcoming' | 'ongoing' | 'finished'
  hint: string
}

export const upcomingExams: StudentExam[] = [
  {
    id: 1001,
    title: '高一数学周测',
    subject: '数学',
    timeLabel: '今天 19:00 截止',
    duration: '90 分钟',
    questionCount: 20,
    totalScore: 100,
    status: 'ongoing',
    hint: '重点覆盖函数、概率统计，建议先看错题提醒。',
  },
  {
    id: 1002,
    title: '物理阶段小测',
    subject: '物理',
    timeLabel: '明天 09:30 开始',
    duration: '45 分钟',
    questionCount: 12,
    totalScore: 60,
    status: 'upcoming',
    hint: '涉及受力分析与图像题，建议先做 10 分钟热身。',
  },
  {
    id: 1003,
    title: '英语阅读诊断',
    subject: '英语',
    timeLabel: '已结束',
    duration: '30 分钟',
    questionCount: 8,
    totalScore: 40,
    status: 'finished',
    hint: '本场已生成结果分析，可直接查看薄弱环节。',
  },
]

export const dashboardMetrics = [
  { label: '待考', value: '02', note: '其中 1 场今天截止' },
  { label: '最近得分', value: '78', note: '超过班均 6 分' },
  { label: '风险点', value: '03', note: '函数应用题反复失分' },
  { label: '计划完成', value: '64%', note: '本周已完成 7 项任务' },
]

export const dashboardSignals = [
  {
    title: '这次不是不会做，而是建模启动慢。',
    copy: '你的失分集中在“读题后前两步”，先解决题意转译，分数会提升得更快。',
    tone: 'accent',
  },
  {
    title: '本周最该补的知识点是函数应用。',
    copy: '近三次考试同类题目重复失分，建议先完成 AI 追问和 3 道同类练习。',
    tone: 'neutral',
  },
]

export const resultSummary = {
  score: 78,
  ranking: 8,
  correctRate: '74%',
  duration: '76 分钟',
  highlight: '基础题稳定，综合题前两步判断失误较多。',
}

export const wrongQuestionInsight = {
  title: '第 14 题函数建模',
  studentAnswer: '将题目条件直接代入，忽略了区间限制。',
  aiReason: '错误不在计算，而在第一步没有先界定变量关系，导致后续公式全部偏离。',
  fix: '先用一句话写出“未知量是什么、约束是什么”，再列式。',
}

export const aiChatMessages = [
  {
    role: 'assistant',
    text: '你这道题的问题不在最后算错，而在前面没有先把“增长量”和“总量”分开。',
  },
  {
    role: 'user',
    text: '为什么我会把这两个量混在一起？',
  },
  {
    role: 'assistant',
    text: '因为题目用自然语言描述条件，你直接跳到了公式。先把条件翻成两句结构化描述，会稳很多。',
  },
]

export const knowledgeMap = [
  { label: '函数性质', value: 82, state: 'stable' },
  { label: '函数建模', value: 43, state: 'risk' },
  { label: '概率统计', value: 58, state: 'watch' },
  { label: '综合应用', value: 61, state: 'watch' },
]

export const studyPlan = [
  {
    title: '15 分钟错题回放',
    meta: '今天 18:30 前',
    copy: '先复盘第 14 题和第 18 题，把错因写成两条自己的提醒。',
  },
  {
    title: '函数建模练习 3 题',
    meta: '预计 20 分钟',
    copy: '完成后由 AI 生成针对性点评，重点看开头两步。',
  },
  {
    title: '睡前 10 分钟复盘',
    meta: '今晚 22:00',
    copy: '确认今天是否还在重复“先套公式再看条件”的问题。',
  },
]

export const growthHistory = [
  { exam: '周测 01', score: 69, summary: '基础题不稳' },
  { exam: '周测 02', score: 73, summary: '计算准确率提升' },
  { exam: '周测 03', score: 78, summary: '基础稳定，应用题待补' },
  { exam: '月考', score: 81, summary: '阅读理解更稳，但建模仍慢' },
]