<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { send_sms_code } from '../api/student'
import { use_auth_store } from '../stores/auth'

const router = useRouter()
const auth = use_auth_store()

const form_ref = ref<FormInstance>()
const submitting = ref(false)
const sending = ref(false)
const countdown = ref(0)
let timer: number | undefined

const form = reactive({ phone: '', code: '', password: '', confirm: '' })

const rules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度为 6-32 位', trigger: 'blur' },
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
          callback(new Error('密码需同时包含字母与数字'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

const send_label = computed(() =>
  countdown.value > 0 ? `${countdown.value} 秒后重发` : '获取验证码',
)

function start_countdown(seconds: number) {
  countdown.value = seconds
  timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(timer)
  }, 1000)
}

async function send_code() {
  if (!/^1\d{10}$/.test(form.phone)) {
    ElMessage.warning('请先填写正确的手机号')
    return
  }
  sending.value = true
  try {
    const data: any = await send_sms_code(form.phone.trim())
    ElMessage.success('验证码已发送，请查看短信')
    start_countdown(data.resend_after || 60)
  } finally {
    sending.value = false
  }
}

async function submit() {
  if (!form_ref.value) return
  const valid = await form_ref.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await auth.register(form.phone.trim(), form.code.trim(), form.password)
    ElMessage.success('注册成功')
    router.replace('/home')
  } catch {
    // 提示由拦截器统一处理
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h1>创建账号</h1>
      <p class="tip">当前为测试环境，仅支持已加入白名单的手机号</p>

      <el-form ref="form_ref" :model="form" :rules="rules" label-position="top">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" maxlength="11" placeholder="请输入手机号" />
        </el-form-item>

        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input v-model="form.code" maxlength="6" placeholder="6 位验证码" />
            <el-button :disabled="countdown > 0" :loading="sending" @click="send_code">
              {{ send_label }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="设置密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="6-32 位，字母 + 数字" />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>

        <el-button type="primary" style="width: 100%" :loading="submitting" @click="submit">
          {{ submitting ? '注册中…' : '注册并登录' }}
        </el-button>
      </el-form>

      <p class="switch">
        已有账号？<router-link to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>
