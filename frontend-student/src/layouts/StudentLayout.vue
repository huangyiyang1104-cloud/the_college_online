<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { use_auth_store } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = use_auth_store()

const menus = [
  { path: '/home', label: '首页' },
  { path: '/practice', label: '刷题' },
  { path: '/wrong', label: '错题本' },
  { path: '/interview', label: 'AI 面试' },
  { path: '/resume', label: '简历面试' },
  { path: '/records', label: '学习记录' },
  { path: '/profile', label: '我的' },
]

// 学员端与管理端是两个独立工程，底部互相留入口
const admin_entry = import.meta.env.DEV ? 'http://localhost:5174/admin/' : '/admin/'

// 二级页面：统一由布局提供「返回」栏（sticky，滚动时始终可见）
const back_map: Record<string, { to: string; label: string }> = {
  subject: { to: '/home', label: '首页' },
  'practice-run': { to: '/practice', label: '刷题' },
  papers: { to: '/practice', label: '刷题' },
  paper: { to: '/papers', label: '我的答卷' },
  'interview-live': { to: '/interview', label: 'AI 面试' },
  'interview-report': { to: '/interview', label: 'AI 面试' },
  resume: { to: '/interview', label: 'AI 面试' },
}

const back_info = computed(() => back_map[String(route.name ?? '')] ?? null)
const page_title = computed(() => String(route.meta.title ?? ''))

const active = computed(() => {
  if (route.path.startsWith('/subject')) return '/home'
  if (route.path.startsWith('/practice')) return '/practice'
  if (route.path.startsWith('/paper')) return '/practice'
  if (route.path.startsWith('/interview')) return '/interview'
  if (route.path.startsWith('/resume')) return '/resume'
  return route.path
})

function go_back() {
  // 有明确的上级页面就直接跳，避免浏览器历史为空时 back() 退出站点
  if (back_info.value) router.push(back_info.value.to)
  else router.back()
}

async function handle_logout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="logo" @click="router.push('/home')">
          <span class="mark">枢</span>
          <span>云枢智学</span>
        </div>

        <nav class="nav">
          <router-link
            v-for="item in menus"
            :key="item.path"
            :to="item.path"
            :class="{ active: active === item.path }"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <el-dropdown>
          <span style="font-size: 14px; cursor: pointer">
            {{ auth.display_name }}
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/profile')">个人信息</el-dropdown-item>
              <el-dropdown-item divided @click="handle_logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 二级页面返回栏：sticky 贴住顶栏，滚动到底部也点得到 -->
    <div v-if="back_info" class="subbar">
      <div class="subbar-inner">
        <button type="button" class="back-btn" @click="go_back">← 返回</button>
        <span class="crumb">{{ back_info.label }}</span>
        <span class="crumb-sep">/</span>
        <span class="crumb-current">{{ page_title }}</span>
      </div>
    </div>

    <router-view />

    <footer class="site-footer">
      <button v-if="back_info" type="button" class="footer-back" @click="go_back">
        ↑ 返回{{ back_info.label }}
      </button>
      <div class="footer-meta">
        <span>云枢智学 · 交互演示</span>
        <span class="dot">·</span>
        <a :href="admin_entry" target="_blank" rel="noopener">进入管理端</a>
      </div>
    </footer>
  </div>
</template>
