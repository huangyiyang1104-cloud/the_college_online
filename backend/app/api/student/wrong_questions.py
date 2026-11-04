"""C5 错题本接口（controller），业务在 services/wrong_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import user
from app.schemas import wrong_attempt
from app.services import wrong_service

router = APIRouter(prefix="/wrong-questions", tags=["student-wrong-questions"])


@router.get("")
def list_wrong_questions(
    subject_id: int | None = Query(default=None),
    pagination: page_params = Depends(page_params),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = wrong_service.list_wrong(
        current, subject_id, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("/{question_id}/attempts")
def retry_wrong_question(
    question_id: int,
    body: wrong_attempt,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(wrong_service.attempt(current, question_id, body.option_keys, db))


@router.delete("/{question_id}", status_code=204)
def remove_wrong_question(
    question_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wrong_service.remove(current, question_id, db)
    return None
