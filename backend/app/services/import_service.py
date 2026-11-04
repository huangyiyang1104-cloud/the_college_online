"""批量导入：解析 → 暂存 Redis → 确认入库。

导入任务不落库（与 03 数据库设计一致），Redis TTL 30 分钟。
"""

import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.cache import load_import_job, save_import_job
from app.core.clock import utcnow
from app.core.errors import conflict, not_found
from app.models import course, question
from app.repositories import course_admin_repo, question_admin_repo, subject_admin_repo
from app.services import audit_service, import_parser

KIND_COURSE = "course"
KIND_QUESTION = "question"
STATUS_PREVIEW = "preview"
STATUS_CONFIRMED = "confirmed"


def _ensure_subject(db: Session, subject_id: int) -> None:
    if not subject_admin_repo.get_active(db, subject_id):
        raise not_found("学科不存在")


def _save_job(kind: str, subject_id: int, valid: list, errors: list, total: int, admin_id: int) -> str:
    job_id = f"imp-{uuid.uuid4().hex[:12]}"
    save_import_job(
        job_id,
        {
            "kind": kind,
            "subject_id": subject_id,
            "status": STATUS_PREVIEW,
            "rows": valid,
            "summary": {"total": total, "valid": len(valid), "invalid": len(errors)},
            "errors": errors[: import_parser.MAX_ERRORS],
            "truncated": len(errors) > import_parser.MAX_ERRORS,
            "created_by": admin_id,
            "created_at": utcnow().isoformat(),
        },
    )
    return job_id


def _summary(total: int, valid: list, errors: list) -> dict:
    return {"total": total, "valid": len(valid), "invalid": len(errors)}


def create_course_import(file: UploadFile, subject_id: int, admin_id: int, db: Session) -> dict:
    _ensure_subject(db, subject_id)

    rows = import_parser.read_rows(file.filename, file.file.read())
    valid, errors = import_parser.parse_course_rows(rows)
    job_id = _save_job(KIND_COURSE, subject_id, valid, errors, len(rows), admin_id)

    return {
        "import_id": job_id,
        "status": STATUS_PREVIEW,
        "summary": _summary(len(rows), valid, errors),
        "preview": [
            {
                "row": item["row"],
                "title": item["title"],
                "duration_minutes": item["duration_minutes"],
                "bilibili_url": item["bilibili_url"],
            }
            for item in valid[: import_parser.MAX_PREVIEW]
        ],
        "errors": errors[: import_parser.MAX_ERRORS],
        "truncated": len(errors) > import_parser.MAX_ERRORS,
    }


def confirm_course_import(job_id: str, admin_id: int, db: Session) -> dict:
    job = load_import_job(job_id)
    if not job or job.get("kind") != KIND_COURSE:
        raise not_found("导入任务不存在或已过期")
    if job.get("status") != STATUS_PREVIEW:
        raise conflict("该导入任务已确认或已过期", 30004)

    subject_id = job["subject_id"]
    next_order = course_admin_repo.max_sort_order(db, subject_id) + 1

    for item in job["rows"]:
        course_admin_repo.add(
            db,
            course(
                subject_id=subject_id,
                title=item["title"],
                description="",
                duration_minutes=item["duration_minutes"],
                bilibili_url=item["bilibili_url"],
                sort_order=next_order,
                status=1,
            ),
        )
        next_order += 1

    job["status"] = STATUS_CONFIRMED
    save_import_job(job_id, job)
    audit_service.record(
        db, admin_id, "课程内容", "导入", "course", subject_id, f"{len(job['rows'])} 门课程"
    )
    db.commit()
    return {"import_id": job_id, "status": STATUS_CONFIRMED, "imported": len(job["rows"])}


def create_question_import(file: UploadFile, subject_id: int, admin_id: int, db: Session) -> dict:
    _ensure_subject(db, subject_id)

    rows = import_parser.read_rows(file.filename, file.file.read())
    valid, errors = import_parser.parse_question_rows(rows)
    job_id = _save_job(KIND_QUESTION, subject_id, valid, errors, len(rows), admin_id)

    return {
        "import_id": job_id,
        "status": STATUS_PREVIEW,
        "summary": _summary(len(rows), valid, errors),
        "preview": [
            {
                "row": item["row"],
                "title": item["title"],
                "type": item["type"],
                "difficulty": item["difficulty"],
                "answer": item["answer"],
            }
            for item in valid[: import_parser.MAX_PREVIEW]
        ],
        "errors": errors[: import_parser.MAX_ERRORS],
        "truncated": len(errors) > import_parser.MAX_ERRORS,
    }


def confirm_question_import(job_id: str, admin_id: int, db: Session) -> dict:
    job = load_import_job(job_id)
    if not job or job.get("kind") != KIND_QUESTION:
        raise not_found("导入任务不存在或已过期")
    if job.get("status") != STATUS_PREVIEW:
        raise conflict("该导入任务已确认或已过期", 30004)

    subject_id = job["subject_id"]
    for item in job["rows"]:
        is_short_answer = item["type"] == 4
        row = question_admin_repo.add(
            db,
            question(
                subject_id=subject_id,
                type=item["type"],
                difficulty=item.get("difficulty", 2),
                category=item.get("category", ""),
                title=item["title"],
                score=20 if is_short_answer else 10,
                reference_answer=item["answer"] if is_short_answer else None,
                analysis=item.get("analysis") or None,
                status=1,
            ),
        )
        question_admin_repo.add_options(db, row.id, item.get("options", []))
        question_admin_repo.add_tags(db, row.id, item.get("tags", []))

    job["status"] = STATUS_CONFIRMED
    save_import_job(job_id, job)
    audit_service.record(
        db, admin_id, "刷题题库", "导入", "question", subject_id, f"{len(job['rows'])} 道题"
    )
    db.commit()
    return {"import_id": job_id, "status": STATUS_CONFIRMED, "imported": len(job["rows"])}


def get_job(job_id: str) -> dict:
    job = load_import_job(job_id)
    if not job:
        raise not_found("导入任务不存在或已过期")
    return {
        "import_id": job_id,
        "kind": job["kind"],
        "status": job["status"],
        "summary": job["summary"],
        "truncated": job.get("truncated", False),
    }
