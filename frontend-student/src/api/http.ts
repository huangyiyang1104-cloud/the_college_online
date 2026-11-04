import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import {
  clear_session,
  get_access_token,
  get_refresh_token,
  get_student,
  save_session,
} from '../utils/token_storage'

const http = axios.create({ baseURL: '/api/v1', timeout: 60000 })

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = get_access_token()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 并发请求同时遇到 401 时，必须共享同一次刷新：
// 否则后来的请求看到"正在刷新"就直接清 session 跳登录，刷新成功也白搭
let refresh_promise: Promise<boolean> | null = null

async function do_refresh(): Promise<boolean> {
  const refresh_token = get_refresh_token()
  if (!refresh_token) return false
  try {
    const { data } = await axios.post('/api/v1/auth/tokens', { refresh_token })
    const payload = data?.data
    if (!payload?.access_token) return false
    save_session(payload.access_token, payload.refresh_token, payload.user || get_student())
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

    if (!error.response) {
      // 区分「没连上」和「等太久」：出题与评分走模型，可能接近超时阈值
      const timed_out =
        error.code === 'ECONNABORTED' || /timeout/i.test(String(error.message || ''))
      ElMessage.error(
        timed_out
          ? '请求超时：模型出题或评分较慢，请稍后重试'
          : '无法连接服务器，请确认后端已启动（127.0.0.1:8000）',
      )
      return Promise.reject(error)
    }

    // 登录 / 注册 / 刷新自身的 401：只提示，不跳转
    const is_auth_entry = /\/auth\/(login|register|tokens|sms-codes)$/.test(original?.url || '')
    if (is_auth_entry) {
      ElMessage.error(body?.message || '操作失败')
      return Promise.reject(error)
    }

    if (status === 401 && original && !original._retried) {
      original._retried = true
      // 所有并发 401 都等这一次刷新结果，成功则各自重放
      const ok = await refresh_access_token()
      if (ok) return http(original)

      clear_session()
      ElMessage.error('登录已失效，请重新登录')
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    const field = body?.data?.fields?.[0]
    ElMessage.error(field ? `${field.field}：${field.reason}` : body?.message || '请求失败')
    return Promise.reject(error)
  },
)

export default http
