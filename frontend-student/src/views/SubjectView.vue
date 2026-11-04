<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  complete_course,
  fetch_subject,
  record_visit,
  uncomplete_course,
} from '../api/student'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const subject = ref<any>({ nodes: [] })
const busy_id = ref('')

const subject_id = computed(() => String(route.params.id))

const recommended_id = computed(() => subject.value.recommended_course_id || '')

async function load() {
  loading.value = true
  try {
    subject.value = await fetch_subject(subject_id.value)
  } finally {
    loading.value = false
  }
}

function node_state(node: any) {
  if (node.is_completed) return 'done'
  if (node.id === recommended_id.value) return 'next'
  return ''
}

function watch(node: any) {
  // 先同步打开，避免异步后被浏览器拦截
  window.open(node.bilibili_url, '_blank', 'noopener')
  record_visit(node.id).catch(() => {
    // 访问流水失败不影响观看
  })
}

async function toggle(node: any) {
  busy_id.value = node.id
  try {
    if (node.is_completed) {
      await uncomplete_course(node.id)
      ElMessage.success('已取消点亮')
    } else {
      await complete_course(node.id)
      ElMessage.success('节点已点亮')
    }
    await load()
  } finally {
    busy_id.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">
      {{ subject.icon || '📘' }} {{ subject.name }}
    </h2>
    <p class="page-sub">{{ subject.description || '按顺序学习，学完点亮节点' }}</p>

    <div class="card" style="margin-bottom: 18px; display: flex; align-items: center; gap: 18px">
      <div style="flex: 1">
        <div class="meter" style="margin: 0 0 6px">
          <span :style="{ width: `${subject.progress_percent || 0}%` }" />
        </div>
        <div class="meta-row">
          <span>已点亮 {{ subject.completed_count || 0 }} / {{ subject.course_count || 0 }}</span>
          <span>{{ subject.progress_percent || 0 }}%</span>
        </div>
      </div>
      <el-button type="primary" @click="router.push(`/practice/${subject_id}`)">刷题自测</el-button>
    </div>

    <div v-if="subject.nodes && subject.nodes.length" class="timeline">
      <div v-for="node in subject.nodes" :key="node.id" class="node" :class="node_state(node)">
        <div class="dot">{{ node.is_completed ? '✓' : node.sort_order }}</div>
        <div class="body">
          <h4>
            {{ node.title }}
            <span v-if="node.is_completed" class="tag-soft tag-done">已点亮</span>
            <span v-else-if="node.id === recommended_id" class="tag-soft tag-next">推荐下一课</span>
          </h4>
          <p class="desc">{{ node.description || '暂无说明' }}</p>
          <div class="actions">
            <span class="meta-row" style="min-width: 60px">{{ node.duration_minutes }} 分钟</span>
            <el-button size="small" type="primary" @click="watch(node)">去 B 站观看</el-button>
            <el-button
              size="small"
              :type="node.is_completed ? 'default' : 'success'"
              :loading="busy_id === node.id"
              @click="toggle(node)"
            >
              {{ node.is_completed ? '取消点亮' : '点亮节点' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">该学科还没有上架课程</div>
    </div>
  </div>
</template>
