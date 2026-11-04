<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { use_auth_store } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = use_auth_store()

const form_ref = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ phone: '', password: '' })

const rules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度为 6-32 位', trigger: 'blur' },
  ],
}

async function submit() {
  if (!form_ref.value) return
  const valid = await form_ref.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await auth.login(form.phone.trim(), form.password)
    ElMessage.success('欢迎回来')
    router.replace((route.query.redirect as string) || '/home')
  } catch {
    // 错误提示由请求拦截器统一处理
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h1>登录云枢智学</h1>
      <p class="tip">按学科顺序学课，学完自己点亮节点</p>

      <el-form ref="form_ref" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" maxlength="11" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="submitting" @click="submit">
          {{ submitting ? '登录中…' : '登录' }}
        </el-button>
      </el-form>

      <p class="switch">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>
