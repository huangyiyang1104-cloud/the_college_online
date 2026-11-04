"""Excel 导入解析：只做「字节 → 行数据 → 校验结果」。

不涉及数据库、Redis 与 HTTP，便于单独测试；失败一律抛 api_error。
"""

from io import BytesIO

from openpyxl import load_workbook

from app.core.errors import api_error

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ERRORS = 200
MAX_PREVIEW = 20

TYPE_MAP = {
    "判断": 1, "判断题": 1,
    "单选": 2, "单选题": 2,
    "多选": 3, "多选题": 3,
    "简答": 4, "简答题": 4,
}
# 难度列：简单=1，中等=2，困难=3；留空默认中等
DIFFICULTY_MAP = {
    "简单": 1, "基础": 1, "容易": 1,
    "中等": 2, "一般": 2, "普通": 2,
    "困难": 3, "难": 3, "高级": 3,
}
COURSE_HEADERS = ("课程名称", "时长（分钟）", "播放链接")
QUESTION_HEADERS = ("题干", "题型", "正确答案")
OPTION_LETTERS = "ABCDEF"


def read_rows(filename: str | None, content: bytes) -> list[tuple[int, dict[str, str]]]:
    """读取 xlsx，返回 [(行号, {表头: 值})]，首行为表头。"""
    if not filename or not filename.lower().endswith((".xlsx", ".xls")):
        raise api_error(60001, "仅支持 xlsx / xls 文件", 400)
    if len(content) > MAX_FILE_SIZE:
        raise api_error(60002, "文件超过 10 MB 限制", 413)

    try:
        book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception:
        raise api_error(60003, "文件解析失败，请确认是有效的 Excel 文件", 422)

    rows = book.active.iter_rows(values_only=True)
    try:
        header = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
    except StopIteration:
        raise api_error(60003, "文件内容为空", 422)

    result: list[tuple[int, dict[str, str]]] = []
    for index, row in enumerate(rows, start=2):
        if row is None or all(cell in (None, "") for cell in row):
            continue
        record = {}
        for position, name in enumerate(header):
            if not name:
                continue
            value = row[position] if position < len(row) else None
            record[name] = str(value).strip() if value is not None else ""
        result.append((index, record))
    return result


def parse_course_rows(
    rows: list[tuple[int, dict[str, str]]]
) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    errors: list[dict] = []
    for line, record in rows:
        title = record.get("课程名称", "").strip()
        url = record.get("播放链接", "").strip()
        duration_raw = record.get("时长（分钟）", "") or record.get("时长", "")

        if not title:
            errors.append({"row": line, "field": "课程名称", "reason": "课程名称不能为空"})
            continue
        if not url.startswith("https://www.bilibili.com/"):
            errors.append({"row": line, "field": "播放链接", "reason": "播放链接为空或不是 B 站链接"})
            continue
        try:
            duration = int(float(duration_raw)) if duration_raw else 0
        except ValueError:
            errors.append({"row": line, "field": "时长", "reason": "时长必须是数字"})
            continue

        valid.append(
            {"row": line, "title": title, "duration_minutes": duration, "bilibili_url": url}
        )
    return valid, errors


def parse_question_rows(
    rows: list[tuple[int, dict[str, str]]]
) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    errors: list[dict] = []
    for line, record in rows:
        title = record.get("题干", "").strip()
        type_raw = record.get("题型", "").strip()
        answer_raw = record.get("正确答案", "").strip()

        if not title:
            errors.append({"row": line, "field": "题干", "reason": "题干不能为空"})
            continue
        q_type = TYPE_MAP.get(type_raw)
        if not q_type:
            errors.append({"row": line, "field": "题型", "reason": f"未知题型：{type_raw}"})
            continue
        if not answer_raw:
            errors.append({"row": line, "field": "正确答案", "reason": "正确答案不能为空"})
            continue

        options = []
        if q_type != 4:
            for letter in OPTION_LETTERS:
                content = record.get(f"选项{letter}", "").strip()
                if not content:
                    continue
                options.append(
                    {
                        "option_key": letter,
                        "content": content,
                        "is_correct": 1 if letter in answer_raw.upper() else 0,
                    }
                )
            if not options:
                errors.append({"row": line, "field": "选项", "reason": "客观题缺少选项"})
                continue

        tags = [
            item.strip()
            for item in record.get("标签", "").replace("，", ",").split(",")
            if item.strip()
        ]
        valid.append(
            {
                "row": line,
                "title": title,
                "type": q_type,
                "difficulty": DIFFICULTY_MAP.get(record.get("难度", "").strip(), 2),
                "category": record.get("分类", "").strip()[:64],
                "answer": answer_raw,
                "analysis": record.get("解析", "").strip(),
                "options": options,
                "tags": tags[:10],
            }
        )
    return valid, errors
