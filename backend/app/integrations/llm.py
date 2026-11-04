"""大模型调用（DeepSeek，OpenAI 兼容），当前仅用于简答题判分。

设计要点：
  - 用标准库发请求，不引入额外 HTTP 依赖；
  - 任何失败（超时、鉴权、返回格式不对）都返回 None，由业务层降级为关键词打分，
    不让一次模型故障毁掉整份答卷。
"""

import json
import logging
import random
import re
import urllib.error
import urllib.request
from decimal import Decimal

from app.core.config import settings_cache

logger = logging.getLogger("yunshu.llm")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

SYSTEM_PROMPT = (
    "你是严谨的阅卷老师。请按参考答案给学员的简答题打分。\n"
    "只输出 JSON，不要任何解释或代码块标记，格式：{\"score\": 0-100 的整数, \"comment\": \"不超过 80 字的点评\"}\n"
    "评分标准：完全覆盖要点 90-100；主要要点覆盖 70-89；部分覆盖 40-69；答非所问或空白 0-39。"
)

# 关键词兜底：中文按标点与空白切分，去掉过短的词
_SPLIT_PATTERN = re.compile(r"[，。；：、,.;:\s（）()\[\]【】\"'“”]+")


def _extract_json(text: str) -> dict | None:
    """模型可能返回 ```json 包裹或前后有废话，抓第一个 JSON 对象。"""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    tag: str = "llm",
) -> str | None:
    """统一的大模型调用；任何失败都返回 None，由业务层决定降级方式。"""
    if not settings_cache.deepseek_api_key or timeout <= 2:
        return None

    payload = json.dumps(
        {
            "model": settings_cache.deepseek_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{settings_cache.deepseek_base_url.rstrip('/')}/chat/completions",
        data=payload,
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {settings_cache.deepseek_api_key}")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        # 常见：模型名不存在（400）、密钥无效（401）、余额不足（402）
        detail = exc.read().decode("utf-8", "ignore")[:300]
        logger.warning("%s 调用失败：HTTP %s %s", tag, exc.code, detail)
        return None
    except Exception as exc:
        logger.warning("%s 调用异常：%s", tag, type(exc).__name__)
        return None


def score_short_answer(
    title: str, reference: str, answer: str, timeout: float
) -> tuple[Decimal, str] | None:
    """调用大模型判分，返回 (按满分折算的得分, 点评)；失败返回 None。"""
    user_prompt = (
        f"题目：{title}\n"
        f"参考答案：{reference}\n"
        f"学员作答：{answer or '（未作答）'}"
    )
    content = _chat(SYSTEM_PROMPT, user_prompt, 0.2, 300, timeout, tag="简答判分")
    if not content:
        return None

    data = _extract_json(content)
    if not data or "score" not in data:
        logger.warning("简答判分返回无法解析：%s", str(content)[:120])
        return None

    try:
        percent = max(0, min(100, int(float(data["score"]))))
    except (TypeError, ValueError):
        return None

    comment = str(data.get("comment", "")).strip()[:200]
    return Decimal(percent) / Decimal(100), comment


QUESTION_SYSTEM_PROMPT = (
    "你是资深技术面试官，正在根据资料片段准备面试题。\n"
    "只依据给定片段出题，不得编造片段中没有的内容。\n"
    "只输出 JSON，不要解释或代码块标记，格式："
    '{"questions":[{"question":"题目文本","snippet_index":0}]}\n'
    "要求：每题一句话、适合口头作答、覆盖不同主题、难度递进；"
    "不要在题目里出现“根据片段”“如资料所述”这类措辞。"
)

RESUME_QUESTION_SYSTEM_PROMPT = (
    "你是技术面试官，正在根据候选人的简历准备面试题。\n"
    "只依据给出的简历内容提问，不要编造简历里没有的项目或公司。\n"
    "优先围绕项目经历：他负责哪部分、为什么这样选型、遇到什么难点、结果如何量化。\n"
    "只输出 JSON，不要解释或代码块标记，格式："
    '{"questions":[{"question":"题目文本","snippet_index":0}]}\n'
    "要求：每题一句话、适合口头作答、覆盖不同项目、难度递进；"
    "题目里不要出现“简历中”“根据简历”这类措辞，直接像正常面试那样问。"
)

FOLLOW_UP_SYSTEM_PROMPT = (
    "你是技术面试官。针对学员的回答提一个更深入的追问，一句话，不要重复原题。\n"
    "只输出追问本身，不要任何前缀、编号或解释。"
)


def _generate_questions_with(
    system_prompt: str,
    snippets: list[dict],
    count: int,
    timeout: float,
    tag: str,
) -> list[dict] | None:
    """出题公共流程：拼素材 → 调模型 → 解析 JSON → 归一化。"""
    if not snippets:
        return None

    material = "\n\n".join(
        f"[{index}] {item.get('title', '')}\n{str(item.get('content', ''))[:600]}"
        for index, item in enumerate(snippets)
    )
    user_prompt = f"资料片段：\n{material}\n\n请出 {count} 道面试题。"

    content = _chat(system_prompt, user_prompt, 0.7, 1500, timeout, tag=tag)
    if not content:
        return None

    data = _extract_json(content)
    if not data:
        logger.warning("%s 返回无法解析：%s", tag, content[:120])
        return None

    questions = []
    for item in data.get("questions") or []:
        if not isinstance(item, dict) or not str(item.get("question", "")).strip():
            continue
        try:
            snippet_index = int(item.get("snippet_index", 0))
        except (TypeError, ValueError):
            snippet_index = 0
        questions.append(
            {
                "question": str(item["question"]).strip()[:500],
                "snippet_index": max(0, min(snippet_index, len(snippets) - 1)),
            }
        )
    return questions or None


def generate_questions(
    snippets: list[dict], count: int = 5, timeout: float = 90
) -> list[dict] | None:
    """学科面试出题：从资料库切片里出技术题。"""
    return _generate_questions_with(
        QUESTION_SYSTEM_PROMPT, snippets, count, timeout, "面试出题"
    )


def generate_resume_questions(
    snippets: list[dict], count: int = 5, timeout: float = 90
) -> list[dict] | None:
    """简历面试出题：围绕候选人自己的项目经历追问。"""
    return _generate_questions_with(
        RESUME_QUESTION_SYSTEM_PROMPT, snippets, count, timeout, "简历出题"
    )


def generate_follow_up(question: str, answer: str, timeout: float = 30) -> str | None:
    """针对作答生成一次追问；失败返回 None。"""
    user_prompt = f"原题：{question}\n学员回答：{answer or '（未作答）'}"
    content = _chat(FOLLOW_UP_SYSTEM_PROMPT, user_prompt, 0.8, 160, timeout, tag="面试追问")
    if not content:
        return None
    text = content.strip().strip('"').strip("“”").strip()
    return text[:300] or None


VERDICT_FAIL_PROMPT = (
    "你是刚结束面试的面试官，现在要收尾。请直接说出你的最后一句话。\n"
    "语气礼貌但公事公办，就像真实面试结束时那样。\n"
    "示例：今天先到这里，回去等通知吧。 / 好的，我们综合评估后再联系你。 / 感谢你的时间，有结果会通知你。\n"
    "要求：20 字以内，只输出这句话，不要引号、不要解释、不要提分数。"
)

VERDICT_PASS_PROMPT = (
    "你是面试官，已经决定录用这位候选人。请用一句话询问入职时间或期望薪资，语气自然。\n"
    "25 字以内，只输出这句话本身，不要引号、不要换行。"
)

# 模型不可用时的兜底台词，保证结语语音不会整体失效
FAIL_VERDICT_LINES = [
    "今天先到这里，回去等通知吧。",
    "好的，我们这边再综合评估一下，你先回去等消息。",
    "行，今天就到这儿，有结果我们会联系你。",
    "感谢你的时间，后续通知会发给你。",
    "先这样，回去等通知。",
]

PASS_VERDICT_LINES = [
    "你什么时候能入职？期望薪资大概多少？",
    "如果录用你，最快什么时候到岗？薪资有什么要求？",
    "这边基本没什么问题了，你期望的薪资是多少？",
    "什么时候可以入职？薪资方面你是怎么考虑的？",
    "我们对你还比较满意，聊聊入职时间和待遇吧。",
]


def generate_verdict_line(passed: bool, score: float, timeout: float = 20) -> str:
    """生成面试结语台词。

    通过 → 面试官追问入职/薪资；未通过 → 公事公办的收尾话。
    模型失败时从候选池随机取一句，保证一定有话说。
    """
    system_prompt = VERDICT_PASS_PROMPT if passed else VERDICT_FAIL_PROMPT
    user_prompt = (
        f"本场面试总分 {score:.0f} 分（百分制），判定为"
        f"{'通过' if passed else '未通过'}。请给出你作为面试官的最后一句话。"
    )

    # temperature 拉高：同一结果每次也要说出不同的收尾语
    content = _chat(system_prompt, user_prompt, 1.0, 160, timeout, tag="面试结语")

    text = ""
    if content:
        text = content.strip().strip('"').strip("“”").replace("\n", "").strip()[:60]
        if not text:
            logger.info("面试结语模型返回空内容：%r", content[:120])

    if not text:
        text = random.choice(PASS_VERDICT_LINES if passed else FAIL_VERDICT_LINES)
        logger.info("面试结语回落候选池：%s", text)

    return text


def fallback_score(reference: str, answer: str) -> tuple[Decimal, str]:
    """关键词重合度兜底打分，返回 (0-1 的比例, 点评)。"""
    key_points = [item for item in _SPLIT_PATTERN.split(reference or "") if len(item) >= 2]
    if not key_points:
        return Decimal(0), "参考答案缺失，按 0 分计"
    if not (answer or "").strip():
        return Decimal(0), "未作答"

    hit = sum(1 for point in key_points if point in answer)
    ratio = Decimal(hit) / Decimal(len(key_points))
    return ratio, f"命中 {hit}/{len(key_points)} 个参考要点（模型判分不可用，按关键词估算）"
