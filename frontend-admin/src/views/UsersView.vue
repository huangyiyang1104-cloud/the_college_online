<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  create_admin_user,
  delete_admin_user,
  list_admin_users,
  update_admin_user,
} from '../api/admin'
import { use_auth_store } from '../stores/auth'

const auth = use_auth_store()
const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const pagination = reactive({ page: 1, page_size: 10 })

const dialog = ref(false)
const editing = ref<any>(null)
const form_ref = ref<FormInstance>()
const form = reactive({ username: '', password: '', role: 2 })
const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ min: 6, max: 32, message: '密码 6-32 位', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const data: any = await list_admin_users({ page: pagination.page, page_size: pagination.page_size })
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function open_dialog(row?: any) {
  editing.value = row || null
  form.username = row?.username || ''
  form.password = ''
  form.role = row?.role ?? 2
  dialog.value = true
}

async function submit() {
  if (!form_ref.value) return
  const valid = await form_ref.value.validate().catch(() => false)
  if (!valid) return

  if (editing.value) {
    const payload: Record<string, unknown> = { role: form.role }
    if (form.password) payload.password = form.password
    await update_admin_user(editing.value.id, payload)
  } else {
    await create_admin_user({ username: form.username, password: form.password, role: form.role })
  }
  ElMessage.success('已保存')
  dialog.value = false
  load()
}

async function toggle(row: any) {
  await update_admin_user(row.id, { status: row.status ? 0 : 1 })
  ElMessage.success(row.status ? '已停用' : '已启用')
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`删除后台账号「${row.username}」？`, '确认删除', { type: 'warning' })
  await delete_admin_user(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>系统用户</h2>
        <p>仅超管可管理；内置账号不可删除与停用，且至少保留一个超管</p>
      </div>
      <el-button type="primary" @click="open_dialog()">新增账号</el-button>
    </div>

    <div class="card-block">
      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="username" label="账号" min-width="160">
          <template #default="{ row }">
            {{ row.username }}
            <el-tag v-if="row.is_builtin" size="small" type="info">内置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === 1 ? 'danger' : 'info'">
              {{ row.role === 1 ? '超管' : '运营' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="190" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'info'" size="small">
              {{ row.status ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="open_dialog(row)">编辑</el-button>
            <el-button link :disabled="row.is_builtin" @click="toggle(row)">
              {{ row.status ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" :disabled="row.is_builtin" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 14px; justify-content: flex-end"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑账号' : '新增账号'" width="480px">
      <el-form ref="form_ref" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="!!editing" maxlength="64" />
        </el-form-item>
        <el-form-item :label="editing ? '重置密码' : '密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editing ? '留空表示不修改' : '6-32 位'"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio :value="2">运营</el-radio>
            <el-radio :value="1">超管</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
