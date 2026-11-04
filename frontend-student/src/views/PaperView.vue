<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetch_paper } from '../api/student'
import { is_code_text } from '../utils/format'

const route = useRoute()

const loading = ref(false)
const paper = ref<any>({ items: [] })

const TYPE_LABEL: Record<number, string> = { 1: '判断题', 2: '单选题', 3: '多选题', 4: '简答题' }

const score_ratio = computed(() => {
  const total = paper.value.total_score || 0
  const got = paper.value.obtained_score || 0
  return total ? Math.round((got / total) * 100) : 0
})

const correct_count = computed(
  () => (paper.value.items || []).filter((item: any) => item.is_correct === 1).length,
)

const objective_count = computed(
  () => (paper.value.items || []).filter((item: any) => item.question_type !== 4).length,
)

function type_label(type: number) {
  return TYPE_LABEL[type] || '题目'
}

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function is_selected(item: any, key: string) {
  return (item.my_option_keys || []).includes(key)
}

async function load() {
  loading.value = true
  try {
    paper.value = await fetch_paper(String(route.params.id))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="card score-board">
      <div>
        <div class="meta-row" style="font-size: 13px">{{ paper.subject_name }}</div>
        <div class="big-score">
          {{ paper.obtained_score ?? '-' }}
          <span class="big-score-total">/ {{ paper.total_score }}</span>
        </div>
        <div class="meta-row" style="font-size: 13px">
          客观题答对 {{ correct_count }} / {{ objective_count }} · {{ format_time(paper.submitted_at) }}
        </div>
      </div>
      <div class="score-ring" :style="{ background: `conic-gradient(var(--brand) ${score_ratio}%, #eef0ff 0)` }">
        <span>{{ score_ratio }}%</span>
      </div>
    </div>

    <div v-for="item in paper.items" :key="item.question_id" class="card" style="margin-bottom: 14px">
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px">
        <span class="q-index">{{ item.question_index }}</span>
        <span class="tag-soft">{{ type_label(item.question_type) }}</span>
        <span
          v-if="item.question_type !== 4"
          class="tag-soft"
          :class="item.is_correct === 1 ? 'tag-done' : 'tag-wrong'"
        >
          {{ item.is_correct === 1 ? '答对' : '答错' }}
        </span>
        <span class="meta-row" style="font-size: 12px; margin-left: auto">
          {{ item.score_obtained ?? '-' }} / {{ item.score_max }} 分
        </span>
      </div>

      <p class="q-title" :class="{ 'q-code': is_code_text(item.title) }">{{ item.title }}</p>

      <!-- 客观题：列出选项并标出我的选择与正确答案 -->
      <div v-if="item.question_type !== 4" class="option-list">
        <div
          v-for="option in item.options"
          :key="option.option_key"
          class="option-item"
          :class="{
            'option-correct': option.is_correct === 1,
            'option-mine-wrong': is_selected(item, option.option_key) && option.is_correct !== 1,
          }"
        >
          <span class="option-key">{{ option.option_key }}</span>
          <span>{{ option.content }}</span>
          <span v-if="is_selected(item, option.option_key)" class="option-flag">我的选择</span>
          <span v-if="option.is_correct === 1" class="option-flag correct-flag">正确答案</span>
        </div>
        <div v-if="!item.my_option_keys?.length" class="meta-row" style="font-size: 12px; margin-top: 6px">
          本题未作答
        </div>
      </div>

      <!-- 简答题 -->
      <div v-else>
        <div class="answer-block">
          <div class="answer-label">我的作答</div>
          <div class="answer-text">{{ item.answer_text || '（未作答）' }}</div>
        </div>
        <div v-if="item.reference_answer" class="answer-block">
          <div class="answer-label">参考答案</div>
          <div class="answer-text">{{ item.reference_answer }}</div>
        </div>
        <div v-if="item.ai_comment" class="answer-block ai-comment">
          <div class="answer-label">AI 点评</div>
          <div class="answer-text">{{ item.ai_comment }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
