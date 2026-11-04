<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { get_me, update_me } from '../api/student'
import { mask_phone, use_auth_store } from '../stores/auth'

const router = useRouter()
const auth = use_auth_store()

const loading = ref(false)
const saving = ref(false)
const form_ref = ref<FormInstance>()
const profile = reactive({
  phone: '',
  nickname: '',
  city: '',
  created_at: '',
  stats: { course_completed: 0, paper_count: 0, wrong_count: 0, interview_count: 0 },
})

const rules: FormRules = {
  nickname: [{ max: 64, message: '昵称不超过 64 个字符', trigger: 'blur' }],
  city: [{ max: 64, message: '城市不超过 64 个字符', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const data: any = await get_me()
    Object.assign(profile, data)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form_ref.value) return
  const valid = await form_ref.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data: any = await update_me({
      nickname: profile.nickname.trim(),
      city: profile.city.trim(),
    })
    Object.assign(profile, data)
    auth.student = { id: data.id, phone: data.phone, nickname: data.nickname }
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <h2 class="page-title">个人信息</h2>
    <p class="page-sub">手机号是账号唯一标识，首期不支持修改</p>

    <div class="card" style="margin-bottom: 16px">
      <div class="meta-row" style="font-size: 14px; color: var(--ink)">
        <span>手机号</span>
        <span>{{ mask_phone(profile.phone) }}</span>
      </div>
      <div class="meta-row" style="font-size: 14px; color: var(--ink); margin-top: 12px">
        <span>注册时间</span>
        <span>{{ profile.created_at ? profile.created_at.slice(0, 10) : '-' }}</span>
      </div>
    </div>

    <div class="card">
      <el-form ref="form_ref" :model="profile" :rules="rules" label-position="top">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="profile.nickname" maxlength="64" placeholder="给自己起个名字" />
        </el-form-item>
        <el-form-item label="城市" prop="city">
          <el-input v-model="profile.city" maxlength="64" placeholder="选填" />
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        <el-button @click="router.push('/records')">查看学习记录</el-button>
      </el-form>
    </div>
  </div>
</template>
