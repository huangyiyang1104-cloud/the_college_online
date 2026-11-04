<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  confirm_course_import,
  create_course,
  create_subject,
  delete_course,
  delete_subject,
  list_courses,
  list_subjects,
  reorder_courses,
  update_course,
  update_subject,
  upload_course_excel,
} from '../api/admin'

const subject_loading = ref(false)
const course_loading = ref(false)
const subjects = ref<any[]>([])
const courses = ref<any[]>([])
const active_subject = ref<any>(null)

const subject_dialog = ref(false)
const subject_editing = ref<any>(null)
const subject_form_ref = ref<FormInstance>()
const subject_form = reactive({ name: '', icon: '📘', description: '', keywords: '' })
const subject_rules: FormRules = {
  name: [{ required: true, message: '请输入学科名称', trigger: 'blur' }],
}

const course_dialog = ref(false)
const course_editing = ref<any>(null)
const course_form_ref = ref<FormInstance>()
const course_form = reactive({ title: '', description: '', duration_minutes: 45, bilibili_url: '' })
const course_rules: FormRules = {
  title: [{ required: true, message: '请输入课程标题', trigger: 'blur' }],
  duration_minutes: [{ required: true, message: '请输入时长', trigger: 'blur' }],
  bilibili_url: [
    { required: true, message: '请输入播放地址', trigger: 'blur' },
    { pattern: /^https:\/\/www\.bilibili\.com\//, message: '必须是 bilibili.com 的完整链接', trigger: 'blur' },
  ],
}

const import_dialog = ref(false)
const import_file = ref<File | null>(null)
const import_preview = ref<any>(null)
const importing = ref(false)

const active_keywords = computed(() => active_subject.value?.keywords || [])

async function load_subjects() {
  subject_loading.value = true
  try {
    const data: any = await list_subjects({ page: 1, page_size: 100 })
    subjects.value = data.list
    if (!active_subject.value && subjects.value.length) {
      await select_subject(subjects.value[0])
    } else if (active_subject.value) {
      const current = subjects.value.find((item) => item.id === active_subject.value.id)
      active_subject.value = current || null
      if (current) await load_courses(current.id)
      else courses.value = []
    }
  } finally {
    subject_loading.value = false
  }
}

async function load_courses(subject_id: string) {
  course_loading.value = true
  try {
    const data: any = await list_courses(subject_id)
    courses.value = data.list
  } finally {
    course_loading.value = false
  }
}

async function select_subject(row: any) {
  active_subject.value = row
  await load_courses(row.id)
}

function open_subject(row?: any) {
  subject_editing.value = row || null
  subject_form.name = row?.name || ''
  subject_form.icon = row?.icon || '📘'
  subject_form.description = row?.description || ''
  subject_form.keywords = (row?.keywords || []).join(',')
  subject_dialog.value = true
}

async function submit_subject() {
  if (!subject_form_ref.value) return
  const valid = await subject_form_ref.value.validate().catch(() => false)
  if (!valid) return

  const payload = {
    name: subject_form.name.trim(),
    icon: subject_form.icon,
    description: subject_form.description.trim(),
    keywords: subject_form.keywords
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean),
  }
  if (subject_editing.value) {
    await update_subject(subject_editing.value.id, payload)
    ElMessage.success('已保存')
  } else {
    const created: any = await create_subject(payload)
    ElMessage.success('已新增，录完即上线')
    active_subject.value = created
  }
  subject_dialog.value = false
  await load_subjects()
}

async function toggle_subject(row: any) {
  await update_subject(row.id, { status: row.status ? 0 : 1 })
  ElMessage.success(row.status ? '已下架' : '已上架')
  await load_subjects()
}

async function remove_subject(row: any) {
  await ElMessageBox.confirm(`删除学科「${row.name}」？学科下必须没有课程。`, '确认删除', { type: 'warning' })
  await delete_subject(row.id)
  ElMessage.success('已删除')
  if (active_subject.value?.id === row.id) {
    active_subject.value = null
    courses.value = []
  }
  await load_subjects()
}

function open_course(row?: any) {
  course_editing.value = row || null
  course_form.title = row?.title || ''
  course_form.description = row?.description || ''
  course_form.duration_minutes = row?.duration_minutes ?? 45
  course_form.bilibili_url = row?.bilibili_url || 'https://www.bilibili.com/video/'
  course_dialog.value = true
}

async function submit_course() {
  if (!course_form_ref.value || !active_subject.value) return
  const valid = await course_form_ref.value.validate().catch(() => false)
  if (!valid) return

  const payload = {
    title: course_form.title.trim(),
    description: course_form.description.trim(),
    duration_minutes: Number(course_form.duration_minutes),
    bilibili_url: course_form.bilibili_url.trim(),
  }
  if (course_editing.value) {
    await update_course(course_editing.value.id, payload)
    ElMessage.success('已保存')
  } else {
    await create_course(active_subject.value.id, payload)
    ElMessage.success('已新增，排在路径末尾')
  }
  course_dialog.value = false
  await load_courses(active_subject.value.id)
  await load_subjects()
}

async function toggle_course(row: any) {
  await update_course(row.id, { status: row.status ? 0 : 1 })
  ElMessage.success(row.status ? '已下架' : '已上架')
  await load_courses(active_subject.value.id)
}

async function remove_course(row: any) {
  await ElMessageBox.confirm(`删除课程「${row.title}」？`, '确认删除', { type: 'warning' })
  await delete_course(row.id)
  ElMessage.success('已删除')
  await load_courses(active_subject.value.id)
  await load_subjects()
}

async function move(index: number, offset: number) {
  const target = index + offset
  if (!active_subject.value || target < 0 || target >= courses.value.length) return
  const list = courses.value.slice()
  const [item] = list.splice(index, 1)
  list.splice(target, 0, item)
  await reorder_courses(
    active_subject.value.id,
    list.map((row) => row.id),
  )
  courses.value = list
  ElMessage.success('顺序已更新')
}

function pick_import_file(file: any) {
  import_file.value = file.raw
  import_preview.value = null
}

async function run_import() {
  if (!active_subject.value || !import_file.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  importing.value = true
  try {
    import_preview.value = await upload_course_excel(import_file.value, active_subject.value.id)
  } finally {
    importing.value = false
  }
}

async function confirm_import() {
  if (!import_preview.value) return
  const result: any = await confirm_course_import(import_preview.value.import_id)
  ElMessage.success(`已导入 ${result.imported} 门课程`)
  import_dialog.value = false
  import_file.value = null
  import_preview.value = null
  await load_courses(active_subject.value.id)
  await load_subjects()
}

onMounted(load_subjects)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>课程内容</h2>
        <p>学科 → 课程两级；课程顺序就是学员看到的学习路径，支持上移/下移</p>
      </div>
      <el-button type="primary" @click="open_subject()">新增学科</el-button>
    </div>

    <div class="split">
      <div class="card-block left">
        <div class="block-head">
          <b>学科</b>
          <el-button link type="primary" @click="load_subjects">刷新</el-button>
        </div>
        <el-table
          v-loading="subject_loading"
          :data="subjects"
          size="small"
          highlight-current-row
          :row-class-name="({ row }) => (row.id === active_subject?.id ? 'current-row' : '')"
          @row-click="select_subject"
        >
          <el-table-column prop="name" label="名称" min-width="120">
            <template #default="{ row }">{{ row.icon }} {{ row.name }}</template>
          </el-table-column>
          <el-table-column prop="course_count" label="课程" width="70" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status ? 'success' : 'info'" size="small">
                {{ row.status ? '上架' : '下架' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="open_subject(row)">编辑</el-button>
              <el-button link @click.stop="toggle_subject(row)">{{ row.status ? '下架' : '上架' }}</el-button>
              <el-button link type="danger" @click.stop="remove_subject(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="还没有学科，先新增一个" :image-size="70" />
          </template>
        </el-table>
      </div>

      <div class="card-block right">
        <div class="block-head">
          <div>
            <b>{{ active_subject ? `${active_subject.icon} ${active_subject.name}` : '未选择学科' }}</b>
            <div v-if="active_subject" class="muted" style="margin-top: 4px">
              面试检索关键词：{{ active_keywords.length ? active_keywords.join('、') : '未设置' }}
            </div>
          </div>
          <div>
            <el-button size="small" :disabled="!active_subject" @click="import_dialog = true">
              导入课程 Excel
            </el-button>
            <el-button type="primary" size="small" :disabled="!active_subject" @click="open_course()">
              新增课程
            </el-button>
          </div>
        </div>

        <el-table v-loading="course_loading" :data="courses" size="small">
          <el-table-column prop="sort_order" label="顺序" width="70" />
          <el-table-column prop="title" label="课程标题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="duration_minutes" label="时长(分)" width="90" />
          <el-table-column prop="bilibili_url" label="B 站地址" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status ? 'success' : 'info'" size="small">
                {{ row.status ? '上架' : '下架' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250">
            <template #default="{ row, $index }">
              <el-button link :disabled="$index === 0" @click="move($index, -1)">上移</el-button>
              <el-button link :disabled="$index === courses.length - 1" @click="move($index, 1)">下移</el-button>
              <el-button link type="primary" @click="open_course(row)">编辑</el-button>
              <el-button link @click="toggle_course(row)">{{ row.status ? '下架' : '上架' }}</el-button>
              <el-button link type="danger" @click="remove_course(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="active_subject ? '该学科还没有课程' : '请先选择左侧学科'" :image-size="70" />
          </template>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="subject_dialog" :title="subject_editing ? '编辑学科' : '新增学科'" width="520px">
      <el-form ref="subject_form_ref" :model="subject_form" :rules="subject_rules" label-width="90px">
        <el-form-item label="学科名称" prop="name">
          <el-input v-model="subject_form.name" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="subject_form.icon" maxlength="16" placeholder="emoji，如 🧠" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="subject_form.description" type="textarea" :rows="3" maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item label="检索关键词">
          <el-input v-model="subject_form.keywords" placeholder="逗号分隔，AI 面试用它检索资料" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subject_dialog = false">取消</el-button>
        <el-button type="primary" @click="submit_subject">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="course_dialog" :title="course_editing ? '编辑课程' : '新增课程'" width="560px">
      <el-form ref="course_form_ref" :model="course_form" :rules="course_rules" label-width="100px">
        <el-form-item label="课程标题" prop="title">
          <el-input v-model="course_form.title" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="时长(分钟)" prop="duration_minutes">
          <el-input-number v-model="course_form.duration_minutes" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="B 站地址" prop="bilibili_url">
          <el-input v-model="course_form.bilibili_url" placeholder="https://www.bilibili.com/video/BV..." />
        </el-form-item>
        <el-form-item label="节点说明">
          <el-input v-model="course_form.description" type="textarea" :rows="3" maxlength="512" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="course_dialog = false">取消</el-button>
        <el-button type="primary" @click="submit_course">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="import_dialog" title="导入课程 Excel" width="640px">
      <el-upload :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="pick_import_file">
        <el-button>选择文件</el-button>
        <template #tip>
          <div class="muted" style="margin-top: 8px">
            模板列：课程名称 / 时长（分钟）/ 播放链接。解析后先预览校验结果，确认后入库。
          </div>
        </template>
      </el-upload>

      <div v-if="import_preview" style="margin-top: 16px">
        <el-alert
          :title="`解析 ${import_preview.summary.total} 行，可导入 ${import_preview.summary.valid} 行，异常 ${import_preview.summary.invalid} 行`"
          :type="import_preview.summary.invalid ? 'warning' : 'success'"
          :closable="false"
        />
        <el-table :data="import_preview.preview" size="small" style="margin-top: 12px" max-height="220">
          <el-table-column prop="row" label="行" width="60" />
          <el-table-column prop="title" label="课程名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="duration_minutes" label="时长" width="80" />
        </el-table>
        <div v-if="import_preview.errors.length" class="muted" style="margin-top: 10px">
          前几条错误：{{ import_preview.errors.slice(0, 3).map((e: any) => `第${e.row}行 ${e.reason}`).join('；') }}
        </div>
      </div>

      <template #footer>
        <el-button @click="import_dialog = false">取消</el-button>
        <el-button :loading="importing" @click="run_import">解析并预览</el-button>
        <el-button type="primary" :disabled="!import_preview" @click="confirm_import">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.split {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
  align-items: start;
}

.block-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

@media (max-width: 1200px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
