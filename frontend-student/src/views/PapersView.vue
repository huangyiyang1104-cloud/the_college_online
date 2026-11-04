<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { list_papers } from '../api/student'

const router = useRouter()

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10 })

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const data: any = await list_papers({ page: query.page, page_size: query.page_size })
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">我的答卷</h2>
    <p class="page-sub">每次提交都会留档，点进去可以看逐题得分与点评</p>

    <div v-if="rows.length" class="card">
      <div v-for="item in rows" :key="item.id" class="record-row">
        <div>
          <div class="title">{{ item.subject_name || '未知学科' }}</div>
          <div class="sub">
            {{ item.question_count }} 题 · {{ format_time(item.submitted_at) }}
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px">
          <span v-if="item.status === 2" class="score-chip">
            {{ item.obtained_score }} / {{ item.total_score }}
          </span>
          <span v-else class="tag-soft">判分中</span>
          <el-button size="small" @click="router.push(`/paper/${item.id}`)">查看</el-button>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">
        还没有答卷，去
        <router-link to="/practice">刷题</router-link>
        试试
      </div>
    </div>

    <el-pagination
      v-if="total > query.page_size"
      v-model:current-page="query.page"
      :page-size="query.page_size"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 16px; justify-content: center"
      @current-change="load"
    />
  </div>
</template>
