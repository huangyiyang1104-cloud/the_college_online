// 令牌存储：与 Pinia store 共用，避免 http 层与 store 相互依赖
const ACCESS_KEY = 'yunshu_admin_access'
const REFRESH_KEY = 'yunshu_admin_refresh'
const USER_KEY = 'yunshu_admin_user'

export function get_access_token(): string {
  return localStorage.getItem(ACCESS_KEY) || ''
}

export function get_refresh_token(): string {
  return localStorage.getItem(REFRESH_KEY) || ''
}

export function get_admin_user(): { id: string; username: string; role: number } | null {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function save_session(access: string, refresh: string, user: unknown): void {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clear_session(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}
