import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import {
  clear_session,
  get_access_token,
  get_refresh_token,
  save_session,
  get_admin_user,
} from '../utils/token_storage'

const http = axios.create({ baseURL: '/api/v1', timeout: 60000 })

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = get_access_token()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 并发请求同时 401 时共享同一次刷新，避免后到的请求把 session 清掉
let refresh_promise: Promise<boolean> | null = null

async function do_refresh(): Promise<boolean> {
  const refresh_token = get_refresh_token()
  if (!refresh_token) return false
  try {
    // 用裸 axios 调用，避免再次进入拦截器
    const { data } = await axios.post('/api/v1/admin/auth/tokens', { refresh_token })
    const payload = data?.data
    if (!payload?.access_token) return false
    save_session(payload.access_token, payload.refresh_token, get_admin_user())
    return true
  } catch {
    return false
  }
}

function refresh_access_token(): Promise<boolean> {
  if (!refresh_promise) {
    refresh_promise = do_refresh().finally(() => {
      refresh_promise = null
    })
  }
  return refresh_promise
}

http.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body?.data ?? body
  },
  async (error: AxiosError<any>) => {
    const status = error.response?.status
    const body = error.response?.data
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }

    // 压根没连上后端（未启动 / 端口不通 / 跨域被拦）
    if (!error.response) {
      ElMessage.error('无法连接服务器，请确认后端已启动（127.0.0.1:8000）')
      return Promise.reject(error)
    }

    // 登录 / 刷新接口自身的 401：只提示，不跳转、不刷新页面，
    // 否则提示还没渲染出来就被 location.href 重载掉了
    const is_auth_entry = /\/admin\/auth\/(login|tokens)$/.test(original?.url || '')
    if (status === 401 && is_auth_entry) {
      ElMessage.error(body?.message || '账号或密码错误')
      return Promise.reject(error)
    }

    if (status === 401 && original && !original._retried) {
      original._retried = true
      const ok = await refresh_access_token()
      if (ok) return http(original)

      clear_session()
      ElMessage.error(body?.message || '登录已失效，请重新登录')
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/admin/login'
      }
      return Promise.reject(error)
    }

    if (status === 401) {
      clear_session()
      ElMessage.error(body?.message || '未认证或登录已失效')
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/admin/login'
      }
      return Promise.reject(error)
    }

    const fieldMessage = body?.data?.fields?.[0]
    ElMessage.error(
      fieldMessage ? `${fieldMessage.field}：${fieldMessage.reason}` : body?.message || '请求失败',
    )
    return Promise.reject(error)
  },
)

export default http
