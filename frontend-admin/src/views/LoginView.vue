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
const form = reactive({ username: '', password: '' })
const student_entry = import.meta.env.DEV ? 'http://localhost:5173' : '/'

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
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
    await auth.login(form.username.trim(), form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch {
    // 错误提示由请求拦截器统一处理
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1>管理后台</h1>
      <p class="tip">云枢智学 · 内容运营与系统管理</p>

      <el-form ref="form_ref" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入后台账号" autocomplete="username" />
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
        <el-button type="primary" class="submit" :loading="submitting" @click="submit">
          {{ submitting ? '登录中…' : '登录' }}
        </el-button>
      </el-form>

      <p class="tip foot">
        学员端是独立页面：<a :href="student_entry" target="_blank" rel="noopener">前往学员端</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.submit {
  width: 100%;
  margin-top: 6px;
}

.foot {
  margin-top: 18px;
}
</style>
