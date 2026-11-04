"""B4 面试资料库接口（controller），业务在 services/doc_service。"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.services import doc_service, ingest_service

router = APIRouter(tags=["admin-interview-docs"])


@router.get("/admin/interview-docs")
def list_docs(
    status: int | None = Query(default=None, ge=1, le=4),
    keyword: str | None = Query(default=None, max_length=255),
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    items, total = doc_service.list_docs(
        status, keyword, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("/admin/interview-docs", status_code=201)
def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    result = doc_service.upload(file, current.id, db)
    # 上传后异步解析入库，避免让上传请求等 20 多秒；状态先停在「待处理」
    background_tasks.add_task(ingest_service.process_doc_background, int(result["id"]))
    return ok(result)


@router.get("/admin/interview-docs/{doc_id}")
def get_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(doc_service.get(doc_id, db))


@router.post("/admin/interview-docs/{doc_id}/processing-jobs", status_code=202)
def retry_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(doc_service.retry(doc_id, current.id, db))


@router.delete("/admin/interview-docs/{doc_id}", status_code=204)
def delete_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    doc_service.delete(doc_id, current.id, db)
    return None


@router.get("/admin/retrieval-tests")
def retrieval_test(
    subject_id: int | None = Query(default=None),
    query: str | None = Query(default=None, max_length=200),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(doc_service.retrieval_test(subject_id, query, top_k))
