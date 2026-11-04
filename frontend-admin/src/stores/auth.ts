import { defineStore } from 'pinia'
import { admin_login, admin_logout } from '../api/admin'
import {
  clear_session,
  get_access_token,
  get_admin_user,
  save_session,
} from '../utils/token_storage'

// 登录态只做前端导航控制，真正的权限校验在后端（见开发规范 8）
export const use_auth_store = defineStore('auth', {
  state: () => ({
    access_token: get_access_token(),
    admin_user: get_admin_user(),
  }),
  getters: {
    is_logged_in: (state) => !!state.access_token,
    is_super_admin: (state) => state.admin_user?.role === 1,
  },
  actions: {
    async login(username: string, password: string) {
      const payload: any = await admin_login(username, password)
      save_session(payload.access_token, payload.refresh_token, payload.admin_user)
      this.access_token = payload.access_token
      this.admin_user = payload.admin_user
      return payload
    },
    async logout() {
      try {
        await admin_logout()
      } catch {
        // 退出失败不影响本地清理
      }
      clear_session()
      this.access_token = ''
      this.admin_user = null
    },
  },
})
