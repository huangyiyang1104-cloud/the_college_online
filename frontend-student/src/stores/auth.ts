import { defineStore } from 'pinia'
import { login as api_login, logout as api_logout, register as api_register } from '../api/student'
import {
  clear_session,
  get_access_token,
  get_student,
  save_session,
} from '../utils/token_storage'

// 登录态只做前端导航控制，真正的认证与权限在后端
export const use_auth_store = defineStore('student_auth', {
  state: () => ({
    access_token: get_access_token(),
    student: get_student(),
  }),
  getters: {
    is_logged_in: (state) => !!state.access_token,
    display_name: (state) => state.student?.nickname || mask_phone(state.student?.phone),
  },
  actions: {
    _apply(payload: any) {
      save_session(payload.access_token, payload.refresh_token, payload.user)
      this.access_token = payload.access_token
      this.student = payload.user
    },
    async login(phone: string, password: string) {
      this._apply(await api_login(phone, password))
    },
    async register(phone: string, code: string, password: string) {
      this._apply(await api_register(phone, code, password))
    },
    async logout() {
      try {
        await api_logout()
      } catch {
        // 退出失败不影响本地清理
      }
      clear_session()
      this.access_token = ''
      this.student = null
    },
  },
})

export function mask_phone(phone?: string | null): string {
  if (!phone) return '学员'
  return phone.length === 11 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone
}
