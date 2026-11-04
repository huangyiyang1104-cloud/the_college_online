import http from './http'

// ---------- 认证 ----------
export const admin_login = (username: string, password: string) =>
  http.post('/admin/auth/login', { username, password })

export const admin_logout = () => http.post('/admin/auth/logout')

export const admin_me = () => http.get('/admin/auth/me')

// ---------- 看板 ----------
export const fetch_dashboard = () => http.get('/admin/dashboard/summary')

// ---------- 学科 ----------
export const list_subjects = (params: Record<string, unknown>) =>
  http.get('/admin/subjects', { params })

export const create_subject = (body: Record<string, unknown>) => http.post('/admin/subjects', body)

export const update_subject = (id: string, body: Record<string, unknown>) =>
  http.patch(`/admin/subjects/${id}`, body)

export const delete_subject = (id: string) => http.delete(`/admin/subjects/${id}`)

// ---------- 课程 ----------
export const list_courses = (subject_id: string) =>
  http.get(`/admin/subjects/${subject_id}/courses`)

export const create_course = (subject_id: string, body: Record<string, unknown>) =>
  http.post(`/admin/subjects/${subject_id}/courses`, body)

export const update_course = (id: string, body: Record<string, unknown>) =>
  http.patch(`/admin/courses/${id}`, body)

export const delete_course = (id: string) => http.delete(`/admin/courses/${id}`)

export const reorder_courses = (subject_id: string, course_ids: string[]) =>
  http.put(`/admin/subjects/${subject_id}/courses/order`, { course_ids })

// ---------- 题库 ----------
export const list_questions = (params: Record<string, unknown>) =>
  http.get('/admin/questions', { params })

export const create_question = (body: Record<string, unknown>) =>
  http.post('/admin/questions', body)

export const update_question = (id: string, body: Record<string, unknown>) =>
  http.patch(`/admin/questions/${id}`, body)

export const delete_question = (id: string) => http.delete(`/admin/questions/${id}`)

// ---------- 导入 ----------
const upload = (url: string, file: File, subject_id: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('subject_id', subject_id)
  return http.post(url, form, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const upload_course_excel = (file: File, subject_id: string) =>
  upload('/admin/course-imports', file, subject_id)

export const upload_question_excel = (file: File, subject_id: string) =>
  upload('/admin/question-imports', file, subject_id)

export const confirm_course_import = (job_id: string) =>
  http.patch(`/admin/course-imports/${job_id}`, { status: 'confirmed' })

export const confirm_question_import = (job_id: string) =>
  http.patch(`/admin/question-imports/${job_id}`, { status: 'confirmed' })

// ---------- 面试资料库 ----------
export const list_docs = (params: Record<string, unknown>) =>
  http.get('/admin/interview-docs', { params })

export const upload_doc = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/admin/interview-docs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const retry_doc = (id: string) => http.post(`/admin/interview-docs/${id}/processing-jobs`)

export const delete_doc = (id: string) => http.delete(`/admin/interview-docs/${id}`)

export const retrieval_test = (params: Record<string, unknown>) =>
  http.get('/admin/retrieval-tests', { params })

// ---------- 学员 ----------
export const list_students = (params: Record<string, unknown>) =>
  http.get('/admin/students', { params })

export const update_student_status = (id: string, status: number) =>
  http.patch(`/admin/students/${id}`, { status })

// ---------- 系统用户 ----------
export const list_admin_users = (params: Record<string, unknown>) =>
  http.get('/admin/users', { params })

export const create_admin_user = (body: Record<string, unknown>) =>
  http.post('/admin/users', body)

export const update_admin_user = (id: string, body: Record<string, unknown>) =>
  http.patch(`/admin/users/${id}`, body)

export const delete_admin_user = (id: string) => http.delete(`/admin/users/${id}`)

// ---------- 操作日志 ----------
export const list_logs = (params: Record<string, unknown>) =>
  http.get('/admin/operation-logs', { params })
