<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  confirm_question_import,
  create_question,
  delete_question,
  list_questions,
  list_subjects,
  update_question,
  upload_question_excel,
} from '../api/admin'

const TYPE_LABEL: Record<number, string> = { 1: '判断题', 2: '单选题', 3: '多选题', 4: '简答题' }

const loading = ref(false)
const questions = ref<any[]>([])
const total = ref(0)
const subjects = ref<any[]>([])
const filters = reactive({ subject_id: '', type: undefined as number | undefined, keyword: '', page: 1, page_size: 10 })

const dialog = ref(false)
const editing = ref<any>(null)
const form_ref = ref<FormInstance>()
const form = reactive({
  subject_id: '',
  type: 2,
  difficulty: 2,
  category: '',
  title: '',
  score: 10,
  reference_answer: '',
  analysis: '',
  tags: '',
  options: [] as Array<{ option_key: string; content: string; is_correct: number }>,
})

const is_short = computed(() => form.type === 4)
const is_judge = computed(() => form.type === 1)

const rules: FormRules = {
  subject_id: [{ required: true, message: '请选择学科', trigger: 'change' }],
  title: [{ required: true, message: '请输入题干', trigger: 'blur' }],
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }],
}

const import_dialog = ref(false)
const import_file = ref<File | null>(null)
const import_subject = ref('')
const import_preview = ref<any>(null)

function default_options() {
  return [
    { option_key: 'A', content: '', is_correct: 0 },
    { option_key: 'B', content: '', is_correct: 0 },
    { option_key: 'C', content: '', is_correct: 0 },
    { option_key: 'D', content: '', is_correct: 0 },
  ]
}

async function load_subjects() {
  const data: any = await list_subjects({ page: 1, page_size: 100 })
  subjects.value = data.list
  if (!import_subject.value && subjects.value.length) import_subject.value = subjects.value[0].id
}

async function load() {
  loading.value = true
  try {
    const data: any = await list_questions({
      page: filters.page,
      page_size: filters.page_size,
      subject_id: filters.subject_id || undefined,
      type: filters.type || undefined,
      keyword: filters.keyword || undefined,
    })
    questions.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reset_filters() {
  filters.subject_id = ''
  filters.type = undefined
  filters.keyword = ''
  filters.page = 1
  load()
}

function open_dialog(row?: any) {
  editing.value = row || null
  if (row) {
    form.subject_id = row.subject_id
    form.type = row.type
    form.difficulty = row.difficulty
    form.category = row.category
    form.title = row.title
    form.score = row.score
    form.reference_answer = row.reference_answer || ''
    form.analysis = row.analysis || ''
    form.tags = (row.tags || []).join(',')
    form.options = row.options?.length
      ? row.options.map((item: any) => ({ ...item }))
      : default_options()
  } else {
    form.subject_id = filters.subject_id || subjects.value[0]?.id || ''
    form.type = 2
    form.difficulty = 2
    form.category = ''
    form.title = ''
    form.score = 10
    form.reference_answer = ''
    form.analysis = ''
    form.tags = ''
    form.options = default_options()
  }
  dialog.value = true
}

function on_type_change() {
  if (is_short.value) {
    form.options = []
    form.score = 20
  } else if (is_judge.value) {
    form.options = [
      { option_key: 'A', content: '正确', is_correct: 1 },
      { option_key: 'B', content: '错误', is_correct: 0 },
    ]
    form.score = 10
  } else if (!form.options.length) {
    form.options = default_options()
    form.score = 10
  }
}

function mark_correct(index: number) {
  if (form.type === 3) {
    form.options[index].is_correct = form.options[index].is_correct ? 0 : 1
  } else {
    form.options.forEach((item, i) => (item.is_correct = i === index ? 1 : 0))
  }
}

async function submit() {
  if (!form_ref.value) return
  const valid = await form_ref.value.validate().catch(() => false)
  if (!valid) return

  const payload: Record<string, unknown> = {
    subject_id: form.subject_id,
    type: form.type,
    difficulty: form.difficulty,
    category: form.category,
    title: form.title.trim(),
    score: Number(form.score),
    analysis: form.analysis.trim() || null,
    tags: form.tags.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
  }
  if (is_short.value) {
    payload.reference_answer = form.reference_answer.trim()
  } else {
    payload.options = form.options.filter((item) => item.content.trim())
  }

  // 编辑时不允许改题型（等同于重录）
  if (editing.value) {
    delete payload.type
    await update_question(editing.value.id, payload)
    ElMessage.success('已保存')
  } else {
    await create_question(payload)
    ElMessage.success('已新增')
  }
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm('删除后历史答卷仍按快照展示，确定删除该题？', '确认删除', { type: 'warning' })
  await delete_question(row.id)
  ElMessage.success('已删除')
  load()
}

function pick_file(file: any) {
  import_file.value = file.raw
  import_preview.value = null
}

async function run_import() {
  if (!import_file.value || !import_subject.value) {
    ElMessage.warning('请选择文件与目标学科')
    return
  }
  import_preview.value = await upload_question_excel(import_file.value, import_subject.value)
}

async function confirm_import() {
  const result: any = await confirm_question_import(import_preview.value.import_id)
  ElMessage.success(`已导入 ${result.imported} 道题`)
  import_dialog.value = false
  import_preview.value = null
  import_file.value = null
  load()
}

onMounted(async () => {
  await load_subjects()
  await load()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>刷题题库</h2>
        <p>题目挂在学科上；客观题用选项标记正确答案，简答题必填参考答案</p>
      </div>
      <div>
        <el-button @click="import_dialog = true">导入题库 Excel</el-button>
        <el-button type="primary" @click="open_dialog()">新增题目</el-button>
      </div>
    </div>

    <div class="toolbar">
      <el-select v-model="filters.subject_id" placeholder="全部学科" clearable style="width: 180px" @change="load">
        <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-select v-model="filters.type" placeholder="全部题型" clearable style="width: 140px" @change="load">
        <el-option v-for="(label, key) in TYPE_LABEL" :key="key" :label="label" :value="Number(key)" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索题干" clearable style="width: 200px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="reset_filters">重置</el-button>
    </div>

    <div class="card-block">
      <el-table v-loading="loading" :data="questions" size="small">
        <el-table-column prop="subject_name" label="学科" width="130" />
        <el-table-column label="题型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ TYPE_LABEL[row.type] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="题干" min-width="260" show-overflow-tooltip />
        <el-table-column prop="score" label="分值" width="70" />
        <el-table-column label="参考答案" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.type === 4 ? row.reference_answer : row.options.filter((o: any) => o.is_correct).map((o: any) => o.option_key).join('、') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link type="primary" @click="open_dialog(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无题目" :image-size="70" />
        </template>
      </el-table>

      <el-pagination
        v-model:current-page="filters.page"
        v-model:page-size="filters.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 14px; justify-content: flex-end"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑题目' : '新增题目'" width="640px" top="6vh">
      <el-form ref="form_ref" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="所属学科" prop="subject_id">
          <el-select v-model="form.subject_id" style="width: 100%">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="题型">
          <el-select v-model="form.type" :disabled="!!editing" style="width: 100%" @change="on_type_change">
            <el-option v-for="(label, key) in TYPE_LABEL" :key="key" :label="label" :value="Number(key)" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-radio-group v-model="form.difficulty">
            <el-radio :value="1">简单</el-radio>
            <el-radio :value="2">中等</el-radio>
            <el-radio :value="3">困难</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="题干" prop="title">
          <el-input v-model="form.title" type="textarea" :rows="3" maxlength="20000" />
        </el-form-item>

        <template v-if="!is_short">
          <el-form-item label="选项">
            <div style="width: 100%">
              <div v-for="(option, index) in form.options" :key="index" class="option-row">
                <el-input v-model="option.content" :placeholder="`选项 ${option.option_key}`" />
                <el-button
                  :type="option.is_correct ? 'success' : 'default'"
                  size="small"
                  :disabled="is_judge"
                  @click="mark_correct(index)"
                >
                  {{ option.is_correct ? '正确' : '设为正确' }}
                </el-button>
              </div>
              <div class="muted" style="margin-top: 6px">
                {{ form.type === 3 ? '多选题可标记多个正确答案' : '单选/判断题只能有一个正确答案' }}
              </div>
            </div>
          </el-form-item>
        </template>

        <el-form-item v-if="is_short" label="参考答案">
          <el-input v-model="form.reference_answer" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item label="解析/要点">
          <el-input v-model="form.analysis" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="分值">
          <el-input-number v-model="form.score" :min="0.5" :max="100" :step="1" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="import_dialog" title="导入题库 Excel" width="640px">
      <el-form label-width="90px">
        <el-form-item label="目标学科">
          <el-select v-model="import_subject" style="width: 100%">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-upload :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="pick_file">
        <el-button>选择文件</el-button>
        <template #tip>
          <div class="muted" style="margin-top: 8px">
            模板列：题干 / 分类 / 题型 / 难度 / 选项A-F / 正确答案 / 解析 / 标签
          </div>
        </template>
      </el-upload>

      <div v-if="import_preview" style="margin-top: 16px">
        <el-alert
          :title="`解析 ${import_preview.summary.total} 行，可导入 ${import_preview.summary.valid} 行，异常 ${import_preview.summary.invalid} 行`"
          :type="import_preview.summary.invalid ? 'warning' : 'success'"
          :closable="false"
        />
        <div v-if="import_preview.errors.length" class="muted" style="margin-top: 10px">
          {{ import_preview.errors.slice(0, 3).map((e: any) => `第${e.row}行 ${e.reason}`).join('；') }}
        </div>
      </div>

      <template #footer>
        <el-button @click="import_dialog = false">取消</el-button>
        <el-button @click="run_import">解析并预览</el-button>
        <el-button type="primary" :disabled="!import_preview" @click="confirm_import">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.option-row {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}
</style>
