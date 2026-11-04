<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { list_students, update_student_status } from '../api/admin'

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const filters = reactive({ keyword: '', status: undefined as number | undefined, page: 1, page_size: 10 })

async function load() {
  loading.value = true
  try {
    const data: any = await list_students({
      page: filters.page,
      page_size: filters.page_size,
      keyword: filters.keyword || undefined,
      status: filters.status,
    })
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function toggle(row: any) {
  const next = row.status ? 0 : 1
  await update_student_status(row.id, next)
  row.status = next
  ElMessage.success(next ? '已启用' : '已禁用')
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>学员管理</h2>
        <p>只展示账号信息与点亮课程数；不展示简历、刷题与面试结果</p>
      </div>
    </div>

    <div class="toolbar">
      <el-input v-model="filters.keyword" placeholder="手机号 / 昵称" clearable style="width: 200px" @keyup.enter="load" />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 140px" @change="load">
        <el-option label="正常" :value="1" />
        <el-option label="已禁用" :value="0" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <div class="card-block">
      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="phone" label="手机号" width="150" />
        <el-table-column prop="nickname" label="昵称" width="140" />
        <el-table-column prop="created_at" label="注册时间" width="190" />
        <el-table-column prop="completed_course_count" label="点亮课程" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link :type="row.status ? 'danger' : 'primary'" @click="toggle(row)">
              {{ row.status ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无学员" :image-size="70" />
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
  </div>
</template>
