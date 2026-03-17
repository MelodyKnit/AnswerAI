import axios from 'axios'

const translateValidationMsg = (msg: string) => {
  const m = String(msg || '')
  if (m.includes('Field required')) return '必填项未填写'
  if (m.includes('Input should be a valid email address')) return '邮箱格式不正确'
  if (m.includes('String should have at least')) return '输入长度不符合要求'
  if (m.includes('String should match pattern')) return '输入格式不符合要求'
  return m
}

const translateFieldName = (name: string) => {
  const map: Record<string, string> = {
    role: '角色',
    name: '真实姓名',
    username: '用户名',
    email: '邮箱地址',
    password: '密码',
    confirm_password: '确认密码',
    login_id: '登录账号',
    teacher_invite_code: '组织机构代码',
    class_code: '班级邀请码',
  }
  return map[name] || name
}

const normalizeErrorMessage = (error: any) => {
  const detail = error?.response?.data?.detail
  const status = Number(error?.response?.status || 0)
  const requestUrl = String(error?.config?.url || '')
  const isAuthApi = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register')

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const lines = detail
      .slice(0, 4)
      .map((item: any) => {
        const locList = Array.isArray(item?.loc) ? item.loc : []
        const field = translateFieldName(String(locList[locList.length - 1] || '参数'))
        const msg = translateValidationMsg(String(item?.msg || '参数不合法'))
        return `${field}：${msg}`
      })
    return lines.join('；')
  }

  if (status === 400) {
    return isAuthApi ? '请求参数有误，请检查输入内容后重试' : '请求参数有误'
  }
  if (status === 401) {
    return isAuthApi ? '账号或密码错误' : '登录状态已失效，请重新登录'
  }
  if (status === 403) {
    return isAuthApi ? '当前账号无权限执行该操作' : '没有访问权限'
  }
  if (status === 404) {
    return '请求的服务不存在'
  }
  if (status === 409) {
    return isAuthApi ? '账号信息冲突，请更换后重试' : '数据冲突，请刷新后重试'
  }
  if (status >= 500) {
    return '服务器开小差了，请稍后重试'
  }

  if (error?.code === 'ECONNABORTED') {
    return '请求超时，请检查网络后重试'
  }
  if (!error?.response) {
    return '网络连接失败，请检查网络或服务是否启动'
  }

  if (error?.message) {
    return String(error.message)
  }
  return '请求失败，请稍后重试'
}

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

    return Promise.reject(new Error(normalizeErrorMessage(error)))
  }
)

export default http
