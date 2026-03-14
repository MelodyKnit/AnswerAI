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
      window.location.href = '/app/auth'
    }
    // Also attach message for unprocessable entities
    if (error.response && error.response.status === 422) {
      return Promise.reject(new Error("参数错误或密码长度不够(请确保密码至少8位并且邮箱格式正确)"))
    }
    return Promise.reject(error)
  }
)

export default http
