<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { list_logs } from '../api/admin'

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const filters = reactive({ module: '', action: '', page: 1, page_size: 10 })

const MODULES = ['课程内容', '刷题题库', '面试资料库', '学员管理', '系统用户']
const ACTIONS = ['新增', '编辑', '上架', '下架', '删除', '导入', '启用', '停用', '调整顺序', '重新处理', '登录', '退出']

const detail_visible = ref(false)
const detail_row = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const data: any = await list_logs({
      page: filters.page,
      page_size: filters.page_size,
      module: filters.module || undefined,
      action: filters.action || undefined,
      with_detail: true,
    })
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function show_detail(row: any) {
  detail_row.value = row
  detail_visible.value = true
}

function reset() {
  filters.module = ''
  filters.action = ''
  filters.page = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>操作日志</h2>
        <p>记录后台关键操作，含变更前后快照，便于追溯</p>
      </div>
    </div>

    <div class="toolbar">
      <el-select v-model="filters.module" placeholder="全部模块" clearable style="width: 160px" @change="load">
        <el-option v-for="item in MODULES" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.action" placeholder="全部动作" clearable style="width: 140px" @change="load">
        <el-option v-for="item in ACTIONS" :key="item" :label="item" :value="item" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <div class="card-block">
      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="created_at" label="时间" width="190" />
        <el-table-column prop="admin_username" label="操作人" width="120" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column label="动作" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_name" label="对象" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="show_detail(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无日志" :image-size="70" />
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

    <el-dialog v-model="detail_visible" title="变更详情" width="680px">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="时间">{{ detail_row?.created_at }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ detail_row?.admin_username }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ detail_row?.module }}</el-descriptions-item>
        <el-descriptions-item label="动作">{{ detail_row?.action }}</el-descriptions-item>
        <el-descriptions-item label="对象" :span="2">{{ detail_row?.target_name }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 14px">
        <b>变更前</b>
        <pre class="json">{{ detail_row?.detail_before ? JSON.stringify(detail_row.detail_before, null, 2) : '无' }}</pre>
        <b>变更后</b>
        <pre class="json">{{ detail_row?.detail_after ? JSON.stringify(detail_row.detail_after, null, 2) : '无' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.json {
  background: #f7f8fc;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
}
</style>
