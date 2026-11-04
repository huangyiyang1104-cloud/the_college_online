"""学员端接口聚合。"""

from fastapi import APIRouter

from app.api.student import (
    auth,
    catalog,
    interview,
    practice,
    records,
    resumes,
    users,
    wrong_questions,
)

student_router = APIRouter()
student_router.include_router(auth.router)
student_router.include_router(users.router)
student_router.include_router(catalog.router)
student_router.include_router(records.router)
student_router.include_router(practice.router)
student_router.include_router(wrong_questions.router)
student_router.include_router(interview.router)
student_router.include_router(resumes.router)
