import { createRouter, createWebHistory } from 'vue-router'
import { get_access_token } from '../utils/token_storage'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '数据看板' } },
      { path: 'content', name: 'content', component: () => import('../views/ContentView.vue'), meta: { title: '课程内容' } },
      { path: 'questions', name: 'questions', component: () => import('../views/QuestionsView.vue'), meta: { title: '刷题题库' } },
      { path: 'interview-docs', name: 'interview-docs', component: () => import('../views/InterviewDocsView.vue'), meta: { title: '面试资料库' } },
      { path: 'students', name: 'students', component: () => import('../views/StudentsView.vue'), meta: { title: '学员管理' } },
      { path: 'users', name: 'users', component: () => import('../views/UsersView.vue'), meta: { title: '系统用户', super_only: true } },
      { path: 'logs', name: 'logs', component: () => import('../views/LogsView.vue'), meta: { title: '操作日志' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes,
})

router.beforeEach((to) => {
  const token = get_access_token()
  if (!to.meta.public && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && token) {
    return { name: 'dashboard' }
  }
  document.title = `${to.meta.title || '管理后台'} · 云枢智学`
  return true
})

export default router
