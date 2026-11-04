"""请求/响应模型：字段名与 04.API接口设计.md 保持一致。"""

from pydantic import BaseModel, Field, field_validator


class login_request(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=32)


class refresh_request(BaseModel):
    refresh_token: str = Field(min_length=10)


# ---------- 学员端 ----------
# 注意：pydantic 的 pattern 走 Rust 正则，不支持 look-ahead，
# 密码复杂度改用 field_validator 校验
PHONE_PATTERN = r"^1\d{10}$"


class sms_code_request(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN, description="11 位手机号")
    scene: str = Field(default="register", pattern="^register$")


class student_register_request(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    code: str = Field(min_length=4, max_length=8)
    password: str = Field(min_length=6, max_length=32, description="6-32 位，至少含字母与数字")

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("密码需同时包含字母与数字")
        return value


class student_login_request(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    password: str = Field(min_length=6, max_length=32)


class profile_update(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=64)


class interview_create_request(BaseModel):
    source: int = Field(ge=1, le=2, description="1 学科面试，2 简历面试")
    subject_id: str | None = None
    resume_id: str | None = None


class interview_answer_request(BaseModel):
    answer_mode: int = Field(ge=1, le=2, description="1 语音，2 打字")
    answer_text: str = Field(min_length=1, max_length=5000)
    is_follow_up: bool = Field(default=False, description="是否为回答追问")


class interview_finish_request(BaseModel):
    status: int = Field(ge=1, le=4, description="2 正常结束，4 提前结束")


# ---------- C4 刷题 ----------
class paper_answer_item(BaseModel):
    question_id: str = Field(description="题目 id（字符串形式的 BIGINT）")
    option_keys: list[str] = Field(default_factory=list, description="客观题所选选项标识")
    answer_text: str | None = Field(default=None, max_length=5000, description="简答题作答正文")


class paper_submit(BaseModel):
    subject_id: str
    answers: list[paper_answer_item] = Field(min_length=1, max_length=100)


# ---------- C5 错题本 ----------
class wrong_attempt(BaseModel):
    option_keys: list[str] = Field(min_length=1, max_length=6, description="本次重做所选选项标识")


class option_item(BaseModel):
    option_key: str = Field(min_length=1, max_length=1)
    content: str = Field(min_length=1, max_length=512)
    is_correct: int = Field(default=0, ge=0, le=1)


class subject_create(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    icon: str = Field(default="", max_length=16)
    description: str = Field(default="", max_length=512)
    sort_order: int = Field(default=0, ge=0)
    keywords: list[str] = Field(default_factory=list)

    @field_validator("keywords")
    @classmethod
    def check_keywords(cls, value: list[str]) -> list[str]:
        if len(value) > 20:
            raise ValueError("关键词最多 20 个")
        for item in value:
            if not item.strip() or len(item) > 64:
                raise ValueError("关键词不能为空且不超过 64 字符")
        return [item.strip() for item in value]


class subject_update(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=16)
    description: str | None = Field(default=None, max_length=512)
    sort_order: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    keywords: list[str] | None = None

    @field_validator("keywords")
    @classmethod
    def check_keywords(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(value) > 20:
            raise ValueError("关键词最多 20 个")
        for item in value:
            if not item.strip() or len(item) > 64:
                raise ValueError("关键词不能为空且不超过 64 字符")
        return [item.strip() for item in value]


class course_create(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=512)
    duration_minutes: int = Field(ge=1, le=100000)
    bilibili_url: str = Field(min_length=10, max_length=512)
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("bilibili_url")
    @classmethod
    def check_url(cls, value: str) -> str:
        if not value.startswith("https://www.bilibili.com/"):
            raise ValueError("播放地址必须是以 https://www.bilibili.com/ 开头的完整链接")
        return value.strip()


class course_update(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    bilibili_url: str | None = Field(default=None, min_length=10, max_length=512)
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("bilibili_url")
    @classmethod
    def check_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("https://www.bilibili.com/"):
            raise ValueError("播放地址必须是以 https://www.bilibili.com/ 开头的完整链接")
        return value.strip()


class course_order_request(BaseModel):
    course_ids: list[int] = Field(default_factory=list)

    @field_validator("course_ids")
    @classmethod
    def check_ids(cls, value: list[int]) -> list[int]:
        if len(value) > 500:
            raise ValueError("单次最多调整 500 门课程")
        return value


class question_create(BaseModel):
    subject_id: int
    type: int = Field(ge=1, le=4)
    difficulty: int = Field(default=2, ge=1, le=3)
    category: str = Field(default="", max_length=64)
    title: str = Field(min_length=1, max_length=20000)
    score: float = Field(gt=0, le=100)
    options: list[option_item] = Field(default_factory=list)
    reference_answer: str | None = Field(default=None, max_length=20000)
    analysis: str | None = Field(default=None, max_length=20000)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def check_tags(cls, value: list[str]) -> list[str]:
        if len(value) > 10:
            raise ValueError("标签最多 10 个")
        for item in value:
            if not item.strip() or len(item) > 32:
                raise ValueError("标签不能为空且不超过 32 字符")
        return [item.strip() for item in value]


class question_update(BaseModel):
    subject_id: int | None = None
    difficulty: int | None = Field(default=None, ge=1, le=3)
    category: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=20000)
    score: float | None = Field(default=None, gt=0, le=100)
    options: list[option_item] | None = None
    reference_answer: str | None = Field(default=None, max_length=20000)
    analysis: str | None = Field(default=None, max_length=20000)
    tags: list[str] | None = None
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("tags")
    @classmethod
    def check_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(value) > 10:
            raise ValueError("标签最多 10 个")
        for item in value:
            if not item.strip() or len(item) > 32:
                raise ValueError("标签不能为空且不超过 32 字符")
        return [item.strip() for item in value]


class import_confirm(BaseModel):
    status: str = Field(pattern="^confirmed$")


class status_update(BaseModel):
    status: int = Field(ge=0, le=1)


class admin_user_create(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=32)
    role: int = Field(default=2, ge=1, le=2)


class admin_user_update(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=32)
    role: int | None = Field(default=None, ge=1, le=2)
    status: int | None = Field(default=None, ge=0, le=1)
