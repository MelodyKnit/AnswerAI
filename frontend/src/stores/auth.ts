import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '../lib/http'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<any>(null)

  const login = async (form: any) => {
    const data: any = await http.post('/auth/login', form)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
  }

  const register = async (form: any) => {
    const data: any = await http.post('/auth/register', form)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
  }

  const fetchUser = async () => {
    if (!token.value) return
    try {
      const data: any = await http.get('/auth/me')
      user.value = data.user
    } catch (err) {
      logout()
    }
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  const setUser = (nextUser: any) => {
    user.value = nextUser
  }

  const patchUser = (patch: Record<string, unknown>) => {
    user.value = {
      ...(user.value || {}),
      ...patch,
    }
  }

  return { token, user, login, register, fetchUser, logout, setUser, patchUser }
})
