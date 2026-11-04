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
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
    meta: { public: true, title: '注册' },
  },
  {
    path: '/',
    component: () => import('../layouts/StudentLayout.vue'),
    redirect: '/home',
    children: [
      { path: 'home', name: 'home', component: () => import('../views/HomeView.vue'), meta: { title: '首页' } },
      { path: 'subject/:id', name: 'subject', component: () => import('../views/SubjectView.vue'), meta: { title: '学习路径' } },
      { path: 'practice', name: 'practice', component: () => import('../views/PracticeSelectView.vue'), meta: { title: '刷题' } },
      { path: 'practice/:subjectId', name: 'practice-run', component: () => import('../views/PracticeRunView.vue'), meta: { title: '答题' } },
      { path: 'papers', name: 'papers', component: () => import('../views/PapersView.vue'), meta: { title: '我的答卷' } },
      { path: 'paper/:id', name: 'paper', component: () => import('../views/PaperView.vue'), meta: { title: '答卷详情' } },
      { path: 'wrong', name: 'wrong', component: () => import('../views/WrongBookView.vue'), meta: { title: '错题本' } },
      { path: 'interview', name: 'interview', component: () => import('../views/InterviewSelectView.vue'), meta: { title: 'AI 面试' } },
      { path: 'resume', name: 'resume', component: () => import('../views/ResumeView.vue'), meta: { title: '简历面试' } },
      { path: 'interview/:id/report', name: 'interview-report', component: () => import('../views/InterviewReportView.vue'), meta: { title: '面试报告' } },
      { path: 'interview/:id', name: 'interview-live', component: () => import('../views/InterviewLiveView.vue'), meta: { title: '面试进行中' } },
      { path: 'records', name: 'records', component: () => import('../views/RecordsView.vue'), meta: { title: '学习记录' } },
      { path: 'profile', name: 'profile', component: () => import('../views/ProfileView.vue'), meta: { title: '我的' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

router.beforeEach((to) => {
  const token = get_access_token()
  if (!to.meta.public && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && token) {
    return { name: 'home' }
  }
  document.title = `${to.meta.title || '云枢智学'} · 云枢智学`
  return true
})

export default router
