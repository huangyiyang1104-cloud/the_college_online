"""C4 刷题接口（controller），业务在 services/practice_service 与 paper_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import user
from app.schemas import paper_submit
from app.services import paper_service, practice_service

router = APIRouter(tags=["student-practice"])


@router.get("/subjects/{subject_id}/practice-paper")
def get_practice_paper(
    subject_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(practice_service.build_paper(current, subject_id, db))


@router.post("/papers", status_code=201)
def submit_paper(
    body: paper_submit,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(paper_service.submit(current, int(body.subject_id), body.answers, db))


@router.get("/papers")
def list_papers(
    subject_id: int | None = Query(default=None),
    pagination: page_params = Depends(page_params),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = paper_service.list_papers(
        current, subject_id, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(paper_service.get_paper(current, paper_id, db))
