"""后台接口聚合：按模块拆分路由，统一在 /api/v1 下暴露。"""

from fastapi import APIRouter

from app.api.admin import auth, courses, dashboard, docs, imports, logs, questions, students, subjects, users

admin_router = APIRouter()
admin_router.include_router(auth.router)
admin_router.include_router(dashboard.router)
admin_router.include_router(subjects.router)
admin_router.include_router(courses.router)
admin_router.include_router(questions.router)
admin_router.include_router(imports.router)
admin_router.include_router(docs.router)
admin_router.include_router(students.router)
admin_router.include_router(users.router)
admin_router.include_router(logs.router)
