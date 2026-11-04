"""C6 学科面试接口（controller），业务在 services/interview_service。

注意路由注册顺序：`/quota` 必须写在 `/{session_id}` 之前，否则会被当成会话 id。
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, page_params
from app.core.db import get_db
from app.core.errors import api_error, ok, paged
from app.models import user
from app.schemas import (
    interview_answer_request,
    interview_create_request,
    interview_finish_request,
)
from app.services import audio_service, interview_service

router = APIRouter(prefix="/interviews", tags=["student-interview"])


@router.get("/quota")
def get_quota(current: user = Depends(get_current_user)):
    return ok(interview_service.quota(current))


@router.get("")
def list_interviews(
    source: int | None = Query(default=None, ge=1, le=2),
    pagination: page_params = Depends(page_params),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = interview_service.list_sessions(
        current, source, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("", status_code=201)
def create_interview(
    body: interview_create_request,
    background_tasks: BackgroundTasks,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = interview_service.create(current, body.source, body.subject_id, db)

    session_pk = int(data["id"])
    items = [(item["question_index"], item["question_text"]) for item in data["questions"]]

    # 第 1 题同步合成：保证学员一进页面就有语音播报（约 4 秒）
    if items:
        try:
            audio_service.generate(session_pk, items[0][0], items[0][1])
        except Exception:
            pass  # 语音失败不影响面试，前端有纯文字降级

    # 其余题目后台生成，不拖慢接口
    if len(items) > 1:
        background_tasks.add_task(audio_service.generate_many, session_pk, items[1:])

    return ok(data)


@router.get("/{session_id}")
def get_interview(
    session_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(interview_service.detail(current, session_id, db))


@router.post("/{session_id}/questions/{question_index}/answers")
def submit_answer(
    session_id: int,
    question_index: int,
    body: interview_answer_request,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(
        interview_service.answer(
            current,
            session_id,
            question_index,
            body.answer_mode,
            body.answer_text,
            body.is_follow_up,
            db,
        )
    )


@router.get("/{session_id}/questions/{question_index}/audio")
def get_question_audio(
    session_id: int,
    question_index: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """题目语音：直接返回二进制音频流，不套 code/message/data 包装。"""
    data = interview_service.load_audio(current, session_id, question_index, db)
    return Response(content=data, media_type="audio/wav")


@router.get("/{session_id}/report")
def get_report(
    session_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """面试报告：仅已结束的会话可查，逐题含分数、回答、追问与点评。"""
    return ok(interview_service.report(current, session_id, db))


@router.post("/{session_id}/asr")
async def transcribe_answer(
    session_id: int,
    request: Request,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """语音作答转写：body 是 WAV 二进制，只返回文字，不评分。"""
    # 先按 Content-Length 快速拒绝超大请求，避免把几十 MB 读进内存
    declared = int(request.headers.get("content-length") or 0)
    if declared > 4 * 1024 * 1024:
        raise api_error(10003, "音频文件过大，请分段作答", 400)

    audio = await request.body()
    return ok(interview_service.transcribe(current, session_id, audio, db))


@router.post("/{session_id}/questions/{question_index}/follow-ups")
def create_follow_up(
    session_id: int,
    question_index: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(interview_service.follow_up(current, session_id, question_index, db))


@router.patch("/{session_id}")
def finish_interview(
    session_id: int,
    body: interview_finish_request,
    background_tasks: BackgroundTasks,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = interview_service.finish(current, session_id, body.status, db)
    # 结语语音（模型出台词 + TTS + RVC 约 8 秒）放后台，结算本身立即返回
    background_tasks.add_task(
        audio_service.generate_verdict,
        session_id,
        bool(data["passed"]),
        float(data["total_score"]),
    )
    return ok(data)


@router.get("/{session_id}/verdict-audio")
def get_verdict_audio(
    session_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """面试官结语语音：直接返回二进制流，未生成时 404。"""
    data = interview_service.verdict_audio(current, session_id, db)
    return Response(content=data, media_type="audio/wav")


@router.post("/{session_id}/ws-tickets", status_code=201)
def create_ws_ticket(
    session_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(interview_service.create_ws_ticket(current, session_id, db))
