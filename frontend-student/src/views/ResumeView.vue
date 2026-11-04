<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  delete_resume,
  fetch_current_resume,
  interview_quota,
  start_resume_interview,
  upload_resume,
} from '../api/student'
import AiLoadingDialog from '../components/AiLoadingDialog.vue'

const router = useRouter()

const loading = ref(true)
const uploading = ref(false)
const starting = ref(false)
const ai_loading = ref(false)
const elapsed = ref(0)
const resume = ref<any>(null)
const quota = ref<any>({ remaining: 0, daily_limit: 3, used: 0 })
const file_input = ref<HTMLInputElement | null>(null)

let poll_timer: number | undefined
let elapsed_timer: number | undefined

const STATUS_TEXT: Record<number, string> = {
  1: '排队中',
  2: '解析中',
  3: '已就绪',
  4: '解析失败',
}

const status_type = computed(() => {
  const status = resume.value?.status
  if (status === 3) return 'success'
  if (status === 4) return 'danger'
  return 'warning'
})

function size_text(bytes: number) {
  if (!bytes) return '-'
  return bytes > 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} KB`
}

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

async function load() {
  try {
    const data: any = await fetch_current_resume()
    resume.value = data
    // 解析中：3 秒轮询一次，完成后自动停
    if (data.status === 2 || data.status === 1) {
      schedule_poll()
    } else {
      stop_poll()
    }
  } catch {
    // 404 表示还没上传，不是错误
    resume.value = null
    stop_poll()
  } finally {
    loading.value = false
  }
}

async function load_quota() {
  // 简历面试与学科面试共用同一份每日配额，这里必须读真实值
  try {
    const data: any = await interview_quota()
    quota.value = data
  } catch {
    // 配额接口失败不影响上传与解析，保留默认值
  }
}

function schedule_poll() {
  stop_poll()
  poll_timer = window.setInterval(load, 3000)
}

function stop_poll() {
  if (poll_timer) {
    window.clearInterval(poll_timer)
    poll_timer = undefined
  }
}

function pick_file() {
  file_input.value?.click()
}

async function on_file_change(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return

  if (!file.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.warning('请上传 PDF 文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 10MB')
    return
  }

  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const data: any = await upload_resume(form)
    resume.value = { ...data, failure_reason: '', parsed_at: null }
    ElMessage.success('上传成功，正在解析')
    schedule_poll()
  } finally {
    uploading.value = false
  }
}

async function remove_resume() {
  try {
    await ElMessageBox.confirm('删除后简历切片一并清除，确定？', '删除简历', {
      type: 'warning',
    })
  } catch {
    return
  }
  await delete_resume()
  resume.value = null
  stop_poll()
  ElMessage.success('已删除')
}

async function start_interview() {
  if (starting.value) return
  starting.value = true
  ai_loading.value = true
  start_elapsed()
  try {
    const data: any = await start_resume_interview()
    router.push(`/interview/${data.id}`)
  } finally {
    stop_elapsed()
    ai_loading.value = false
    starting.value = false
  }
}

onMounted(() => {
  void load()
  void load_quota()
})
onBeforeUnmount(() => {
  stop_poll()
  stop_elapsed()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h2 class="page-title">简历面试</h2>
        <p class="page-sub">
          上传简历后，AI 会围绕你的项目经历提问——问职责、问选型、问难点，而不是通用题库
        </p>
      </div>
    </div>

    <AiLoadingDialog
      v-model="ai_loading"
      title="AI 正在出题"
      hint="读取你的简历切片并向面试官模型提问，通常 10–30 秒"
      :elapsed="elapsed"
      :slow_after="45"
    />

    <input
      ref="file_input"
      type="file"
      accept="application/pdf,.pdf"
      style="display: none"
      @change="on_file_change"
    />

    <!-- 未上传 -->
    <div v-if="!resume" class="card upload-card">
      <div class="upload-icon">📄</div>
      <div class="upload-title">上传你的简历</div>
      <div class="upload-sub">
        支持 PDF，不超过 10MB；解析约 5–15 秒，完成后即可发起简历面试
      </div>
      <el-button type="primary" size="large" :loading="uploading" @click="pick_file">
        {{ uploading ? '上传中…' : '选择 PDF 文件' }}
      </el-button>
      <div class="upload-tip">
        建议用文字版 PDF。扫描件（图片）无法提取文字，会提示解析失败
      </div>
    </div>

    <!-- 已上传 -->
    <div v-else class="card">
      <div class="file-row">
        <div class="file-icon">📄</div>
        <div class="file-info">
          <div class="file-name">{{ resume.file_name }}</div>
          <div class="file-meta">
            {{ size_text(resume.file_size) }}
            <span class="sep">·</span>
            <el-tag size="small" :type="status_type">{{ STATUS_TEXT[resume.status] || '未知' }}</el-tag>
            <template v-if="resume.parsed_at">
              <span class="sep">·</span>
              <span>{{ resume.parsed_at }}</span>
            </template>
          </div>
        </div>
        <div class="file-actions">
          <el-button size="small" :disabled="uploading" @click="pick_file">重新上传</el-button>
          <el-button size="small" type="danger" plain @click="remove_resume">删除</el-button>
        </div>
      </div>

      <div v-if="resume.status === 4" class="fail-box">
        <b>解析失败：</b>{{ resume.failure_reason || '未知原因' }}
        <div class="fail-tip">
          常见原因：扫描件（图片）没有文字层、PDF 已加密、内容过少。换一份文字版 PDF 再试。
        </div>
      </div>

      <div v-else-if="resume.status !== 3" class="parsing-box">
        <span class="pulse-dot" />
        正在解析简历（提取文字 → 切片 → 向量化），稍等几秒…
      </div>

      <div class="start-row">
        <el-button
          type="primary"
          size="large"
          :disabled="resume.status !== 3 || starting"
          :loading="starting"
          @click="start_interview"
        >
          {{ starting ? '正在出题…' : '开始简历面试' }}
        </el-button>
        <span class="start-hint">
          5 题 · 15 分钟 · 发起即扣 1 次额度（今日剩余 {{ quota.remaining }} 次）
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-card {
  text-align: center;
  padding: 46px 24px;
}

.upload-icon {
  font-size: 42px;
  margin-bottom: 12px;
}

.upload-title {
  font-size: 17px;
  font-weight: 600;
  color: #1f2a44;
  margin-bottom: 8px;
}

.upload-sub {
  font-size: 13px;
  color: #7a8699;
  line-height: 1.7;
  margin-bottom: 22px;
}

.upload-tip {
  margin-top: 18px;
  font-size: 12px;
  color: #9aa5b8;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #e7ebf3;
}

.file-icon {
  font-size: 30px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2a44;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: #8491a5;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sep {
  color: #ccd4e0;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.fail-box {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fdeaea;
  border: 1px solid #f4c9c9;
  color: #a33a3a;
  font-size: 13px;
  line-height: 1.7;
}

.fail-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #b06a6a;
}

.parsing-box {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fff8e6;
  border: 1px solid #ffe1a8;
  color: #96702a;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f0a020;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.start-row {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.start-hint {
  font-size: 12px;
  color: #8491a5;
}
</style>
