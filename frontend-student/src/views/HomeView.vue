<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetch_home } from '../api/student'
import { use_auth_store } from '../stores/auth'

const router = useRouter()
const auth = use_auth_store()

const loading = ref(false)
const subjects = ref<any[]>([])
const recent = ref<any[]>([])

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

async function load() {
  loading.value = true
  try {
    const data: any = await fetch_home()
    subjects.value = data.subjects || []
    recent.value = data.recent_visits || []
  } finally {
    loading.value = false
  }
}

function open_subject(id: string) {
  router.push(`/subject/${id}`)
}

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">{{ greeting }}，{{ auth.display_name }}</h2>
    <p class="page-sub">选一个学科，按顺序把课程节点一个个点亮</p>

    <div v-if="subjects.length" class="subject-grid">
      <div v-for="item in subjects" :key="item.id" class="subject-card" @click="open_subject(item.id)">
        <div class="head">
          <span class="icon">{{ item.icon || '📘' }}</span>
          <h3>{{ item.name }}</h3>
        </div>
        <div class="desc">{{ item.description || '暂无简介' }}</div>

        <div class="meter">
          <span :style="{ width: `${item.progress_percent}%` }" />
        </div>
        <div class="meta-row">
          <span>已点亮 {{ item.completed_count }} / {{ item.course_count }}</span>
          <span>{{ item.progress_percent }}%</span>
        </div>

        <div v-if="item.next_course" class="meta-row" style="margin-top: 8px">
          <span class="tag-soft">下一课：{{ item.next_course.title }}</span>
        </div>
        <div v-else-if="item.course_count" class="meta-row" style="margin-top: 8px">
          <span class="tag-soft tag-done">已全部点亮</span>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">运营还没有上架任何学科，稍后再来看看</div>
    </div>

    <div v-if="recent.length" class="card" style="margin-top: 18px">
      <h3 style="margin: 0 0 6px; font-size: 16px">最近学习</h3>
      <div v-for="item in recent" :key="item.course_id" class="record-row">
        <div>
          <div class="title">{{ item.course_title }}</div>
          <div class="sub">{{ item.subject_name }} · {{ format_time(item.visited_at) }}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px">
          <span v-if="item.is_completed" class="tag-soft tag-done">已点亮</span>
          <el-button size="small" @click="open_subject(item.subject_id)">继续</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
