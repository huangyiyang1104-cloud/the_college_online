import http from './http'
import { get_access_token } from '../utils/token_storage'

// ---------- 认证 ----------
export const send_sms_code = (phone: string) =>
  http.post('/auth/sms-codes', { phone, scene: 'register' })

export const register = (phone: string, code: string, password: string) =>
  http.post('/auth/register', { phone, code, password })

export const login = (phone: string, password: string) =>
  http.post('/auth/login', { phone, password })

export const logout = () => http.post('/auth/logout')

// ---------- C2 首页与节点图 ----------
export const fetch_home = () => http.get('/home')

export const list_subjects = (params: Record<string, unknown>) =>
  http.get('/subjects', { params })

export const fetch_subject = (id: string) => http.get(`/subjects/${id}`)

export const record_visit = (course_id: string) => http.post(`/courses/${course_id}/visits`)

export const complete_course = (course_id: string) =>
  http.put(`/courses/${course_id}/completion`)

export const uncomplete_course = (course_id: string) =>
  http.delete(`/courses/${course_id}/completion`)

// ---------- C3 学习记录 ----------
export const list_records = (params: Record<string, unknown>) =>
  http.get('/learning-records', { params })

export const records_summary = () => http.get('/learning-records/summary')

// ---------- C4 刷题 ----------
export const fetch_practice_paper = (subject_id: string) =>
  http.get(`/subjects/${subject_id}/practice-paper`)

export const submit_paper = (subject_id: string, answers: unknown[]) =>
  http.post('/papers', { subject_id, answers })

export const list_papers = (params: Record<string, unknown>) => http.get('/papers', { params })

export const fetch_paper = (id: string) => http.get(`/papers/${id}`)

// ---------- C5 错题本 ----------
export const list_wrong = (params: Record<string, unknown>) =>
  http.get('/wrong-questions', { params })

export const retry_wrong = (question_id: string, option_keys: string[]) =>
  http.post(`/wrong-questions/${question_id}/attempts`, { option_keys })

export const remove_wrong = (question_id: string) => http.delete(`/wrong-questions/${question_id}`)

// ---------- C6 学科面试 ----------
export const interview_quota = () => http.get('/interviews/quota')

// 出题要检索 + 调模型，单独放宽超时
export const start_interview = (subject_id: string) =>
  http.post('/interviews', { source: 1, subject_id }, { timeout: 180000 })

export const fetch_interview = (id: string) => http.get(`/interviews/${id}`)

export const submit_interview_answer = (
  id: string,
  question_index: number,
  body: Record<string, unknown>,
) =>
  http.post(`/interviews/${id}/questions/${question_index}/answers`, body, {
    timeout: 120000,
  })

export const request_follow_up = (id: string, question_index: number) =>
  http.post(`/interviews/${id}/questions/${question_index}/follow-ups`)

export const finish_interview = (id: string, status: number) =>
  http.patch(`/interviews/${id}`, { status })

export const list_interviews = (params: Record<string, unknown>) =>
  http.get('/interviews', { params })

// C8 面试报告：仅已结束的会话可查
export const fetch_interview_report = (id: string) => http.get(`/interviews/${id}/report`)

// ---------- C7 简历 ----------
// 上传走 multipart，axios 会自己补 boundary，不要手动设 Content-Type
export const upload_resume = (form: FormData) =>
  http.post('/resumes', form, { timeout: 60000 })

export const fetch_current_resume = () => http.get('/resumes/current')

export const delete_resume = () => http.delete('/resumes/current')

// 简历面试：出题同样要检索 + 调模型，超时放宽
export const start_resume_interview = () =>
  http.post('/interviews', { source: 2 }, { timeout: 180000 })

// 题目语音：走原生 fetch 拿二进制，绕开 axios 拦截器的 {code,data} 解包
export async function fetch_question_audio(
  id: string,
  question_index: number,
): Promise<string> {
  const token = get_access_token()
  const response = await fetch(`/api/v1/interviews/${id}/questions/${question_index}/audio`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`audio ${response.status}`)
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

// 语音作答转写：上传一段 WAV，返回识别文本（不评分）
export async function transcribe_answer(id: string, wav: Blob): Promise<string> {
  const token = get_access_token()
  const response = await fetch(`/api/v1/interviews/${id}/asr`, {
    method: 'POST',
    headers: {
      'Content-Type': 'audio/wav',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: wav,
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload || payload.code !== 0) {
    throw new Error(payload?.message || `asr ${response.status}`)
  }
  return payload.data?.text || ''
}

// 面试官结语语音：结算后由后台生成，需轮询等待
export async function fetch_verdict_audio(id: string): Promise<string> {
  const token = get_access_token()
  const response = await fetch(`/api/v1/interviews/${id}/verdict-audio`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`verdict audio ${response.status}`)
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

// ---------- 个人信息 ----------
export const get_me = () => http.get('/users/me')

export const update_me = (body: Record<string, unknown>) => http.patch('/users/me', body)
