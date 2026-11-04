<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { list_papers, list_subjects } from '../api/student'

const router = useRouter()

const loading = ref(false)
const subjects = ref<any[]>([])
const papers = ref<any[]>([])

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    // 用 allSettled：答卷列表失败不该把学科列表也拖空
    const [subject_result, paper_result] = await Promise.allSettled([
      list_subjects({ page: 1, page_size: 50 }),
      list_papers({ page: 1, page_size: 5 }),
    ])
    if (subject_result.status === 'fulfilled') {
      subjects.value = (subject_result.value as any)?.list ?? []
    }
    if (paper_result.status === 'fulfilled') {
      papers.value = (paper_result.value as any)?.list ?? []
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">刷题自测</h2>
    <p class="page-sub">按题型比例随机抽 20 题组卷，全部作答后一次性提交；提交后立即判分</p>

    <div v-if="subjects.length" class="subject-grid">
      <div
        v-for="item in subjects"
        :key="item.id"
        class="subject-card"
        @click="router.push({ path: `/practice/${item.id}`, query: { name: item.name } })"
      >
        <div class="head">
          <span class="icon">{{ item.icon || '📘' }}</span>
          <h3>{{ item.name }}</h3>
        </div>
        <div class="desc">从该学科题池随机组卷</div>
        <div class="meta-row" style="margin-top: 10px">
          <span class="tag-soft">开始组卷 →</span>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">还没有可刷题的学科</div>
    </div>

    <div v-if="papers.length" class="card" style="margin-top: 18px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <h3 style="margin: 0; font-size: 16px">最近答卷</h3>
        <el-button link @click="router.push('/papers')">查看全部</el-button>
      </div>
      <div v-for="item in papers" :key="item.id" class="record-row">
        <div>
          <div class="title">{{ item.subject_name }}</div>
          <div class="sub">{{ item.question_count }} 题 · {{ format_time(item.submitted_at) }}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px">
          <span v-if="item.status === 2" class="score-chip">
            {{ item.obtained_score }} / {{ item.total_score }}
          </span>
          <span v-else class="tag-soft">判分中</span>
          <el-button size="small" @click="router.push(`/paper/${item.id}`)">查看</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
