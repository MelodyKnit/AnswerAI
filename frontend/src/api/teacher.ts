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

export interface TeacherStudentPortrait {
  student: {
    id: number
    name: string
    email?: string | null
    phone?: string | null
    avatar_url?: string | null
    grade_name?: string | null
    school_name?: string | null
    status?: string | null
    last_login_at?: string | null
  }
  class?: {
    id: number
    name: string
    grade_name: string
    subject: string
    teacher_id: number
    student_count: number
    invite_code: string
    status: string
    created_at: string
  } | null
  overview: {
    exam_count: number
    avg_score: number
    latest_score: number
    avg_correct_rate: number
    momentum: number
    pending_review_count: number
    active_task_count: number
    estimated_study_minutes: number
    risk_level: 'high' | 'medium' | 'low' | string
  }
  ability_profile: Array<{
    name: string
    value: number
    question_count: number
    accuracy: number
    reason: string
  }>
  question_type_distribution: Array<{
    type: string
    question_count: number
    accuracy: number
  }>
  knowledge_points: Array<{
    id: number
    name: string
    question_count: number
    wrong_count: number
    mastery: number
  }>
  trend: Array<{
    exam_id: number
    exam_title: string
    submitted_at: string
    score: number
    correct_rate: number
    class_avg: number
    ranking_in_class?: number | null
  }>
  study_tasks: Array<{
    id: number
    title: string
    task_type?: string | null
    status: string
    priority: number
    estimated_minutes?: number | null
    feedback?: string | null
    created_at: string
  }>
  task_summary: {
    pending_count: number
    completed_count: number
    ignored_count: number
    estimated_minutes: number
  }
  ai_insight: {
    summary?: string | null
    coaching_suggestions: string[]
    weak_knowledge_points: string[]
    highlight?: {
      name: string
      value: number
      question_count: number
      accuracy: number
      reason: string
    } | null
    risk_focus?: {
      name: string
      value: number
      question_count: number
      accuracy: number
      reason: string
    } | null
  }
  latest_summary: {
    latest_exam_id?: number | null
    latest_exam_title?: string | null
    latest_total_score?: number | null
    latest_submitted_at?: string | null
  }
}

export interface TeacherFeedbackItem {
  id: number
  category: 'bug' | 'product' | 'design' | 'other' | string
  content: string
  images: string[]
  page_path?: string | null
  client_role?: string | null
  client_name?: string | null
  client_email?: string | null
  created_at: string
}

export interface TeacherFeedbackListResponse {
  items: TeacherFeedbackItem[]
  total: number
  summary: {
    bug: number
    product: number
    design: number
    other: number
  }
  page: number
  page_size: number
}

export interface TeacherClassAnalysis {
  overview: {
    class_name: string
    student_count: number
    exam_count: number
    avg_score: number
    avg_correct_rate: number
    completion_rate: number
  }
  risk_distribution: Array<{
    level: 'high' | 'medium' | 'low' | string
    label: string
    count: number
  }>
  score_distribution: Array<{
    range: string
    count: number
  }>
  exam_trend: Array<{
    exam_id: number
    title: string
    avg_score: number
    submission_rate: number
    submitted_count: number
    student_count: number
  }>
  weak_knowledge_points: Array<{
    name: string
    count: number
    source?: 'knowledge_point' | 'stem_keyword' | 'question_type' | string
    source_label?: string
  }>
  weak_question_signals: Array<{
    question_id: number
    title: string
    type: string
    type_label: string
    attempt_count: number
    wrong_count: number
    wrong_rate: number
    avg_spent_seconds: number
    sample_wrong_answer?: string
  }>
  answer_diagnostics: Array<{
    type: string
    label: string
    count: number
    ratio: number
    description: string
  }>
  question_type_performance: Array<{
    type: string
    label: string
    question_count: number
    wrong_rate: number
  }>
  focus_students: Array<{
    student_id: number
    student_name: string
    score: number
    correct_rate: number
    risk_level: 'high' | 'medium' | 'low' | string
  }>
  student_risks: Array<{
    student_id: number
    student_name: string
    risk_level: 'high' | 'medium' | 'low' | string
    score: number
    correct_rate: number
  }>
  ai_insight: {
    summary: string
    actions: string[]
    findings?: string[]
  }
}

export const getTeacherDashboardOverview = (params?: { subject?: string }) => {
  return http.get('/teacher/dashboard/overview', { params }) as Promise<TeacherDashboardOverview>
}

export const getTeacherFeedbackList = (params?: {
  category?: 'bug' | 'product' | 'design' | 'other'
  keyword?: string
  page?: number
  page_size?: number
}) => {
  return http.get('/teacher/feedback/list', { params }) as Promise<TeacherFeedbackListResponse>
}

// --- 5. 教师班级与学生管理接口 ---

export const getClasses = (params?: { page?: number, page_size?: number }) => {
  return http.get('/teacher/classes', { params })
}

export const createClass = (data: { name: string, grade_name: string, subject: string }) => {
  return http.post('/teacher/classes/create', data)
}

export const updateClass = (data: { class_id: number, name: string, grade_name: string, subject: string }) => {
  return http.post('/teacher/classes/update', data)
}

export const getClassDetail = (class_id: number) => {
  return http.get('/teacher/classes/detail', { params: { class_id } })
}

export const getClassStudents = (params: { class_id: number, keyword?: string, risk_level?: string, page?: number, page_size?: number }) => {
  return http.get('/teacher/classes/students', { params })
}

export const getClassAnalysis = (class_id: number) => {
  return http.get('/teacher/classes/analysis', { params: { class_id } }) as Promise<TeacherClassAnalysis>
}

export const inviteStudentToClass = (data: { class_id: number, student_id: number }) => {
  return http.post('/teacher/classes/students/invite', data)
}

export const removeStudentFromClass = (data: { class_id: number, student_id: number }) => {
  return http.post('/teacher/classes/students/remove', data)
}

export const getStudentDetail = (student_id: number) => {
  return http.get('/teacher/students/detail', { params: { student_id } }) as Promise<TeacherStudentPortrait>
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
