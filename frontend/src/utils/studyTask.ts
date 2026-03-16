export const mapStudyTaskTypeLabel = (taskType?: string | null) => {
  const normalized = String(taskType || '').trim().toLowerCase()
  if (normalized === 'wrong_question_review') return '错题回顾'
  if (normalized === 'knowledge_review') return '知识点复习'
  if (normalized === 'consolidation') return '巩固训练'
  return '综合复习'
}

export const mapStudyTaskStatusLabel = (status?: string | null) => {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'pending') return '待开始'
  if (normalized === 'in_progress') return '进行中'
  if (normalized === 'completed') return '已完成'
  if (normalized === 'ignored') return '已忽略'
  return '未知状态'
}
