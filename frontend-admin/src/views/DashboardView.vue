<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetch_dashboard } from '../api/admin'

const loading = ref(false)
const summary = ref<Record<string, any>>({
  total_users: 0,
  today_registered: 0,
  today_active: 0,
  week_active: 0,
  week_registered: 0,
  register_trend: [],
})

const max_count = computed(() => {
  const list = summary.value.register_trend || []
  return Math.max(1, ...list.map((item: any) => item.count))
})

function bar_height(count: number) {
  return `${Math.max(3, Math.round((count / max_count.value) * 100))}%`
}

async function load() {
  loading.value = true
  try {
    summary.value = (await fetch_dashboard()) as any
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h2>数据看板</h2>
        <p>只统计学员规模与活跃；不发散到学习、刷题与面试数据</p>
      </div>
      <el-button size="small" @click="load">刷新</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="label">累计注册学员</div>
        <div class="value">{{ summary.total_users }}</div>
      </div>
      <div class="stat-card">
        <div class="label">今日新增</div>
        <div class="value">{{ summary.today_registered }}</div>
      </div>
      <div class="stat-card">
        <div class="label">今日活跃</div>
        <div class="value">{{ summary.today_active }}</div>
      </div>
      <div class="stat-card">
        <div class="label">近 7 日活跃</div>
        <div class="value">{{ summary.week_active }}</div>
      </div>
    </div>

    <div class="card-block" style="margin-top: 16px">
      <div class="page-head" style="margin-bottom: 4px">
        <div>
          <h2 style="font-size: 16px">近 7 日新增注册</h2>
          <p>按北京时间自然日归集</p>
        </div>
        <span class="muted">近 7 日合计 {{ summary.week_registered }}</span>
      </div>

      <div class="trend">
        <div v-for="item in summary.register_trend" :key="item.date" class="col">
          <div class="bar" :style="{ height: bar_height(item.count) }">
            <span>{{ item.count }}</span>
          </div>
          <div class="day">{{ item.date.slice(5) }}</div>
        </div>
      </div>

      <el-empty v-if="!summary.register_trend.length" description="暂无数据" />
    </div>
  </div>
</template>
