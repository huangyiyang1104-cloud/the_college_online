"""简历接口：上传、查询当前简历、删除。

上传只做落库与投递，解析在后台跑（PDF 提取 + 切片 + 向量化约 5–15 秒），
前端通过 GET /resumes/current 的 status 判断是否就绪。
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import ok
from app.models import user
from app.services import resume_service

router = APIRouter(prefix="/resumes", tags=["学员-简历"])


@router.post("", status_code=201)
def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = resume_service.upload(current, file, db)
    background_tasks.add_task(resume_service.parse_task, int(data["id"]))
    return ok(data)


@router.get("/current")
def get_current_resume(
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(resume_service.current(current, db))


@router.delete("/current", status_code=204)
def delete_current_resume(
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume_service.remove(current, db)
