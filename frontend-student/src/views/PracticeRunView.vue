<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetch_practice_paper, submit_paper } from '../api/student'
import { is_code_text } from '../utils/format'
import AiLoadingDialog from '../components/AiLoadingDialog.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const ai_loading = ref(false)
const error_message = ref('')
// 只有点了「开始组卷」才真正抽题，避免一进页面就随机组卷
const started = ref(false)
const paper = ref<any>({ questions: [] })
const answers = reactive<Record<string, { option_keys: string[]; answer_text: string }>>({})

const TYPE_LABEL: Record<number, string> = { 1: '判断题', 2: '单选题', 3: '多选题', 4: '简答题' }

const subject_name = computed(() => String(route.query.name ?? ''))

const answered_count = computed(() =>
  (paper.value.questions || []).filter((item: any) => {
    const answer = answers[item.id]
    if (!answer) return false
    return item.type === 4 ? !!answer.answer_text.trim() : answer.option_keys.length > 0
  }).length,
)

function type_label(type: number) {
  return TYPE_LABEL[type] || '题目'
}

function reset_form() {
  for (const key of Object.keys(answers)) delete answers[key]
}

async function load() {
  loading.value = true
  error_message.value = ''
  try {
    paper.value = await fetch_practice_paper(String(route.params.subjectId))
    reset_form()
    for (const item of paper.value.questions || []) {
      answers[item.id] = { option_keys: [], answer_text: '' }
    }
    started.value = true
    return true
  } catch (err: any) {
    error_message.value = err?.message || '题目加载失败，请检查网络后重试'
    return false
  } finally {
    loading.value = false
  }
}

async function start() {
  await load()
}

// 已开始后可以重新抽一套（每次都是新的随机 20 题）
async function regroup() {
  await ElMessageBox.confirm('重新组卷会清空当前作答，确定继续？', '提示', { type: 'warning' })
  await load()
}

function pick_single(question_id: string, value: string) {
  answers[question_id].option_keys = [value]
}

async function submit() {
  if (!answered_count.value) {
    ElMessage.warning('至少作答一题再提交')
    return
  }
  const missing = paper.value.questions.length - answered_count.value
  if (missing > 0) {
    await ElMessageBox.confirm(
      `还有 ${missing} 题未作答，未作答按 0 分计，确定提交？`,
      '提示',
      { type: 'warning' },
    )
  }

  submitting.value = true
  ai_loading.value = true
  try {
    const payload = paper.value.questions.map((item: any) => ({
      question_id: item.id,
      option_keys: answers[item.id].option_keys,
      answer_text: item.type === 4 ? answers[item.id].answer_text : null,
    }))
    const result: any = await submit_paper(paper.value.subject_id, payload)
    ElMessage.success('判分完成')
    router.replace(`/paper/${result.id}`)
  } finally {
    submitting.value = false
    ai_loading.value = false
  }
}

// 同一路由切换学科（如从选择页连续点不同学科）时回到"未组卷"状态
watch(
  () => route.params.subjectId,
  () => {
    started.value = false
    paper.value = { questions: [] }
    error_message.value = ''
    reset_form()
  },
)
</script>

<template>
  <AiLoadingDialog
    v-model="ai_loading"
    title="AI 正在判分"
    hint="客观题即时判分，简答题由 AI 逐题批阅，一般 5–20 秒"
    :slow_after="25"
  />

  <div class="page" v-loading="loading">
    <!-- 第一阶段：进入页面不抽题，等用户点开始 -->
    <div v-if="!started" class="card start-card">
      <div class="start-head">
        <span class="start-icon">📝</span>
        <div>
          <h2 class="page-title" style="margin: 0">{{ subject_name || '刷题自测' }}</h2>
          <p class="page-sub" style="margin: 6px 0 0">
            随机抽取 20 道题（判断 / 单选 / 多选 / 简答混合），全部作答后一次性提交，提交后立即判分
          </p>
        </div>
      </div>

      <div v-if="error_message" class="empty-box" style="margin-top: 18px">
        {{ error_message }}
      </div>

      <div style="margin-top: 22px; display: flex; align-items: center; gap: 12px">
        <el-button type="primary" size="large" :loading="loading" @click="start">
          {{ error_message ? '重新组卷' : '开始组卷' }}
        </el-button>
        <el-button link @click="router.push('/practice')">换个学科</el-button>
      </div>
    </div>

    <!-- 第二阶段：已组卷 -->
    <template v-else>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <h2 class="page-title">{{ paper.subject_name || subject_name || '答题中' }}</h2>
          <p class="page-sub">
            共 {{ paper.question_count || 0 }} 题 · 满分 {{ paper.total_score || 0 }} 分 ·
            已作答 {{ answered_count }} 题
          </p>
        </div>
        <div style="display: flex; gap: 10px">
          <el-button :disabled="submitting" @click="regroup">重新组卷</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">
            {{ submitting ? 'AI 判分中…' : '交卷判分' }}
          </el-button>
        </div>
      </div>

      <div v-if="submitting" class="card" style="margin-bottom: 14px">
        <div class="empty-box">正在判分，简答题需要 AI 逐题批阅，请稍候（一般 5-20 秒）</div>
      </div>

      <div
        v-for="(item, index) in paper.questions"
        :key="item.id"
        class="card"
        style="margin-bottom: 14px"
      >
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px">
          <span class="q-index">{{ index + 1 }}</span>
          <span class="tag-soft">{{ type_label(item.type) }}</span>
          <span class="meta-row" style="font-size: 12px">{{ item.score }} 分</span>
        </div>

        <p class="q-title" :class="{ 'q-code': is_code_text(item.title) }">{{ item.title }}</p>

        <!-- 判断题 / 单选题 -->
        <el-radio-group
          v-if="item.type === 1 || item.type === 2"
          :model-value="answers[item.id]?.option_keys[0] || ''"
          @update:model-value="(value: any) => pick_single(item.id, String(value))"
          style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start"
        >
          <el-radio v-for="option in item.options" :key="option.option_key" :value="option.option_key">
            {{ option.option_key }}. {{ option.content }}
          </el-radio>
        </el-radio-group>

        <!-- 多选题 -->
        <el-checkbox-group
          v-else-if="item.type === 3"
          v-model="answers[item.id].option_keys"
          style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start"
        >
          <el-checkbox
            v-for="option in item.options"
            :key="option.option_key"
            :value="option.option_key"
          >
            {{ option.option_key }}. {{ option.content }}
          </el-checkbox>
        </el-checkbox-group>

        <!-- 简答题 -->
        <el-input
          v-else
          v-model="answers[item.id].answer_text"
          type="textarea"
          :rows="4"
          maxlength="5000"
          show-word-limit
          placeholder="请作答，AI 会按参考要点评分"
        />
      </div>

      <div v-if="!paper.questions?.length" class="card">
        <div class="empty-box">该学科题池为空，请联系管理员补充题目</div>
      </div>

      <div v-else style="text-align: center; margin-top: 8px">
        <el-button type="primary" size="large" :loading="submitting" @click="submit">
          {{ submitting ? 'AI 判分中…' : `交卷判分（已答 ${answered_count} / ${paper.questions.length}）` }}
        </el-button>
      </div>
    </template>
  </div>
</template>
