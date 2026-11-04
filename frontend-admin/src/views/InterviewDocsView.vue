<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { delete_doc, list_docs, list_subjects, retrieval_test, retry_doc, upload_doc } from '../api/admin'
import AiLoadingDialog from '../components/AiLoadingDialog.vue'

const STATUS: Record<number, { label: string; type: string }> = {
  1: { label: '待处理', type: 'info' },
  2: { label: '转 md 中', type: 'warning' },
  3: { label: '已入库', type: 'success' },
  4: { label: '解析失败', type: 'danger' },
}

const loading = ref(false)
const docs = ref<any[]>([])
const total = ref(0)
const filters = reactive({ status: undefined as number | undefined, keyword: '', page: 1, page_size: 10 })
const uploading = ref(false)
const subjects = ref<any[]>([])

const test_dialog = ref(false)
const test_form = reactive({ subject_id: '', query: '' })
const test_loading = ref(false)
const test_result = ref<any>(null)
const ai_loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data: any = await list_docs({
      page: filters.page,
      page_size: filters.page_size,
      status: filters.status || undefined,
      keyword: filters.keyword || undefined,
    })
    docs.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function load_subjects() {
  const data: any = await list_subjects({ page: 1, page_size: 100 })
  subjects.value = data.list
  if (subjects.value.length) test_form.subject_id = subjects.value[0].id
}

async function on_file_change(file: any) {
  uploading.value = true
  try {
    await upload_doc(file.raw)
    ElMessage.success('已上传，等待切分入库')
    load()
  } finally {
    uploading.value = false
  }
}

async function retry(row: any) {
  await retry_doc(row.id)
  ElMessage.success('已重新投递处理')
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`删除文档「${row.file_name}」？切片会一并清理。`, '确认删除', { type: 'warning' })
  await delete_doc(row.id)
  ElMessage.success('已删除')
  load()
}

async function run_test() {
  test_loading.value = true
  ai_loading.value = true
  try {
    test_result.value = await retrieval_test({
      subject_id: test_form.subject_id || undefined,
      query: test_form.query || undefined,
      top_k: 5,
    })
  } finally {
    test_loading.value = false
    ai_loading.value = false
  }
}

function size_text(bytes: number) {
  if (!bytes) return '-'
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

onMounted(async () => {
  await load_subjects()
  await load()
})
</script>

<template>
  <div class="page">
    <AiLoadingDialog
      v-model="ai_loading"
      title="AI 正在检索"
      hint="把查询文本向量化后到 Milvus 里召回相似切片，约 2–5 秒"
      :slow_after="10"
    />

    <div class="page-head">
      <div>
        <h2>面试资料库</h2>
        <p>只管理原始资料：上传后转 md、切分并向量化；面试题由检索片段动态生成</p>
      </div>
      <div>
        <el-button @click="test_dialog = true">检索测试（RRF）</el-button>
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept=".pdf,.md"
          :on-change="on_file_change"
          style="display: inline-block; margin-left: 8px"
        >
          <el-button type="primary" :loading="uploading">上传资料</el-button>
        </el-upload>
      </div>
    </div>

    <div class="toolbar">
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px" @change="load">
        <el-option v-for="(item, key) in STATUS" :key="key" :label="item.label" :value="Number(key)" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索文件名" clearable style="width: 220px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <div class="card-block">
      <el-table v-loading="loading" :data="docs" size="small">
        <el-table-column prop="file_name" label="文档" min-width="240" show-overflow-tooltip />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">{{ row.file_type === 1 ? 'PDF' : 'MD' }}</template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ size_text(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="(STATUS[row.status]?.type as any) || 'info'" size="small">
              {{ STATUS[row.status]?.label || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 4" link type="primary" @click="retry(row)">重新处理</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="还没有资料，上传 PDF 或 Markdown" :image-size="70" />
        </template>
      </el-table>

      <el-pagination
        v-model:current-page="filters.page"
        v-model:page-size="filters.page_size"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 14px; justify-content: flex-end"
        @current-change="load"
      />

      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 16px"
        title="切片与向量化由后台任务处理；当前上传后状态停留在「待处理」，待切分任务接入后自动推进到「已入库」。"
      />
    </div>

    <el-dialog v-model="test_dialog" title="检索测试（RRF 融合）" width="620px">
      <el-form label-width="90px">
        <el-form-item label="学科">
          <el-select v-model="test_form.subject_id" clearable style="width: 100%">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义查询">
          <el-input v-model="test_form.query" placeholder="可选，填了就优先用它检索" />
        </el-form-item>
      </el-form>

      <el-button type="primary" :loading="test_loading" @click="run_test">开始检索</el-button>

      <el-table v-if="test_result" :data="test_result.items" size="small" style="margin-top: 14px">
        <el-table-column prop="rank" label="#" width="50" />
        <el-table-column prop="question" label="召回片段" min-width="220" show-overflow-tooltip />
        <el-table-column prop="doc_name" label="来源" width="160" show-overflow-tooltip />
        <el-table-column prop="rrf_score" label="RRF" width="90" />
        <template #empty>
          <el-empty description="暂无命中（向量库尚未接入）" :image-size="60" />
        </template>
      </el-table>
    </el-dialog>
  </div>
</template>
