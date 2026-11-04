<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { list_wrong, remove_wrong, retry_wrong } from '../api/student'
import { is_code_text } from '../utils/format'

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, subject_id: '' })
const subjects = ref<any[]>([])

const dialog_visible = ref(false)
const submitting = ref(false)
const current = ref<any>(null)
const chosen_keys = ref<string[]>([])
const result = ref<any>(null)

const TYPE_LABEL: Record<number, string> = { 1: '判断题', 2: '单选题', 3: '多选题' }

function type_label(type: number) {
  return TYPE_LABEL[type] || '题目'
}

function format_time(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const data: any = await list_wrong({
      page: query.page,
      page_size: query.page_size,
      subject_id: query.subject_id || undefined,
    })
    rows.value = data.list
    total.value = data.total
    // 用当前页的学科去重做筛选选项，避免额外请求
    const map = new Map<string, string>()
    for (const item of data.list) map.set(item.subject_id, item.subject_name)
    for (const item of subjects.value) map.set(item.subject_id, item.subject_name)
    subjects.value = Array.from(map, ([id, name]) => ({ id, name }))
  } finally {
    loading.value = false
  }
}

function open_retry(item: any) {
  current.value = item
  chosen_keys.value = []
  result.value = null
  dialog_visible.value = true
}

function pick_single(value: string) {
  chosen_keys.value = [value]
}

async function submit_retry() {
  if (!chosen_keys.value.length) {
    ElMessage.warning('请先选择答案')
    return
  }
  submitting.value = true
  try {
    result.value = await retry_wrong(current.value.question_id, chosen_keys.value)
    if (result.value.is_correct === 1) {
      ElMessage.success('答对了，已移出错题本')
    } else {
      ElMessage.warning('还是不对，再想想')
    }
  } finally {
    submitting.value = false
  }
}

async function close_dialog() {
  dialog_visible.value = false
  if (result.value?.removed) await load()
}

async function handle_remove(item: any) {
  await ElMessageBox.confirm('从错题本移除这道题？', '提示', { type: 'warning' })
  await remove_wrong(item.question_id)
  ElMessage.success('已移除')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">错题本</h2>
    <p class="page-sub">只收录客观题；重做答对会自动移出，答错则累计次数</p>

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
      <span class="meta-row" style="font-size: 13px">共 {{ total }} 道</span>
    </div>

    <div v-if="rows.length">
      <div v-for="item in rows" :key="item.question_id" class="card" style="margin-bottom: 12px">
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px">
          <span class="tag-soft">{{ type_label(item.type) }}</span>
          <span class="meta-row" style="font-size: 12px">{{ item.subject_name }}</span>
          <span class="meta-row" style="font-size: 12px; margin-left: auto">
            错 {{ item.wrong_times }} 次 · {{ format_time(item.last_wrong_at) }}
          </span>
        </div>
        <p class="q-title" :class="{ 'q-code': is_code_text(item.title) }">{{ item.title }}</p>
        <div class="option-list">
          <div v-for="option in item.options" :key="option.option_key" class="option-item">
            <span class="option-key">{{ option.option_key }}</span>
            <span>{{ option.content }}</span>
          </div>
        </div>
        <div style="display: flex; gap: 10px; margin-top: 12px">
          <el-button type="primary" size="small" @click="open_retry(item)">重做这题</el-button>
          <el-button size="small" @click="handle_remove(item)">移出错题本</el-button>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="card">
      <div class="empty-box">错题本是空的，去刷题吧</div>
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

    <el-dialog
      v-model="dialog_visible"
      :title="result ? (result.is_correct === 1 ? '答对了' : '答错了') : '重做这道题'"
      width="560px"
      @closed="close_dialog"
    >
      <template v-if="current">
        <p
          class="q-title"
          :class="{ 'q-code': is_code_text(current.title) }"
          style="margin-top: 0"
        >
          {{ current.title }}
        </p>

        <el-radio-group
          v-if="current.type !== 3"
          :model-value="chosen_keys[0] || ''"
          :disabled="!!result"
          @update:model-value="(value: any) => pick_single(String(value))"
          style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start"
        >
          <el-radio v-for="option in current.options" :key="option.option_key" :value="option.option_key">
            {{ option.option_key }}. {{ option.content }}
          </el-radio>
        </el-radio-group>

        <el-checkbox-group
          v-else
          v-model="chosen_keys"
          :disabled="!!result"
          style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start"
        >
          <el-checkbox v-for="option in current.options" :key="option.option_key" :value="option.option_key">
            {{ option.option_key }}. {{ option.content }}
          </el-checkbox>
        </el-checkbox-group>

        <div v-if="result" class="answer-block" style="margin-top: 14px">
          <div class="answer-label">
            正确答案：{{ result.correct_option_keys.join('、') }}
            <span v-if="result.removed" class="tag-soft tag-done" style="margin-left: 8px">已移出错题本</span>
          </div>
          <div class="answer-text">{{ result.analysis || '暂无解析' }}</div>
        </div>
      </template>

      <template #footer>
        <el-button v-if="!result" @click="dialog_visible = false">取消</el-button>
        <el-button v-if="!result" type="primary" :loading="submitting" @click="submit_retry">
          提交
        </el-button>
        <el-button v-else @click="dialog_visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>
