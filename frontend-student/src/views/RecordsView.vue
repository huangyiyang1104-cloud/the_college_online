<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { list_records, list_subjects, records_summary } from '../api/student'

const router = useRouter()

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const summary = ref({ visited_count: 0, completed_count: 0, subject_count: 0 })
const subjects = ref<any[]>([])
const query = reactive({ subject_id: '', page: 1, page_size: 10 })

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const [list, stats] = await Promise.all([
      list_records({
        page: query.page,
        page_size: query.page_size,
        subject_id: query.subject_id || undefined,
      }) as any,
      records_summary() as any,
    ])
    rows.value = list.list
    total.value = list.total
    summary.value = stats
  } finally {
    loading.value = false
  }
}

async function load_subjects() {
  const data: any = await list_subjects({ page: 1, page_size: 100 })
  subjects.value = data.list
}

onMounted(async () => {
  await load_subjects()
  await load()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">学习记录</h2>
    <p class="page-sub">访问过的课程与点亮进度，只增不删</p>

    <div class="stat-grid">
      <div class="stat">
        <div class="label">访问课程</div>
        <div class="value">{{ summary.visited_count }}</div>
      </div>
      <div class="stat">
        <div class="label">已点亮</div>
        <div class="value">{{ summary.completed_count }}</div>
      </div>
      <div class="stat">
        <div class="label">涉及学科</div>
        <div class="value">{{ summary.subject_count }}</div>
      </div>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
      <el-select
        v-model="query.subject_id"
        placeholder="全部学科"
        clearable
        style="width: 180px"
        @change="query.page = 1; load()"
      >
        <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <span class="meta-row" style="font-size: 13px">共 {{ total }} 条</span>
    </div>

    <div v-if="rows.length" class="card">
      <div v-for="item in rows" :key="item.course_id + item.visited_at" class="record-row">
        <div>
          <div class="title">{{ item.course_title }}</div>
          <div class="sub">{{ item.subject_name }} · {{ format_time(item.visited_at) }}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px">
          <span v-if="item.is_completed" class="tag-soft tag-done">已点亮</span>
          <span v-else class="tag-soft">未点亮</span>
          <el-button size="small" @click="router.push(`/subject/${item.subject_id}`)">去学习</el-button>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">还没有学习记录，去首页挑个学科开始吧</div>
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
