"""把 CodeBuddy 导出的会话 JSON 提炼成 Markdown 纪要。

用法：
    python scripts/parse_conversation.py <导出的.json> [--out 输出路径] [--dry-run]

做三件事：
  1. 解开 messages[].message 里被二次转义的 JSON；
  2. 只保留真实对话（user 的 <user_query>、assistant 的正文），丢掉系统提示、记忆、工具调用；
  3. 按 message id 去重（导出文件里 requests 是逐次请求的快照，重复很多）。
"""

import argparse
import json
import re
from pathlib import Path

USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.S)
# 用户消息里这些区块是上下文注入，不是人说的话
NOISE_BLOCK_RE = re.compile(
    r"<(user_info|rules|additional_data|artifact_directory_path|manually_attached_skills)>.*?</\1>",
    re.S,
)


def load_export(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_inner(raw) -> dict:
    """外层 message 字段是一段转义 JSON，解开得到 {role, content:[...]}。"""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def extract_text(inner: dict) -> str:
    blocks = inner.get("content") or []
    texts = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block.get("text") or "")
    return "\n".join(texts).strip()


def clean_user_text(text: str) -> str:
    match = USER_QUERY_RE.search(text)
    target = match.group(1) if match else text
    return NOISE_BLOCK_RE.sub("", target).strip()


def collect_turns(export: dict) -> tuple[list[dict], dict]:
    conversations = export.get("data", {}).get("conversations", [])
    seen: set[str] = set()
    turns: list[dict] = []
    stats = {"conversations": len(conversations), "requests": 0, "raw_messages": 0, "kept": 0}

    for conv in conversations:
        for request in conv.get("requests", []):
            stats["requests"] += 1
            for message in request.get("messages", []):
                stats["raw_messages"] += 1
                message_id = message.get("id") or ""
                if message_id and message_id in seen:
                    continue
                if message_id:
                    seen.add(message_id)

                inner = parse_inner(message.get("message"))
                role = inner.get("role") or message.get("role") or ""
                text = extract_text(inner)
                if not text:
                    continue
                if role == "user":
                    text = clean_user_text(text)

                # 系统注入的上下文包装，不是真实对话
                if not text or text.startswith("<previous_assistant_message>"):
                    continue
                turns.append({"role": role, "text": text, "at": message.get("createdAt", "")})
                stats["kept"] += 1

    return turns, stats


def render_index(turns: list[dict], title: str, width: int = 90) -> str:
    """只输出 user 轮次的骨架，用来快速定位"哪一轮聊了什么"。"""
    lines = [f"# {title} · 对话索引", "", f"> 共 {len(turns)} 条消息，下列为提问轮次（编号即全文纪要中的序号）。", ""]
    for index, turn in enumerate(turns, start=1):
        if turn["role"] != "user":
            continue
        snippet = " ".join(turn["text"].split())[:width]
        lines.append(f"- **{index}.** {snippet}")
    return "\n".join(lines) + "\n"


def render(turns: list[dict], title: str) -> str:
    lines = [f"# {title}", "", "> 由 CodeBuddy 导出的会话 JSON 自动提炼，已去除系统提示与工具调用。", ""]
    for index, turn in enumerate(turns, start=1):
        who = "我" if turn["role"] == "user" else "助手"
        lines.append(f"## {index}. {who}")
        lines.append("")
        lines.append(turn["text"].strip())
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="导出的会话 JSON 路径")
    parser.add_argument("--out", help="输出 Markdown 路径")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写文件")
    parser.add_argument("--index", metavar="路径", help="另存一份提问索引（只含 user 轮次）")
    parser.add_argument("--head", type=int, default=6, help="预览前 N 轮")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"文件不存在：{source}")
        return 1

    export = load_export(source)
    turns, stats = collect_turns(export)
    total_chars = sum(len(turn["text"]) for turn in turns)
    users = [turn for turn in turns if turn["role"] == "user"]
    assistants = [turn for turn in turns if turn["role"] == "assistant"]

    print(f"会话数：{stats['conversations']}，请求快照：{stats['requests']}，原始消息：{stats['raw_messages']}")
    print(f"去重后保留：{stats['kept']} 条（user {len(users)} / assistant {len(assistants)}）")
    print(f"总字数：{total_chars}，其中用户输入 {sum(len(t['text']) for t in users)}")
    if turns:
        longest = max(turns, key=lambda item: len(item["text"]))
        print(f"最长一条：{len(longest['text'])} 字（{longest['role']}）")

    print("\n---- 预览 ----")
    for index, turn in enumerate(turns[: args.head], start=1):
        snippet = turn["text"].replace("\n", " ")[:120]
        print(f"{index}. [{turn['role']}] {snippet}")

    if args.dry_run:
        print("\n（dry-run，未写文件）")
        return 0

    out = Path(args.out) if args.out else source.with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    title = source.stem
    out.write_text(render(turns, title), encoding="utf-8")
    print(f"\n已写出：{out}（{len(turns)} 条，{total_chars} 字）")

    if args.index:
        index_path = Path(args.index)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_text = render_index(turns, title)
        index_path.write_text(index_text, encoding="utf-8")
        print(f"已写出索引：{index_path}（{index_text.count(chr(10) + '- **')} 个提问轮次）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
