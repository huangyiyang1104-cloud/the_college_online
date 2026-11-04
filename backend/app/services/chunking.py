"""文本切分：Markdown 按标题分节，再按长度切块并保留少量重叠。

切分粒度决定检索质量：
  - 太小 → 语义不完整，模型拿不到上下文；
  - 太大 → 一条切片混多个主题，召回不准。
这里取 500 字/片、60 字重叠，并保留所属小节标题作为检索结果的来源提示。
"""

import re

MAX_CHARS = 500
OVERLAP = 60
MIN_CHARS = 30

HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.M)


def _sections(text: str):
    """按 Markdown 标题切节，产出 (标题, 正文)。"""
    matches = list(HEADING.finditer(text))
    if not matches:
        yield "", text
        return

    if matches[0].start() > 0:
        yield "", text[: matches[0].start()]

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield match.group(2).strip(), text[start:end]


def _split_body(body: str, max_chars: int, overlap: int):
    """把一节正文按段落拼接到 max_chars，超长段落硬切并保留重叠。"""
    body = body.strip()
    if not body:
        return

    if len(body) <= max_chars:
        yield body
        return

    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= max_chars:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
            continue

        if buffer:
            yield buffer

        # 单个段落就超过上限：按字符硬切，保留重叠避免语义断裂
        while len(paragraph) > max_chars:
            yield paragraph[:max_chars]
            paragraph = paragraph[max_chars - overlap :]
        buffer = paragraph

    if buffer:
        yield buffer


def split_markdown(
    text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP
) -> list[dict]:
    """返回 [{index, title, content}]，index 连续递增。"""
    chunks: list[dict] = []
    for title, body in _sections(text):
        for piece in _split_body(body, max_chars, overlap):
            content = piece.strip()
            if len(content) < MIN_CHARS:
                continue
            chunks.append({"index": len(chunks), "title": title[:200], "content": content})
    return chunks
