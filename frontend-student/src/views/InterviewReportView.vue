<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetch_interview_report } from '../api/student'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const report = ref<any>({ items: [] })

const session_id = computed(() => String(route.params.id))

/** 单题得分对应颜色：不及格橙、良好绿、优秀青 */
function score_class(score: number | null) {
  if (score === null) return 'none'
  if (score < 60) return 'bad'
  if (score < 80) return 'ok'
  return 'good'
}

function format_time(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

function duration_text(seconds: number | null) {
  if (!seconds) return '-'
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return minutes ? `${minutes} 分 ${rest} 秒` : `${rest} 秒`
}

async function load() {
  loading.value = true
  try {
    const data: any = await fetch_interview_report(session_id.value)
    report.value = data
  } catch {
    // 拦截器已提示（未结束返回 409），退回列表
    router.replace('/interview')
  } finally {
    loading.value = false
  }
}

function retry_interview() {
  router.push('/interview')
}

onMounted(load)
</script>

<template>
  <div class="report-stage" v-loading="loading" element-loading-background="rgba(5, 6, 13, .85)">
    <header class="report-head">
      <button class="back-btn" @click="router.replace('/interview')">← 返回面试列表</button>
      <div class="head-title">INTERVIEW REPORT</div>
    </header>

    <!-- 总分 -->
    <section class="hero">
      <div class="hero-ring" :class="report.passed ? 'pass' : 'fail'">
        <span class="ring-score">{{ Math.round(report.total_score ?? 0) }}</span>
        <span class="ring-unit">分</span>
      </div>

      <div class="hero-info">
        <div class="hero-badge" :class="report.passed ? 'pass' : 'fail'">
          {{ report.passed ? 'PASS · 通过' : 'FAIL · 未通过' }}
        </div>
        <h1 class="hero-subject">{{ report.subject_name || 'AI 面试' }}</h1>
        <p class="hero-summary">{{ report.summary }}</p>

        <div class="hero-meta">
          <span>答 {{ report.answered_count }}/{{ report.question_count }} 题</span>
          <span class="sep">·</span>
          <span>用时 {{ duration_text(report.duration_seconds) }}</span>
          <span class="sep">·</span>
          <span>通过线 {{ report.pass_score }} 分</span>
        </div>
        <div class="hero-time">
          {{ format_time(report.started_at) }}
          <template v-if="report.ended_at"> → {{ format_time(report.ended_at) }}</template>
        </div>
      </div>
    </section>

    <!-- 逐题 -->
    <section class="items">
      <article
        v-for="item in report.items"
        :key="item.question_index"
        class="item-card"
      >
        <div class="item-head">
          <span class="item-index">Q{{ String(item.question_index).padStart(2, '0') }}</span>
          <span class="item-score" :class="score_class(item.score)">
            {{ item.score === null ? '未答' : Math.round(item.score) }}
            <small v-if="item.score !== null">分</small>
          </span>
        </div>

        <h3 class="item-question">{{ item.question_text }}</h3>

        <div class="item-tags">
          <span v-if="item.source_doc_name" class="tag source">
            来源：{{ item.source_doc_name }}
          </span>
          <span v-if="item.answer_mode" class="tag mode">
            {{ item.answer_mode === 1 ? '语音作答' : '文字作答' }}
          </span>
        </div>

        <div class="item-block">
          <div class="block-label">我的回答</div>
          <div class="block-body" :class="{ empty: !item.answer_text }">
            {{ item.answer_text || '未作答' }}
          </div>
        </div>

        <div v-if="item.follow_up_text" class="item-block follow">
          <div class="block-label">面试官追问</div>
          <div class="block-body">{{ item.follow_up_text }}</div>
          <div class="block-label" style="margin-top: 10px">我的追问回答</div>
          <div class="block-body" :class="{ empty: !item.follow_up_answer }">
            {{ item.follow_up_answer || '未回答' }}
          </div>
        </div>

        <div v-if="item.ai_comment" class="item-block comment">
          <div class="block-label">AI 点评</div>
          <div class="block-body">{{ item.ai_comment }}</div>
        </div>
      </article>
    </section>

    <footer class="report-foot">
      <button class="primary-btn" @click="retry_interview">再练一场</button>
      <button class="ghost-btn" @click="router.replace('/records')">查看学习记录</button>
    </footer>
  </div>
</template>

<style scoped>
.report-stage {
  /* 与面试页一致：盖住导航栏，自己做全屏滚动 */
  position: fixed;
  inset: 0;
  z-index: 60;
  overflow-y: auto;
  padding: 20px 22px 60px;
  color: #e8ecff;
  background:
    radial-gradient(900px 480px at 50% -10%, rgba(99, 102, 241, 0.22), transparent 60%),
    #05060d;
}

.report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}

.back-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.16);
  color: #9aa6d0;
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s ease;
}

.back-btn:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.4);
}

.head-title {
  font-size: 11px;
  letter-spacing: 0.3em;
  color: #6b76a0;
}

/* 总分 */
.hero {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 26px 28px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(120, 170, 255, 0.16);
  backdrop-filter: blur(14px);
  margin-bottom: 22px;
}

.hero-ring {
  flex-shrink: 0;
  width: 132px;
  height: 132px;
  border-radius: 50%;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  padding-top: 12px;
  border: 2px solid;
  background: rgba(255, 255, 255, 0.03);
}

.hero-ring.pass {
  border-color: rgba(74, 222, 155, 0.55);
  box-shadow: 0 0 40px rgba(74, 222, 155, 0.16) inset;
}

.hero-ring.fail {
  border-color: rgba(251, 113, 133, 0.55);
  box-shadow: 0 0 40px rgba(251, 113, 133, 0.16) inset;
}

.ring-score {
  font-size: 46px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.hero-ring.pass .ring-score {
  color: #4ade9b;
}

.hero-ring.fail .ring-score {
  color: #fb7185;
}

.ring-unit {
  font-size: 13px;
  color: #6b76a0;
  margin-bottom: 6px;
}

.hero-info {
  min-width: 0;
}

.hero-badge {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.16em;
  padding: 3px 12px;
  border-radius: 999px;
  margin-bottom: 10px;
}

.hero-badge.pass {
  color: #4ade9b;
  background: rgba(74, 222, 155, 0.12);
  border: 1px solid rgba(74, 222, 155, 0.35);
}

.hero-badge.fail {
  color: #fb7185;
  background: rgba(251, 113, 133, 0.12);
  border: 1px solid rgba(251, 113, 133, 0.35);
}

.hero-subject {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
}

.hero-summary {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #a8bcd8;
}

.hero-meta {
  font-size: 12px;
  color: #7d8aa8;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sep {
  color: #3f4a68;
}

.hero-time {
  margin-top: 6px;
  font-size: 11px;
  color: #5c688a;
}

/* 逐题 */
.items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.item-card {
  border-radius: 16px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(120, 170, 255, 0.14);
  transition: border-color 0.2s ease;
}

.item-card:hover {
  border-color: rgba(120, 170, 255, 0.3);
}

.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.item-index {
  font-size: 11px;
  letter-spacing: 0.2em;
  color: #6f8ac0;
}

.item-score {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.item-score small {
  font-size: 11px;
  margin-left: 2px;
  opacity: 0.7;
}

.item-score.good {
  color: #69d7ff;
}

.item-score.ok {
  color: #4ade9b;
}

.item-score.bad {
  color: #fb923c;
}

.item-score.none {
  color: #5c688a;
  font-size: 13px;
}

.item-question {
  margin: 0 0 12px;
  font-size: 15px;
  line-height: 1.7;
  font-weight: 600;
  color: #f2f5ff;
}

.item-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
}

.tag.source {
  color: #93a5cc;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tag.mode {
  color: #7dd3fc;
  background: rgba(125, 211, 252, 0.1);
  border: 1px solid rgba(125, 211, 252, 0.25);
}

.item-block {
  margin-top: 10px;
}

.block-label {
  font-size: 11px;
  letter-spacing: 0.1em;
  color: #6b76a0;
  margin-bottom: 5px;
}

.block-body {
  font-size: 13px;
  line-height: 1.8;
  color: #c3cee6;
  white-space: pre-wrap;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(8, 14, 30, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.block-body.empty {
  color: #5c688a;
  font-style: italic;
}

.item-block.comment .block-body {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.22);
  color: #c7d2fe;
}

.item-block.follow .block-body {
  background: rgba(255, 196, 92, 0.07);
  border-color: rgba(255, 196, 92, 0.2);
  color: #ffe0a8;
}

.report-foot {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 26px;
}

.primary-btn,
.ghost-btn {
  font-family: inherit;
  font-size: 14px;
  padding: 10px 26px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s ease;
  border: 1px solid transparent;
}

.primary-btn {
  color: #04101f;
  font-weight: 600;
  background: linear-gradient(135deg, #69d7ff, #3f7bff);
  box-shadow: 0 8px 24px rgba(63, 123, 255, 0.3);
}

.primary-btn:hover {
  transform: translateY(-1px);
}

.ghost-btn {
  color: #a8c0e8;
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(120, 170, 255, 0.25);
}

.ghost-btn:hover {
  color: #fff;
  border-color: rgba(120, 170, 255, 0.5);
}

@media (max-width: 640px) {
  .hero {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .hero-meta {
    justify-content: center;
  }
}
</style>
