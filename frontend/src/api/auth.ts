import http from '@/lib/http'

export type ProfileUpdatePayload = {
  name?: string
  email?: string
  phone?: string
  avatar_url?: string
  school_name?: string
  grade_name?: string
}

export type ChangePasswordPayload = {
  old_password: string
  new_password: string
}

export const updateProfile = (payload: ProfileUpdatePayload) => {
  return http.post('/users/profile/update', payload)
}

export const changePassword = (payload: ChangePasswordPayload) => {
  return http.post('/users/password/change', payload)
}
