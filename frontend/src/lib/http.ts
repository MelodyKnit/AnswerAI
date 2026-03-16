import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 15000
})

http.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

http.interceptors.response.use(
  response => {
    // API always returns { code, message, data, ... }
    const res = response.data
    // You might want to handle custom API error codes here
    if (res.code !== 0) {
      return Promise.reject(new Error(res.message || 'API Error'))
    }
    return res.data
  },
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/auth'
    }

    const detail = error?.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return Promise.reject(new Error(detail))
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      if (first?.msg) {
        return Promise.reject(new Error(String(first.msg)))
      }
    }

    if (error?.message) {
      return Promise.reject(new Error(String(error.message)))
    }

    return Promise.reject(new Error('请求失败，请稍后重试'))
  }
)

export default http
