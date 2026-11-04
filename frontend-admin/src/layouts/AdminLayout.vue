<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { use_auth_store } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = use_auth_store()

const menus = computed(() => {
  const items = [
    { path: '/dashboard', label: '数据看板' },
    { path: '/content', label: '课程内容' },
    { path: '/questions', label: '刷题题库' },
    { path: '/interview-docs', label: '面试资料库' },
    { path: '/students', label: '学员管理' },
  ]
  if (auth.is_super_admin) items.push({ path: '/users', label: '系统用户' })
  items.push({ path: '/logs', label: '操作日志' })
  return items
})

const student_entry = import.meta.env.DEV ? 'http://localhost:5173' : '/'

async function handle_logout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside width="216px" class="aside">
      <div class="brand">
        <span class="dot">枢</span>
        <span>云枢智学 · 后台</span>
      </div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="left">
          <span class="page-title">{{ route.meta.title }}</span>
        </div>
        <div class="right">
          <a class="entry-link" :href="student_entry" target="_blank" rel="noopener">返回学员端</a>
          <el-dropdown>
            <span class="user">
              {{ auth.admin_user?.username || '管理员' }}
              <el-tag size="small" :type="auth.is_super_admin ? 'danger' : 'info'">
                {{ auth.is_super_admin ? '超管' : '运营' }}
              </el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handle_logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>

      <el-footer class="footer" height="42px">
        <span>云枢智学 · 管理后台</span>
        <span class="sep">·</span>
        <a :href="student_entry" target="_blank" rel="noopener">返回学员端</a>
      </el-footer>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-shell {
  height: 100%;
}

.aside {
  background: #fff;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
}

.menu {
  border-right: none;
  flex: 1;
}

.header {
  background: #fff;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
}

.right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}

.entry-link {
  color: var(--brand);
  text-decoration: none;
  font-size: 13px;
}

.main {
  background: #f5f6fb;
  padding: 0;
  overflow-y: auto;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
  background: #fff;
  border-top: 1px solid var(--line);
}

.footer a {
  color: var(--muted);
}

.footer a:hover {
  color: var(--brand);
}
</style>
