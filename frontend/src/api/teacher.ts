import http from '@/lib/http'

export interface TeacherDashboardOverview {
  exam_count: number
  pending_review_count: number
  risk_student_count: number
  avg_score_trend: Array<{ exam_id: number, avg_score: number }>
  ai_class_summary: string
  risk_students?: Array<{
    student_id: number
    student_name: string
    class_name?: string | null
    exam_id: number
    exam_title?: string | null
    latest_score: number
    correct_rate: number
    risk_level: 'high' | 'medium' | 'low' | string
    weak_abilities: string[]
    weak_knowledge_points: string[]
    coaching_suggestions: string[]
  }>
}

export const getTeacherDashboardOverview = (params?: { subject?: string }) => {
  return http.get('/teacher/dashboard/overview', { params }) as Promise<TeacherDashboardOverview>
}

// --- 5. 教师班级与学生管理接口 ---

export const getClasses = (params?: { page?: number, page_size?: number }) => {
  return http.get('/teacher/classes', { params })
}

export const createClass = (data: { name: string, grade_name: string, subject: string }) => {
  return http.post('/teacher/classes/create', data)
}

export const getClassDetail = (class_id: number) => {
  return http.get('/teacher/classes/detail', { params: { class_id } })
}

export const getClassStudents = (params: { class_id: number, keyword?: string, risk_level?: string, page?: number, page_size?: number }) => {
  return http.get('/teacher/classes/students', { params })
}

export const inviteStudentToClass = (data: { class_id: number, student_id: number }) => {
  return http.post('/teacher/classes/students/invite', data)
}

export const removeStudentFromClass = (data: { class_id: number, student_id: number }) => {
  return http.post('/teacher/classes/students/remove', data)
}

export const getStudentDetail = (student_id: number) => {
  return http.get('/teacher/students/detail', { params: { student_id } })
}

// --- 6. 教师题库与出题接口 ---

export const getQuestions = (params?: {
  subject?: string, type?: string, difficulty_min?: number, difficulty_max?: number,
  knowledge_point_id?: number, keyword?: string, page?: number, page_size?: number
}) => {
  return http.get('/teacher/questions', { params })
}

export const getQuestionSubjects = () => {
  return http.get('/teacher/questions/subjects')
}

export const getQuestionDetail = (question_id: number) => {
  return http.get('/teacher/questions/detail', { params: { question_id } })
}

export const createQuestion = (data: any) => {
  return http.post('/teacher/questions/create', data)
}

export const updateQuestion = (data: any) => {
  return http.post('/teacher/questions/update', data)
}

export const deleteQuestion = (question_id: number) => {
  return http.post('/teacher/questions/delete', { question_id })
}

export const importQuestions = (data: { file_url?: string, import_type: string, subject: string }) => {
  return http.post('/teacher/questions/import', data)
}

export const generateQuestionsByAi = (data: any) => {
  return http.post('/teacher/questions/ai-generate', data)
}

export const reviewQuestionByAi = (question_id: number) => {
  return http.post('/teacher/questions/ai-review', { question_id })
}

// --- 7. 教师考试管理接口 ---

export const createExam = (data: any) => {
  return http.post('/teacher/exams/create', data)
}

export const getExams = (params?: {
  status?: string, subject?: string, class_id?: number, keyword?: string, page?: number, page_size?: number
}) => {
  return http.get('/teacher/exams', { params })
}

export const getExamDetail = (exam_id: number) => {
  return http.get('/teacher/exams/detail', { params: { exam_id } })
}

export const getExamInsights = (exam_id: number) => {
  return http.get('/teacher/exams/insights', { params: { exam_id } })
}

export const updateExam = (data: any) => {
  return http.post('/teacher/exams/update', data)
}

export const publishExam = (exam_id: number) => {
  return http.post('/teacher/exams/publish', { exam_id })
}

export const pauseExam = (exam_id: number) => {
  return http.post('/teacher/exams/pause', { exam_id })
}

export const finishExam = (exam_id: number) => {
  return http.post('/teacher/exams/finish', { exam_id })
}

export const deleteExam = (exam_id: number) => {
  return http.post('/teacher/exams/delete', { exam_id })
}

export const evaluateExamByAi = (exam_id: number) => {
  return http.post('/teacher/exams/ai-evaluate', { exam_id })
}

export const assembleExamByAi = (data: { subject: string, requirement: string, exclude_question_ids?: number[] }) => {
  return http.post('/teacher/exams/ai-assemble', data)
}

// --- 9. 阅卷与评分接口 ---

export const getObjectiveScore = (params: { exam_id: number, submission_id: number }) => {
  return http.get('/teacher/review/objective-score', { params })
}

export const triggerAiScore = (data: { exam_id: number, submission_id: number }) => {
  return http.post('/teacher/review/ai-score', data)
}

export const getReviewItems = (params: { exam_id: number, review_status?: string, page?: number, page_size?: number }) => {
  const safeParams = {
    ...params,
    page_size: Math.min(100, Math.max(1, Number(params.page_size || 20))),
  }
  return http.get('/teacher/review/items', { params: safeParams })
}

export const getReviewTasks = (params?: { view?: 'all' | 'pending' | 'completed', page?: number, page_size?: number }) => {
  return http.get('/teacher/review/tasks', { params })
}

export const getRetakeRequests = (params?: { status?: string, page?: number, page_size?: number }) => {
  return http.get('/teacher/review/retake-requests', { params })
}

export const reviewRetakeRequest = (data: { request_id: number, action: 'approve' | 'reject', comment?: string }) => {
  return http.post('/teacher/review/retake-requests/action', data)
}

export const submitReview = (data: { review_item_id: number, final_score: number, review_comment?: string }) => {
  return http.post('/teacher/review/submit', data)
}

export const publishExamResults = (exam_id: number) => {
  return http.post('/teacher/review/publish-results', { exam_id })
}
