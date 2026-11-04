<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetch_interview,
  fetch_question_audio,
  fetch_verdict_audio,
  finish_interview,
  request_follow_up,
  submit_interview_answer,
  transcribe_answer,
} from '../api/student'
import AiLoadingDialog from '../components/AiLoadingDialog.vue'
import { use_pcm_recorder } from '../utils/recorder'

const route = useRoute()
const router = useRouter()

const session_id = computed(() => String(route.params.id))
const loading = ref(true)
const submitting = ref(false)
const following = ref(false)
const finishing = ref(false)

const session = ref<any>({ questions: [], status: 1 })
const current_index = ref(1)
const answer_text = ref('')
const remaining = ref(0)
const first_load = ref(true)
const result_dialog = ref(false)
const final_result = ref<any>(null)

// 单题结算弹窗：答完先看点评，点「开始下一道」才跳
const answer_dialog = ref(false)
const answer_result = ref<any>(null)

// 面试官结语：结算后后台合成，前端轮询等待
const verdict_url = ref('')
const verdict_pending = ref(false)
const verdict_blocked = ref(false)
const verdict_el = ref<HTMLAudioElement | null>(null)
let verdict_timer: number | undefined

function reset_verdict() {
  if (verdict_url.value) URL.revokeObjectURL(verdict_url.value)
  verdict_url.value = ''
  verdict_pending.value = false
  verdict_blocked.value = false
  if (verdict_timer) {
    window.clearTimeout(verdict_timer)
    verdict_timer = undefined
  }
}

async function play_verdict_audio(attempt = 1) {
  if (verdict_url.value) return
  verdict_pending.value = true
  try {
    const url = await fetch_verdict_audio(session_id.value)
    verdict_pending.value = false
    if (verdict_url.value) URL.revokeObjectURL(verdict_url.value)
    verdict_url.value = url
    await nextTick()
    const player = verdict_el.value
    if (player) {
      try {
        await player.play()
      } catch {
        verdict_blocked.value = true
      }
    }
  } catch {
    // 后台合成约 8 秒，这里 1.5 秒一轮，最多等 12 秒
    if (attempt <= 8) {
      if (verdict_timer) window.clearTimeout(verdict_timer)
      verdict_timer = window.setTimeout(() => play_verdict_audio(attempt + 1), 1500)
    } else {
      verdict_pending.value = false
    }
  }
}

// 追问：每题最多一次，答完即锁
const follow_up_open = ref(false)
const follow_up_answered = ref<number[]>([])

const audio_url = ref('')
const audio_playing = ref(false)
const audio_blocked = ref(false)
const audio_pending = ref(false)
const audio_el = ref<HTMLAudioElement | null>(null)

let timer: number | undefined
let jump_timer: number | undefined
let audio_retry_timer: number | undefined

// AI 等待弹窗（评分、追问都走大模型，必须让用户看到进度）
const ai_loading = ref(false)
const ai_title = ref('')
const ai_hint = ref('')
const ai_elapsed = ref(0)
let ai_timer: number | undefined

function open_ai(title: string, hint: string) {
  ai_title.value = title
  ai_hint.value = hint
  ai_elapsed.value = 0
  ai_loading.value = true
  if (ai_timer) window.clearInterval(ai_timer)
  ai_timer = window.setInterval(() => {
    ai_elapsed.value += 1
  }, 1000)
}

function close_ai() {
  ai_loading.value = false
  if (ai_timer) {
    window.clearInterval(ai_timer)
    ai_timer = undefined
  }
}

const questions = computed(() => session.value.questions || [])
const current = computed(
  () => questions.value.find((item: any) => item.question_index === current_index.value) || null,
)
const answered_count = computed(() => questions.value.filter((item: any) => item.is_answered).length)
const finished = computed(() => session.value.status !== 1)
const has_next = computed(() =>
  questions.value.some((item: any) => !item.is_answered && item.question_index !== current_index.value),
)

const time_text = computed(() => {
  const minutes = Math.floor(remaining.value / 60)
  const seconds = remaining.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
const urgent = computed(() => remaining.value > 0 && remaining.value <= 120)
const expired = computed(() => remaining.value === 0 && !finished.value)

/** 本场是否还能对当前题输入：未答过，或追问刚打开 */
const can_answer = computed(() => {
  if (finished.value || expired.value || submitting.value) return false
  const item = current.value
  if (!item) return false
  if (!item.is_answered) return true
  return follow_up_open.value && !follow_up_answered.value.includes(item.question_index)
})

const hint_text = computed(() => {
  if (finished.value) return '本场面试已结束'
  if (submitting.value) return '已收到回答，AI 正在评估…'
  if (audio_pending.value) return '语音准备中，马上开始播报…'
  if (expired.value) return '时间到，请结束本场面试'
  if (can_answer.value) return follow_up_open.value ? '请回答面试官的追问' : '请用文字作答'
  return '本题已作答，不可修改'
})

const orb_icon = computed(() => {
  if (submitting.value) return '🤖'
  if (finished.value) return '✅'
  if (audio_playing.value) return '🎙'
  return '🎤'
})

function start_timer(seconds: number) {
  remaining.value = seconds
  if (timer) window.clearInterval(timer)
  timer = window.setInterval(() => {
    if (remaining.value > 0) remaining.value -= 1
    if (remaining.value === 0 && timer) window.clearInterval(timer)
  }, 1000)
}

function reset_audio() {
  if (audio_url.value) URL.revokeObjectURL(audio_url.value)
  audio_url.value = ''
  audio_playing.value = false
  audio_blocked.value = false
  audio_pending.value = false
  if (audio_retry_timer) {
    window.clearTimeout(audio_retry_timer)
    audio_retry_timer = undefined
  }
}

async function play_question_audio(index: number, attempt = 1) {
  if (current_index.value !== index) return
  audio_playing.value = false
  try {
    const url = await fetch_question_audio(session_id.value, index)
    if (current_index.value !== index) {
      URL.revokeObjectURL(url)
      return
    }
    audio_pending.value = false
    if (audio_url.value) URL.revokeObjectURL(audio_url.value)
    audio_url.value = url
    await nextTick()
    const player = audio_el.value
    if (player) {
      try {
        await player.play()
        audio_playing.value = true
      } catch {
        audio_blocked.value = true
      }
    }
  } catch {
    // 发起接口已不再等语音，后台合成约需 7 秒：这里轮询等待，而不是放弃
    if (attempt <= 6 && current_index.value === index) {
      audio_pending.value = true
      if (audio_retry_timer) window.clearTimeout(audio_retry_timer)
      audio_retry_timer = window.setTimeout(
        () => play_question_audio(index, attempt + 1),
        1500,
      )
    } else {
      audio_pending.value = false
    }
  }
}

function go_to(index: number) {
  // 切题前先停录音，避免音轨泄漏和串题
  if (recording.value) void stop_record()
  if (jump_timer) {
    window.clearTimeout(jump_timer)
    jump_timer = undefined
  }
  current_index.value = index
  follow_up_open.value = false
  const item = questions.value.find((row: any) => row.question_index === index)
  answer_text.value = ''
  reset_audio()
  play_question_audio(index)
  void item
}

function go_next() {
  const next = questions.value.find((item: any) => !item.is_answered)
  if (next) go_to(next.question_index)
}

// 语音作答：16k PCM 录音 → 按段上传识别 → 文本追加进作答框
const recording = ref(false)
const record_seconds = ref(0)
const asr_pending = ref(false)
const segment_texts = ref<string[]>([])
let recorder: ReturnType<typeof use_pcm_recorder> | null = null
let record_timer: number | undefined
let pending_segments = 0

function merge_segments() {
  const text = segment_texts.value.filter(Boolean).join('，')
  segment_texts.value = []
  if (!text) return false
  answer_text.value = answer_text.value ? `${answer_text.value}\n${text}` : text
  return true
}

async function upload_segment(wav: Blob, index: number) {
  pending_segments += 1
  asr_pending.value = true
  try {
    const text = await transcribe_answer(session_id.value, wav)
    if (text) segment_texts.value[index] = text
  } catch {
    ElMessage.warning('这段没识别成功，可以重录或改用打字')
  } finally {
    pending_segments -= 1
    if (pending_segments <= 0) {
      asr_pending.value = false
      // 停止录音后最后一段回来时，统一并入作答框
      if (!recording.value) merge_segments()
    }
  }
}

async function start_record() {
  if (!can_answer.value) return
  try {
    if (!recorder) {
      recorder = use_pcm_recorder({
        max_seconds: 55,
        on_segment: (wav, index) => {
          void upload_segment(wav, index)
        },
      })
    }
    segment_texts.value = []
    pending_segments = 0
    await recorder.start()
    recording.value = true
    record_seconds.value = 0
    if (record_timer) window.clearInterval(record_timer)
    record_timer = window.setInterval(() => {
      record_seconds.value = recorder ? recorder.seconds() : 0
    }, 500)
  } catch {
    ElMessage.error('无法使用麦克风：请在浏览器地址栏允许麦克风权限后重试')
  }
}

async function stop_record() {
  if (!recorder || !recording.value) return
  await recorder.stop()
  recording.value = false
  if (record_timer) {
    window.clearInterval(record_timer)
    record_timer = undefined
  }
  if (pending_segments <= 0) {
    const merged = merge_segments()
    if (!merged && !answer_text.value.trim()) {
      ElMessage.warning('没听清，请再说一次或改用打字')
    }
  }
}

async function load() {
  loading.value = true
  try {
    const data: any = await fetch_interview(session_id.value)
    session.value = data
    start_timer(data.remaining_seconds || 0)
    if (first_load.value) {
      first_load.value = false
      if (data.status === 1) {
        go_to(data.current_index || 1)
      } else {
        // 重进已结束的会话：直接展示成绩，并尝试播放结语
        final_result.value = data
        result_dialog.value = true
        play_verdict_audio()
      }
    } else if (data.status !== 1) {
      final_result.value = data
    }
  } finally {
    loading.value = false
  }
}

async function submit() {
  // 录音中直接提交会漏掉尾段音频，先停掉
  if (recording.value) await stop_record()

  const text = answer_text.value.trim()
  if (!text) {
    ElMessage.warning('先写点内容再提交')
    return
  }

  const answering_follow_up = follow_up_open.value
  submitting.value = true
  open_ai(
    answering_follow_up ? 'AI 正在评估追问回答' : 'AI 正在评分',
    answering_follow_up
      ? '结合追问与前一次作答重新计算得分，约 5–15 秒'
      : '分析你的回答要点并给出分数与点评，约 5–15 秒',
  )
  try {
    const data: any = await submit_interview_answer(session_id.value, current_index.value, {
      answer_mode: 2,
      answer_text: text,
      is_follow_up: answering_follow_up,
    })
    if (answering_follow_up) {
      follow_up_answered.value = [...follow_up_answered.value, current_index.value]
      follow_up_open.value = false
    }
    answer_text.value = ''

    await load()

    // 不自动跳题：先让学员看分数与点评，点「开始下一道」再走
    answer_result.value = data
    answer_dialog.value = true
  } finally {
    submitting.value = false
    close_ai()
  }
}

function next_after_dialog() {
  answer_dialog.value = false
  go_next()
}

function finish_after_dialog() {
  answer_dialog.value = false
  do_finish()
}

async function follow_up() {
  following.value = true
  open_ai('AI 正在思考追问', '根据你的回答生成一个更深入的问题，约 5–15 秒')
  try {
    const data: any = await request_follow_up(session_id.value, current_index.value)
    const item = current.value
    if (item) item.follow_up_text = data.follow_up_text
    follow_up_open.value = true
    ElMessage.info('面试官追问了一句')
  } finally {
    following.value = false
    close_ai()
  }
}

async function do_finish() {
  finishing.value = true
  try {
    final_result.value = await finish_interview(session_id.value, 2)
    result_dialog.value = true
    await load()
    // 结语由后台生成，这里开始轮询拉取
    play_verdict_audio()
  } finally {
    finishing.value = false
  }
}

async function finish() {
  try {
    await ElMessageBox.confirm(
      '确定结束本场面试？未作答的题目按 0 分计入总分。',
      '结束面试',
      { confirmButtonText: '结束并查看结果', cancelButtonText: '继续作答', type: 'warning' },
    )
  } catch {
    return
  }
  await do_finish()
}

function show_result() {
  result_dialog.value = true
  if (!verdict_url.value) play_verdict_audio()
}

function open_report() {
  result_dialog.value = false
  router.push(`/interview/${session_id.value}/report`)
}

function back_to_list() {
  router.replace('/interview')
}

async function exit_confirm() {
  if (finished.value) {
    back_to_list()
    return
  }
  try {
    await ElMessageBox.confirm('退出后本场仍在计时，可稍后从面试列表继续。', '退出面试', {
      confirmButtonText: '退出',
      cancelButtonText: '继续作答',
      type: 'warning',
    })
  } catch {
    return
  }
  back_to_list()
}

onMounted(load)
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
  if (jump_timer) window.clearTimeout(jump_timer)
  if (ai_timer) window.clearInterval(ai_timer)
  if (record_timer) window.clearInterval(record_timer)
  recorder?.dispose()
  reset_audio()
  reset_verdict()
})
</script>

<template>
  <div class="iv-stage" v-loading="loading" element-loading-background="rgba(5, 6, 13, .85)">
    <!-- 顶部状态 -->
    <header class="iv-top">
      <button class="iv-exit" @click="exit_confirm">← 退出</button>

      <div class="iv-dots">
        <span
          v-for="item in questions"
          :key="item.question_index"
          class="iv-dot"
          :class="{ done: item.is_answered, active: item.question_index === current_index }"
          @click="go_to(item.question_index)"
        >
          {{ item.question_index }}
        </span>
      </div>

      <div class="iv-clock" :class="{ urgent }">{{ expired ? '已超时' : time_text }}</div>
    </header>

    <!-- 中央舞台 -->
    <main class="iv-center">
      <div class="ai-orb" :class="{ speaking: submitting || audio_playing }">
        <span>{{ orb_icon }}</span>
      </div>

      <div class="iv-hint">{{ hint_text }}</div>

      <div v-if="current" class="iv-question">{{ current.question_text }}</div>

      <div v-if="current?.follow_up_text" class="iv-follow">
        <b>追问：</b>{{ current.follow_up_text }}
      </div>

      <!-- 作答区：语音或打字 -->
      <template v-if="can_answer">
        <div class="record-bar">
          <button
            v-if="!recording"
            class="mic-btn"
            :disabled="asr_pending"
            @click="start_record"
          >
            🎤 语音作答
          </button>
          <template v-else>
            <span class="rec-dot" />
            <span class="rec-time" :class="{ warn: record_seconds >= 50 }">
              {{ record_seconds }}s
            </span>
            <div class="rec-wave">
              <i /><i /><i /><i /><i /><i />
            </div>
            <button class="mic-btn stop" @click="stop_record">停止并转写</button>
          </template>
          <span v-if="asr_pending" class="asr-hint">识别中…</span>
        </div>

        <textarea
          v-model="answer_text"
          class="iv-textarea"
          maxlength="5000"
          placeholder="语音作答后可直接修改文字，也可以自己打字"
        />
      </template>

      <!-- 已答：只读展示答案与点评 -->
      <div v-if="current?.is_answered && !can_answer" class="iv-answered">
        <div class="iv-answer-label">我的回答</div>
        <div class="iv-answer">{{ current.answer_text || '（未记录）' }}</div>
        <div class="iv-score-row">
          <span class="iv-score">{{ Math.round(current.score ?? 0) }}</span>
          <span class="iv-score-unit">分</span>
        </div>
        <div v-if="current.ai_comment" class="iv-comment">{{ current.ai_comment }}</div>
      </div>

      <button
        v-if="audio_blocked && audio_url"
        class="iv-replay"
        @click="audio_el?.play()"
      >
        浏览器拦截了自动播放，点此重听题目
      </button>
    </main>

    <!-- 底部按钮 -->
    <footer class="iv-bottom">
      <template v-if="finished">
        <button class="btn-light" @click="open_report">查看详细报告</button>
        <button class="btn-ghost" @click="show_result">结果概况</button>
        <button class="btn-ghost" @click="back_to_list">返回列表</button>
      </template>

      <template v-else-if="submitting">
        <button class="btn-light" disabled>AI 正在评估…</button>
      </template>

      <template v-else-if="can_answer">
        <button class="btn-light" :disabled="!answer_text.trim()" @click="submit">
          {{ follow_up_open ? '提交追问回答' : '提交回答' }}
        </button>
        <button v-if="audio_url" class="btn-ghost" @click="audio_el?.play()">重听题目</button>
      </template>

      <template v-else>
        <button v-if="has_next" class="btn-light" @click="go_next">下一题 →</button>
        <button v-else class="btn-light" :disabled="finishing" @click="finish">
          {{ finishing ? '结算中…' : '结束并查看结果' }}
        </button>
        <button
          v-if="current && !current.follow_up_text"
          class="btn-ghost"
          :disabled="following"
          @click="follow_up"
        >
          {{ following ? '思考中…' : 'AI 追问（还可 1 次）' }}
        </button>
      </template>
    </footer>

    <audio
      ref="audio_el"
      :src="audio_url"
      class="iv-audio"
      @play="audio_playing = true"
      @ended="audio_playing = false"
      @pause="audio_playing = false"
    />

    <AiLoadingDialog
      v-model="ai_loading"
      :title="ai_title"
      :hint="ai_hint"
      :elapsed="ai_elapsed"
      :slow_after="20"
    />

    <!-- 单题点评：看完再决定是否进入下一道 -->
    <el-dialog
      v-model="answer_dialog"
      width="420px"
      :show-close="false"
      :close-on-click-modal="false"
      align-center
    >
      <div class="answer-review">
        <div class="review-label">本题得分</div>
        <div class="review-score" :class="{ good: (answer_result?.score ?? 0) >= 60 }">
          {{ Math.round(answer_result?.score ?? 0) }}<span>分</span>
        </div>
        <div class="review-comment">{{ answer_result?.ai_comment || '暂无点评' }}</div>
      </div>
      <template #footer>
        <el-button v-if="has_next" type="primary" @click="next_after_dialog">
          开始下一道
        </el-button>
        <el-button v-else type="primary" @click="finish_after_dialog">
          结束并查看结果
        </el-button>
      </template>
    </el-dialog>

    <!-- 结果 -->
    <el-dialog v-model="result_dialog" width="420px" :show-close="false" align-center>
      <div class="verdict" :class="final_result?.passed ? 'pass' : 'fail'">
        <div class="verdict-badge">{{ final_result?.passed ? 'PASS' : 'FAIL' }}</div>
        <div class="verdict-score">{{ final_result?.total_score }}<span>分</span></div>
        <div class="verdict-text">{{ final_result?.summary }}</div>
        <div class="verdict-meta">
          答 {{ final_result?.answered_count }}/{{ final_result?.question_count }} 题
          · 用时 {{ final_result?.duration_seconds }} 秒
          · 通过线 {{ final_result?.pass_score }} 分
        </div>

        <div class="verdict-audio">
          <audio ref="verdict_el" :src="verdict_url" class="hidden-audio" />
          <span v-if="verdict_pending" class="verdict-audio-hint">
            面试官正在说最后一句话…
          </span>
          <button
            v-else-if="verdict_url"
            class="verdict-replay"
            @click="verdict_el?.play()"
          >
            {{ verdict_blocked ? '点击播放面试官结语' : '重播面试官结语' }}
          </button>
        </div>
      </div>
      <template #footer>
        <el-button @click="back_to_list">返回列表</el-button>
        <el-button type="primary" @click="open_report">查看详细报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 全屏黑色舞台：盖住整个视口，包含导航栏 */
.iv-stage {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  padding: 18px 22px 24px;
  color: #e8ecff;
  background:
    radial-gradient(900px 520px at 50% -10%, rgba(99, 102, 241, 0.28), transparent 62%),
    radial-gradient(700px 420px at 12% 105%, rgba(56, 189, 248, 0.16), transparent 60%),
    #05060d;
  overflow-y: auto;
}

.iv-stage::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(120, 140, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 140, 255, 0.05) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(circle at 50% 20%, #000 25%, transparent 72%);
  pointer-events: none;
}

.iv-top {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.iv-exit {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.16);
  color: #9aa6d0;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s ease;
}

.iv-exit:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.4);
}

.iv-dots {
  display: flex;
  gap: 8px;
}

.iv-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: #6b76a0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  cursor: pointer;
  transition: all 0.18s ease;
}

.iv-dot.done {
  color: #4ade9b;
  border-color: rgba(74, 222, 155, 0.42);
  background: rgba(74, 222, 155, 0.1);
}

.iv-dot.active {
  color: #fff;
  border-color: #818cf8;
  background: rgba(129, 140, 248, 0.22);
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.iv-clock {
  font-size: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #7dd3fc;
  min-width: 74px;
  text-align: right;
}

.iv-clock.urgent {
  color: #fb7185;
}

.iv-center {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 26px 0;
  text-align: center;
}

/* AI 球体：原型同款紫蓝渐变 + 呼吸光晕 */
.ai-orb {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 32px;
  background: linear-gradient(135deg, #6366f1, #4338ca);
  box-shadow: 0 0 0 12px rgba(99, 102, 241, 0.12);
  animation: breathe 3.4s ease-in-out infinite;
}

.ai-orb.speaking {
  animation: orb_pulse 1.1s infinite;
}

@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes orb_pulse {
  0% { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0.14); }
  50% { box-shadow: 0 0 0 24px rgba(99, 102, 241, 0.07); }
  100% { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0.14); }
}

.iv-hint {
  font-size: 13px;
  color: #8d97bd;
  letter-spacing: 0.03em;
}

.iv-question {
  font-size: 19px;
  line-height: 1.75;
  font-weight: 600;
  max-width: 660px;
  color: #f2f5ff;
  animation: fade_up 0.3s ease both;
}

@keyframes fade_up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

.iv-follow {
  max-width: 640px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.13);
  font-size: 14px;
  line-height: 1.7;
  color: #d6dcf7;
  text-align: left;
}

/* 录音条 */
.record-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.mic-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(129, 140, 248, 0.4);
  background: rgba(129, 140, 248, 0.12);
  color: #c7d2fe;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s ease;
}

.mic-btn:hover:not(:disabled) {
  background: rgba(129, 140, 248, 0.22);
  color: #fff;
}

.mic-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mic-btn.stop {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.14);
  color: #fca5a5;
}

.mic-btn.stop:hover {
  background: rgba(239, 68, 68, 0.24);
  color: #fff;
}

.rec-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ef4444;
  animation: rec_pulse 1.1s ease-in-out infinite;
}

@keyframes rec_pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
  }
}

.rec-time {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #fca5a5;
  min-width: 34px;
}

.rec-time.warn {
  color: #fbbf24;
}

.rec-wave {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 20px;
}

.rec-wave i {
  display: block;
  width: 3px;
  height: 6px;
  border-radius: 2px;
  background: #ef4444;
  animation: rec_wave 0.9s ease-in-out infinite;
}

.rec-wave i:nth-child(2) { animation-delay: 0.1s; }
.rec-wave i:nth-child(3) { animation-delay: 0.2s; }
.rec-wave i:nth-child(4) { animation-delay: 0.3s; }
.rec-wave i:nth-child(5) { animation-delay: 0.4s; }
.rec-wave i:nth-child(6) { animation-delay: 0.5s; }

@keyframes rec_wave {
  0%, 100% { height: 6px; }
  50% { height: 18px; }
}

.asr-hint {
  font-size: 12px;
  color: #8d97bd;
}

.iv-textarea {
  width: 100%;
  max-width: 660px;
  min-height: 130px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(129, 140, 248, 0.28);
  background: rgba(12, 16, 32, 0.72);
  color: #e8ecff;
  font-size: 14px;
  line-height: 1.7;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.iv-textarea:focus {
  border-color: rgba(129, 140, 248, 0.7);
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.14);
}

.iv-textarea::placeholder {
  color: #5a6485;
}

.iv-answered {
  width: 100%;
  max-width: 660px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.iv-answer-label {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #6b76a0;
  align-self: flex-start;
}

.iv-answer {
  width: 100%;
  text-align: left;
  font-size: 13px;
  line-height: 1.75;
  color: #aab4d8;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  max-height: 150px;
  overflow-y: auto;
}

.iv-score-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.iv-score {
  font-size: 42px;
  font-weight: 700;
  line-height: 1;
  color: #7dd3fc;
  text-shadow: 0 0 24px rgba(125, 211, 252, 0.45);
}

.iv-score-unit {
  font-size: 13px;
  color: #6b76a0;
}

.iv-comment {
  font-size: 13px;
  line-height: 1.8;
  color: #97a3c9;
  max-width: 620px;
}

.iv-replay {
  background: transparent;
  border: none;
  color: #818cf8;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  font-family: inherit;
}

.iv-bottom {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-top: 8px;
}

.btn-light,
.btn-ghost {
  height: 44px;
  padding: 0 28px;
  border-radius: 999px;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s ease;
  border: 1px solid transparent;
}

.btn-light {
  background: #fff;
  color: #1b1f2e;
  font-weight: 600;
}

.btn-light:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 26px rgba(255, 255, 255, 0.16);
}

.btn-light:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.22);
  color: #fff;
}

.btn-ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}

.iv-audio {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

/* 单题点评弹窗 */
.answer-review {
  text-align: center;
  padding: 6px 0 2px;
}

.review-label {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: #8a94a8;
}

.review-score {
  font-size: 46px;
  font-weight: 700;
  line-height: 1.1;
  margin: 8px 0 14px;
  color: #c98a2e;
}

.review-score.good {
  color: #12a06a;
}

.review-score span {
  font-size: 14px;
  margin-left: 3px;
  opacity: 0.7;
}

.review-comment {
  font-size: 13px;
  line-height: 1.8;
  color: #4a5266;
  text-align: left;
  background: #f6f7fb;
  border-radius: 10px;
  padding: 12px 14px;
  max-height: 220px;
  overflow-y: auto;
}

/* 结果弹窗 */
.verdict {
  text-align: center;
  padding: 10px 0 4px;
}

.verdict-badge {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.3em;
  padding: 4px 14px;
  border-radius: 999px;
  margin-bottom: 14px;
}

.verdict.pass .verdict-badge {
  color: #0f7a4d;
  background: #e2f8ee;
  border: 1px solid #b7e4ca;
}

.verdict.fail .verdict-badge {
  color: #a33a3a;
  background: #fdeaea;
  border: 1px solid #f4c9c9;
}

.verdict-score {
  font-size: 46px;
  font-weight: 700;
  line-height: 1;
}

.verdict.pass .verdict-score {
  color: #12a06a;
}

.verdict.fail .verdict-score {
  color: #d64545;
}

.verdict-score span {
  font-size: 15px;
  margin-left: 3px;
  opacity: 0.7;
}

.verdict-text {
  font-size: 14px;
  margin: 12px 0 8px;
  color: #333;
}

.verdict-meta {
  font-size: 12px;
  color: #8a94a8;
}

.verdict-audio {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.hidden-audio {
  display: none;
}

.verdict-audio-hint {
  font-size: 12px;
  color: #8a94a8;
}

.verdict-replay {
  background: transparent;
  border: none;
  color: #6366f1;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  font-family: inherit;
}

@media (max-width: 640px) {
  .iv-stage {
    padding: 14px 14px 18px;
  }

  .iv-question {
    font-size: 16px;
  }

  .ai-orb {
    width: 72px;
    height: 72px;
    font-size: 26px;
  }
}
</style>
