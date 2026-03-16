import http from '@/lib/http'

export type FeedbackCategory = 'bug' | 'product' | 'design' | 'other'

export type SubmitFeedbackPayload = {
  category: FeedbackCategory
  content: string
  images: string[]
  page_path?: string
}

export const submitUserFeedback = (payload: SubmitFeedbackPayload) => {
  return http.post('/users/feedback/create', payload)
}
