<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { interview_quota, list_interviews, list_subjects, start_interview } from '../api/student'
import AiLoadingDialog from '../components/AiLoadingDialog.vue'

const router = useRouter()

const loading = ref(false)
const starting_id = ref('')
const ai_loading = ref(false)
// 出题要等 20–60 秒，把已等待秒数显示出来，避免用户以为卡死
const elapsed = ref(0)
let elapsed_timer: number | undefined

function start_elapsed() {
  elapsed.value = 0
  if (elapsed_timer) window.clearInterval(elapsed_timer)
  elapsed_timer = window.setInterval(() => {
    elapsed.value += 1
  }, 1000)
}

function stop_elapsed() {
  if (elapsed_timer) window.clearInterval(elapsed_timer)
  elapsed_timer = undefined
}
const quota = reactive({ daily_limit: 3, used: 0, remaining: 3, reset_at: '' })
const subjects = ref<any[]>([])
const history = ref<any[]>([])

const STATUS_TEXT: Record<number, string> = { 1: '进行中', 2: '已完成', 3: '已超时', 4: '提前结束' }

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function reset_text() {
  if (!quota.reset_at) return ''
  const date = new Date(quota.reset_at)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')} 重置`
}

async function load() {
  loading.value = true
  try {
    const [quota_data, subject_data, history_data] = (await Promise.all([
      interview_quota(),
      list_subjects({ page: 1, page_size: 50 }),
      list_interviews({ page: 1, page_size: 5 }),
    ])) as any[]
    Object.assign(quota, quota_data)
    subjects.value = subject_data.list
    history.value = history_data.list
  } finally {
    loading.value = false
  }
}

async function start(item: any) {
  if (quota.remaining <= 0) {
    ElMessage.warning('今日面试次数已用完，明天再来')
    return
  }
  try {
    await ElMessageBox.confirm(
      `开始「${item.name}」的模拟面试？共 5 道题、约 15 分钟。发起即计一次额度，中途退出不退还。`,
      '确认开始',
      { confirmButtonText: '开始面试', cancelButtonText: '再想想', type: 'info' },
    )
  } catch {
    return
  }

  starting_id.value = item.id
  ai_loading.value = true
  start_elapsed()
  try {
    const data: any = await start_interview(item.id)
    router.push(`/interview/${data.id}`)
  } finally {
    stop_elapsed()
    starting_id.value = ''
    ai_loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(stop_elapsed)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">AI 模拟面试</h2>
    <p class="page-sub">选一个学科，面试官会从该学科的资料库里出 5 道题，逐题作答并现场点评</p>

    <div class="card quota-card">
      <div class="quota-item">
        <div class="label">今日额度</div>
        <div class="value">{{ quota.daily_limit }} 次</div>
      </div>
      <div class="quota-item">
        <div class="label">已使用</div>
        <div class="value">{{ quota.used }}</div>
      </div>
      <div class="quota-item">
        <div class="label">剩余</div>
        <div class="value" :class="{ empty: quota.remaining === 0 }">{{ quota.remaining }}</div>
      </div>
      <div class="quota-reset">{{ reset_text() }}</div>
    </div>

    <AiLoadingDialog
      v-model="ai_loading"
      title="AI 正在出题"
      hint="从资料库检索并生成 5 道题，通常 10–30 秒"
      :elapsed="elapsed"
      :slow_after="45"
    />

    <h3 class="section-title">选择面试学科</h3>
    <div v-if="subjects.length" class="subject-grid">
      <div v-for="item in subjects" :key="item.id" class="subject-card" style="cursor: default">
        <div class="head">
          <span class="icon">{{ item.icon || '📘' }}</span>
          <h3>{{ item.name }}</h3>
        </div>
        <div class="desc">{{ item.description || '暂无简介' }}</div>
        <div class="meta-row" style="margin-bottom: 12px">
          <span>{{ item.course_count }} 门课程</span>
          <span>资料库出题</span>
        </div>
        <el-button
          type="primary"
          style="width: 100%"
          :loading="starting_id === item.id"
          :disabled="quota.remaining <= 0 || !!starting_id"
          @click="start(item)"
        >
          {{ starting_id === item.id ? `正在出题 ${elapsed}s` : '开始面试' }}
        </el-button>
      </div>
    </div>
    <div v-else-if="!loading" class="card">
      <div class="empty-box">还没有上架学科，先去管理端配置</div>
    </div>

    <template v-if="history.length">
      <h3 class="section-title">最近面试</h3>
      <div class="card">
        <div v-for="item in history" :key="item.id" class="record-row">
          <div>
            <div class="title">
              {{ item.subject_name || (item.source === 2 ? '简历面试' : '学科面试') }}
            </div>
            <div class="sub">
              {{ format_time(item.started_at) }} · {{ item.question_count }} 题
              <span class="tag-soft" :class="{ 'tag-done': item.status === 2 }">{{ STATUS_TEXT[item.status] }}</span>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 10px">
            <span v-if="item.total_score !== null" class="score-text">{{ item.total_score }} 分</span>
            <el-button size="small" @click="router.push(item.status === 1 ? `/interview/${item.id}` : `/interview/${item.id}/report`)">
              {{ item.status === 1 ? '继续' : '查看报告' }}
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.quota-card {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-bottom: 22px;
  position: relative;
}

.quota-item .label {
  font-size: 12px;
  color: var(--muted);
}

.quota-item .value {
  font-size: 22px;
  font-weight: 600;
  margin-top: 4px;
}

.quota-item .value.empty {
  color: #e5484d;
}

.quota-reset {
  margin-left: auto;
  font-size: 12px;
  color: var(--muted);
}

.starting-tip {
  background: #fff8e6;
  border: 1px solid #ffe1a8;
  color: #96650a;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  margin: 24px 0 12px;
}

.score-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand);
}
</style>
