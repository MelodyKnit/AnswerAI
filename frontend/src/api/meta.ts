import http from '@/lib/http'

export const getSubjects = () => {
  return http.get('/meta/subjects')
}

export const getGrades = () => {
  return http.get('/meta/grades')
}

export const getQuestionTypes = () => {
  return http.get('/meta/question-types')
}

export const getKnowledgePointsTree = (subject: string) => {
  return http.get('/meta/knowledge-points/tree', { params: { subject } })
}
