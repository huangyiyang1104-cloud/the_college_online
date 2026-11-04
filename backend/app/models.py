"""ORM 模型：与 scripts/sql/schema.sql 一一对应，不做结构改动。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import base

# 软删除的“未删除”哨兵值，与建表脚本保持一致
NOT_DELETED = datetime(1970, 1, 1, 0, 0, 0)


class admin_user(base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[int] = mapped_column(SmallInteger, default=2)  # 1 超管 2 运营
    is_builtin: Mapped[int] = mapped_column(SmallInteger, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class user(base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    city: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class user_login_log(base):
    __tablename__ = "user_login_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class learning_visit(base):
    __tablename__ = "learning_visit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    course_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visited_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class course_completion(base):
    __tablename__ = "course_completion"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    course_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class exam_paper(base):
    __tablename__ = "exam_paper"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    obtained_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    # 1 判分中（仅同步判分超时降级），2 已完成
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class exam_answer(base):
    __tablename__ = "exam_answer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_title: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_max: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_obtained: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_correct: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    judged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class exam_answer_option(base):
    __tablename__ = "exam_answer_option"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    answer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    option_key: Mapped[str] = mapped_column(String(1), nullable=False)
    option_content: Mapped[str] = mapped_column(String(512), nullable=False)
    is_correct: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class wrong_question(base):
    __tablename__ = "wrong_question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wrong_times: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class subject(base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=NOT_DELETED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class subject_keyword(base):
    __tablename__ = "subject_keyword"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    keyword: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class course(base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    bilibili_url: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=NOT_DELETED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class question(base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=2)
    category: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), default=10)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=NOT_DELETED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class question_option(base):
    __tablename__ = "question_option"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    option_key: Mapped[str] = mapped_column(String(1), nullable=False)
    content: Mapped[str] = mapped_column(String(512), nullable=False)
    is_correct: Mapped[int] = mapped_column(SmallInteger, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class question_tag(base):
    __tablename__ = "question_tag"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tag_name: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class interview_doc(base):
    __tablename__ = "interview_doc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 pdf 2 md
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    oss_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 待处理 2 转md中 3 已入库 4 失败
    failure_reason: Mapped[str] = mapped_column(String(512), default="")
    uploaded_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=NOT_DELETED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class resume(base):
    __tablename__ = "resume"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    oss_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # 1 待处理 2 解析中 3 就绪（可发起简历面试） 4 失败
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    failure_reason: Mapped[str] = mapped_column(String(512), default="")
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=NOT_DELETED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class interview_session(base):
    __tablename__ = "interview_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 学科 2 简历
    subject_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    resume_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    question_count: Mapped[int] = mapped_column(SmallInteger, default=5)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 进行中 2 正常结束 3 超时 4 提前结束
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class interview_question(base):
    __tablename__ = "interview_question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 资料库 2 简历
    source_doc_name: Mapped[str] = mapped_column(String(255), default="")
    source_snippet_id: Mapped[str] = mapped_column(String(64), default="")
    answer_mode: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class admin_operation_log(base):
    __tablename__ = "admin_operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_name: Mapped[str] = mapped_column(String(255), default="")
    detail_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
