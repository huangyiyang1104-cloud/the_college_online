"""C6 学科面试：配额、发起出题、作答评分、追问、结束与记录。

出题链路：学科关键词 → 向量检索切片 → LLM 出题 → 落库（题目文本与来源快照）。
评分口径：每题 0-100 分；结束分 = 各题得分求平均（未作答记 0），四舍五入取整。
"""

import json
import logging
import random
import secrets
import time
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core import cache
from app.core.cache import redis_client
from app.core.clock import beijing_day_start_utc, utcnow
from app.core.config import settings_cache
from app.core.errors import api_error, forbidden, not_found
from app.integrations import embedding, llm, vector_store
from app.integrations import tencent_asr as asr
from app.models import interview_question, interview_session, user
from app.repositories import interview_repo, subject_repo
from app.services import audio_service

QUESTION_COUNT = 5
# 候选池放大到 40 条，再随机抽 10 条喂给模型 —— 保证每次题目来源不同
RETRIEVAL_TOP_K = 40
SNIPPETS_FOR_GENERATION = 10
MIN_SNIPPETS = 3
RESUME_MIN_CHUNKS = 2  # 简历比资料库短，一页纸切出 2 片是常态
HUNDRED = Decimal("100")
CENT = Decimal("0.01")

logger = logging.getLogger("yunshu.interview")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _iso(value) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _collection() -> str:
    return settings_cache.milvus_collection_docs


def _deadline(session: interview_session):
    return session.started_at + timedelta(minutes=settings_cache.interview_minutes)


def _load_own(user_id: int, session_id: int, db: Session) -> interview_session:
    session = interview_repo.get_session(db, session_id)
    if not session:
        raise not_found("面试会话不存在")
    if session.user_id != user_id:
        raise forbidden("无权访问该面试")
    return session


def _ensure_open(session: interview_session) -> None:
    if session.status != 1:
        raise api_error(50002, "面试已结束", 409)
    if utcnow() > _deadline(session):
        raise api_error(50005, "面试已超时", 409)


EMBED_CACHE_TTL = 86400  # 学科关键词固定，向量一天内复用


def _subject_vector(subject_pk: int, query: str) -> list[float]:
    """取学科的检索向量：优先读 Redis 缓存，失败重试一次。

    同一学科反复发起面试时不再打 DashScope，既快也能避开限流（429）。
    """
    cache_key = f"embed:subject:{subject_pk}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    last_error = ""
    for attempt in (1, 2):
        try:
            vectors = embedding.embed_texts([query])
        except Exception as exc:
            last_error = type(exc).__name__
            logger.warning(
                "发起面试：向量化失败 subject=%s 第 %s 次 %s", subject_pk, attempt, last_error
            )
            vectors = None

        if vectors:
            try:
                redis_client.setex(cache_key, EMBED_CACHE_TTL, json.dumps(vectors[0]))
            except Exception:
                pass
            return vectors[0]

        if attempt == 1:
            time.sleep(1)

    raise api_error(10008, "向量化服务暂不可用，请稍后重试", 503)


def _fallback_follow_up(answer: str) -> str:
    """模型不可用时的通用追问，保证面试流程不中断。"""
    if (answer or "").strip():
        return "能结合你刚才说的，再具体讲讲实现细节和你踩过的坑吗？"
    return "这题你还没展开，能说说你的思路吗？"


def _reference_text(question_text: str) -> str:
    """用题目本身检索最相关切片作为评分参考；失败返回空串，走关键词兜底。"""
    try:
        vectors = embedding.embed_texts([question_text], timeout=15)
        if not vectors:
            return ""
        rows = vector_store.search(_collection(), vectors[0], 1)
        return rows[0].get("content", "") if rows else ""
    except Exception:
        return ""


def quota(user: user) -> dict:
    used = cache.get_interview_used(user.id)
    limit = settings_cache.interview_daily_limit
    reset_at = beijing_day_start_utc() + timedelta(days=1)
    return {
        "daily_limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "reset_at": _iso(reset_at),
    }


def _collection_resume() -> str:
    return settings_cache.milvus_collection_resume


def _create_from_resume(current: user, db: Session) -> dict:
    """简历面试：从本人简历切片随机采样出题，重点问项目细节。

    简历切片量不大（十几片），直接按 doc_id 全取再随机采样，
    比向量检索更不容易漏掉项目经历。
    """
    from app.services import resume_service  # 局部导入，避免模块级循环依赖

    resume_row = resume_service.get_ready(current, db)

    chunks = vector_store.query_doc_chunks(_collection_resume(), resume_row.id, limit=100)
    logger.info("发起简历面试：简历 %s 共 %s 个切片", resume_row.id, len(chunks))
    # 简历比资料库短，一页纸的应届简历切出 2 片是常态，这里不能用资料库的阈值
    if len(chunks) < RESUME_MIN_CHUNKS:
        raise api_error(60004, "简历内容过少，无法出题，请上传更完整的简历", 409)

    snippets = random.sample(chunks, min(SNIPPETS_FOR_GENERATION, len(chunks)))

    generated = llm.generate_resume_questions(snippets, QUESTION_COUNT)
    if not generated:
        logger.warning("发起简历面试：出题首次失败，重试 resume=%s", resume_row.id)
        generated = llm.generate_resume_questions(snippets, QUESTION_COUNT)
    if not generated:
        logger.error("发起简历面试：出题两次均失败 resume=%s", resume_row.id)
        raise api_error(10008, "出题服务繁忙，请稍后再试", 503)

    selected = generated[:QUESTION_COUNT]
    cache.incr_interview_used(current.id)

    started = utcnow()
    session = interview_repo.add_session(
        db,
        interview_session(
            user_id=current.id,
            source=2,
            subject_id=None,
            resume_id=resume_row.id,
            question_count=len(selected),
            status=1,
            started_at=started,
        ),
    )

    saved = []
    for index, item in enumerate(selected, start=1):
        snippet = snippets[item["snippet_index"]]
        saved.append(
            interview_repo.add_question(
                db,
                interview_question(
                    session_id=session.id,
                    question_index=index,
                    question_text=item["question"],
                    source_type=2,  # 2 = 简历
                    source_doc_name=resume_row.file_name,
                    source_snippet_id=f"resume-{resume_row.id}-{snippet['chunk_index']}",
                ),
            )
        )
    db.commit()
    db.refresh(session)

    return {
        "id": str(session.id),
        "source": 2,
        "status": 1,
        "question_count": session.question_count,
        "started_at": _iso(started),
        "expires_at": _iso(_deadline(session)),
        "questions": [
            {
                "question_index": row.question_index,
                "question_text": row.question_text,
                "source_type": row.source_type,
                "source_doc_name": row.source_doc_name,
            }
            for row in saved
        ],
    }


def create(current: user, source: int, subject_id: str | None, db: Session) -> dict:
    limit = settings_cache.interview_daily_limit
    if cache.get_interview_used(current.id) >= limit:
        raise api_error(50001, "今日面试次数已用完，明天再来", 429)

    if source == 2:
        return _create_from_resume(current, db)
    if source != 1:
        raise api_error(10001, "source 只能是 1（学科）或 2（简历）", 400)
    if not subject_id:
        raise api_error(10001, "学科面试需指定 subject_id", 400)
    try:
        subject_pk = int(subject_id)
    except (TypeError, ValueError):
        raise api_error(10001, "subject_id 非法", 400)

    subject = subject_repo.get_published(db, subject_pk)
    if not subject:
        raise not_found("学科不存在")

    keywords = subject_repo.keywords_of(db, subject_pk)
    query = " ".join(keywords) if keywords else subject.name

    vector = _subject_vector(subject_pk, query)
    candidates = vector_store.search(_collection(), vector, RETRIEVAL_TOP_K)
    logger.info("发起面试：学科 %s 检索到 %s 个候选片段", subject_pk, len(candidates))
    if len(candidates) < MIN_SNIPPETS:
        raise api_error(50003, "该学科的资料库切片不足，无法出题", 409)

    # 每次从候选池随机采样：题目来源不固定，避免反复考同一批内容
    snippets = random.sample(candidates, min(SNIPPETS_FOR_GENERATION, len(candidates)))

    generated = llm.generate_questions(snippets, QUESTION_COUNT)
    if not generated:
        # 模型偶发超时或返回格式异常，重试一次再判失败
        logger.warning("发起面试：出题首次失败，重试 subject=%s", subject_pk)
        generated = llm.generate_questions(snippets, QUESTION_COUNT)
    if not generated:
        logger.error("发起面试：出题两次均失败 subject=%s", subject_pk)
        raise api_error(10008, "出题服务繁忙，请稍后再试", 503)

    selected = generated[:QUESTION_COUNT]
    # 发起即扣：进入面试就占一次额度，中途退出不退还
    cache.incr_interview_used(current.id)

    started = utcnow()
    session = interview_repo.add_session(
        db,
        interview_session(
            user_id=current.id,
            source=1,
            subject_id=subject_pk,
            question_count=len(selected),
            status=1,
            started_at=started,
        ),
    )

    names = interview_repo.doc_names(db, [item["doc_id"] for item in snippets])
    rows = []
    for index, item in enumerate(selected, start=1):
        snippet = snippets[item["snippet_index"]]
        rows.append(
            interview_repo.add_question(
                db,
                interview_question(
                    session_id=session.id,
                    question_index=index,
                    question_text=item["question"],
                    source_type=1,
                    source_doc_name=names.get(snippet["doc_id"], ""),
                    source_snippet_id=f"{snippet['doc_id']}-{snippet['chunk_index']}",
                ),
            )
        )
    db.commit()
    db.refresh(session)
    # 语音预生成交给 controller 投递到后台任务，避免发起接口多等 20 秒

    return {
        "id": str(session.id),
        "source": 1,
        "status": 1,
        "question_count": session.question_count,
        "started_at": _iso(started),
        "expires_at": _iso(_deadline(session)),
        "questions": [
            {
                "question_index": row.question_index,
                "question_text": row.question_text,
                "source_type": row.source_type,
                "source_doc_name": row.source_doc_name,
            }
            for row in rows
        ],
    }


def detail(current: user, session_id: int, db: Session) -> dict:
    session = _load_own(current.id, session_id, db)
    questions = interview_repo.list_questions(db, session_id)

    remaining = 0
    if session.status == 1:
        remaining = max(0, int((_deadline(session) - utcnow()).total_seconds()))

    items = []
    current_index = None
    for row in questions:
        answered = bool((row.answer_text or "").strip())
        if not answered and current_index is None:
            current_index = row.question_index
        items.append(
            {
                "question_index": row.question_index,
                "question_text": row.question_text,
                "is_answered": answered,
                # 回填已答内容，支持重新作答时在原答案上修改
                "answer_text": row.answer_text or "",
                "answer_mode": row.answer_mode,
                "follow_up_used": bool((row.follow_up_text or "").strip()),
                "follow_up_text": row.follow_up_text or None,
                "score": float(row.score) if row.score is not None else None,
                # 已答题只读展示点评，供回看
                "ai_comment": row.ai_comment or "",
            }
        )
    if current_index is None and questions:
        current_index = questions[-1].question_index

    data = {
        "id": str(session.id),
        "status": session.status,
        "source": session.source,
        "subject_id": str(session.subject_id) if session.subject_id else None,
        "remaining_seconds": remaining,
        "current_index": current_index or 1,
        "questions": items,
    }
    # 已结束的会话把结算结果一并带回，重进页面也能看成绩、听结语
    if session.status != 1:
        pass_score = settings_cache.interview_pass_score
        total = float(session.total_score) if session.total_score is not None else None
        data["total_score"] = total
        data["pass_score"] = pass_score
        data["passed"] = total is not None and total >= pass_score
        data["duration_seconds"] = session.duration_seconds
        data["answered_count"] = sum(1 for row in questions if (row.answer_text or "").strip())
        data["summary"] = _verdict(
            bool(data["passed"]), total or 0.0, pass_score, data["answered_count"], len(questions)
        )
    return data


def answer(
    current: user,
    session_id: int,
    question_index: int,
    answer_mode: int,
    answer_text: str,
    is_follow_up: bool,
    db: Session,
) -> dict:
    session = _load_own(current.id, session_id, db)
    _ensure_open(session)

    row = interview_repo.get_question(db, session_id, question_index)
    if not row:
        raise not_found("题目不存在")

    reference = _reference_text(row.question_text)
    scored = llm.score_short_answer(row.question_text, reference, answer_text, timeout=45)
    if scored:
        ratio, comment = scored
    else:
        ratio, comment = llm.fallback_score(reference, answer_text)
    score = (Decimal(ratio) * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)

    if is_follow_up:
        row.follow_up_answer = answer_text
        base = Decimal(row.score) if row.score is not None else score
        row.score = ((base + score) / Decimal(2)).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        row.answer_mode = answer_mode
        row.answer_text = answer_text
        row.score = score
        row.ai_comment = comment
        row.answered_at = utcnow()

    db.commit()
    db.refresh(row)

    return {
        "question_index": row.question_index,
        "score": float(row.score) if row.score is not None else None,
        "ai_comment": row.ai_comment or comment,
        "answered_at": _iso(row.answered_at or utcnow()),
    }


def follow_up(current: user, session_id: int, question_index: int, db: Session) -> dict:
    session = _load_own(current.id, session_id, db)
    _ensure_open(session)

    row = interview_repo.get_question(db, session_id, question_index)
    if not row:
        raise not_found("题目不存在")
    if (row.follow_up_text or "").strip():
        raise api_error(50004, "本题已完成追问", 409)

    # 追问失败不中断面试：模型超时/异常时用一句通用追问兜底
    text = llm.generate_follow_up(row.question_text, row.answer_text or "", timeout=45)
    if not text:
        text = _fallback_follow_up(row.answer_text)

    row.follow_up_text = text
    db.commit()
    return {"follow_up_text": text, "follow_up_used": True}


def finish(current: user, session_id: int, status: int, db: Session) -> dict:
    if status not in (2, 4):
        raise api_error(10001, "status 仅支持 2（正常结束）或 4（提前结束）", 400)

    session = _load_own(current.id, session_id, db)
    if session.status != 1:
        raise api_error(50002, "面试已结束", 409)

    questions = interview_repo.list_questions(db, session_id)
    total = sum((row.score or Decimal("0")) for row in questions)
    average = (total / Decimal(len(questions) or 1)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )

    ended = utcnow()
    session.status = status
    session.ended_at = ended
    session.total_score = average
    session.duration_seconds = max(0, int((ended - session.started_at).total_seconds()))
    db.commit()

    pass_score = settings_cache.interview_pass_score
    passed = float(average) >= pass_score
    answered = sum(1 for row in questions if (row.answer_text or "").strip())

    return {
        "id": str(session.id),
        "status": status,
        "total_score": float(average),
        "duration_seconds": session.duration_seconds,
        "passed": passed,
        "pass_score": pass_score,
        "answered_count": answered,
        "question_count": len(questions),
        "summary": _verdict(passed, float(average), pass_score, answered, len(questions)),
    }


def _verdict(
    passed: bool, score: float, pass_score: int, answered: int, total: int
) -> str:
    """给学员一句人话结论，前端直接展示。"""
    if passed:
        return f"恭喜通过本轮面试（{score:.0f} 分 ≥ {pass_score} 分）"
    if answered == 0:
        return "本场未作答，未通过"
    gap = pass_score - score
    return f"未通过，差 {gap:.0f} 分；建议回顾本场点评后再练一次"


def create_ws_ticket(current: user, session_id: int, db: Session) -> dict:
    session = _load_own(current.id, session_id, db)
    if session.status != 1:
        raise api_error(50002, "面试已结束", 409)

    ticket = secrets.token_urlsafe(24)
    cache.save_ws_ticket(ticket, session.id, 60)
    return {"ticket": ticket, "expires_in": 60}


def load_audio(current: user, session_id: int, question_index: int, db: Session) -> bytes:
    """读取某题的预生成语音；未生成时抛 404，由前端降级为纯文字。"""
    _load_own(current.id, session_id, db)
    data = audio_service.load(session_id, question_index)
    if not data:
        raise not_found("该题语音尚未生成")
    return data


def report(current: user, session_id: int, db: Session) -> dict:
    """面试报告：逐题分数、回答、追问与点评，供报告页展示。

    与 detail 的区别：detail 面向「进行中」的答题界面（含剩余时间、当前题号），
    report 面向「已结束」的复盘，不允许查询进行中的会话。
    """
    session = _load_own(current.id, session_id, db)
    if session.status == 1:
        raise api_error(50002, "面试尚未结束", 409)

    questions = interview_repo.list_questions(db, session_id)
    pass_score = settings_cache.interview_pass_score
    total = float(session.total_score) if session.total_score is not None else 0.0

    items = []
    for row in questions:
        items.append(
            {
                "question_index": row.question_index,
                "question_text": row.question_text,
                "answer_mode": row.answer_mode,
                "score": float(row.score) if row.score is not None else None,
                "source_type": row.source_type,
                "source_doc_name": row.source_doc_name or "",
                "answer_text": row.answer_text or "",
                "follow_up_text": row.follow_up_text or "",
                "follow_up_answer": row.follow_up_answer or "",
                "ai_comment": row.ai_comment or "",
            }
        )

    return {
        "id": str(session.id),
        "source": session.source,
        "subject_name": interview_repo.subject_name(db, session.subject_id)
        or ("简历面试" if session.source == 2 else ""),
        "total_score": total,
        "pass_score": pass_score,
        "passed": total >= pass_score,
        "question_count": session.question_count,
        "answered_count": sum(1 for row in questions if (row.answer_text or "").strip()),
        "started_at": _iso(session.started_at),
        "ended_at": _iso(session.ended_at) if session.ended_at else None,
        "duration_seconds": session.duration_seconds,
        "summary": _verdict(
            total >= pass_score,
            total,
            pass_score,
            sum(1 for row in questions if (row.answer_text or "").strip()),
            len(questions),
        ),
        "items": items,
    }


MIN_ASR_BYTES = 8 * 1024  # 约 0.25 秒，太短不调腾讯云（每次识别都计费）
MAX_ASR_BYTES = 3 * 1024 * 1024


def transcribe(current: user, session_id: int, audio: bytes, db: Session) -> dict:
    """语音作答转写：只负责出文字，评分仍走 answer()。"""
    session = _load_own(current.id, session_id, db)
    _ensure_open(session)

    if len(audio) > MAX_ASR_BYTES:
        raise api_error(10003, "单段音频过长，请分段作答", 400)

    if len(audio) < MIN_ASR_BYTES:
        # 太短（咳嗽、误触）直接返回空文本，不消耗识别额度
        logger.info("语音过短跳过识别 session=%s %s 字节", session_id, len(audio))
        return {"text": "", "bytes": len(audio)}

    text = asr.recognize(audio)
    if text is None:
        raise api_error(10008, "语音识别失败，请重试或改用文字作答", 503)

    return {"text": text, "bytes": len(audio)}


def verdict_audio(current: user, session_id: int, db: Session) -> bytes:
    """读取本场面试的结语语音；未生成时 404，前端降级为不播。"""
    _load_own(current.id, session_id, db)
    data = audio_service.load_verdict(session_id)
    if not data:
        raise not_found("结语语音尚未生成")
    return data


def list_sessions(
    current: user, source: int | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    rows, total = interview_repo.paginate_sessions(
        db, current.id, source, (page - 1) * page_size, page_size
    )
    items = [
        {
            "id": str(row[0].id),
            "source": row[0].source,
            "subject_name": row[1],
            "total_score": float(row[0].total_score)
            if row[0].total_score is not None
            else None,
            "question_count": row[0].question_count,
            "started_at": _iso(row[0].started_at),
            "status": row[0].status,
        }
        for row in rows
    ]
    return items, total
