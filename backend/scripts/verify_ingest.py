"""验证面试资料入库链路：重试处理 → 轮询状态 → 向量检索。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\verify_ingest.py [doc_id]
"""

import json
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"
STATUS_TEXT = {1: "待处理", 2: "处理中", 3: "已入库", 4: "解析失败"}


def call(method: str, path: str, body: dict | None = None, token: str = ""):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else None)


def main() -> int:
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    if status != 200:
        print(f"登录失败：{status} {payload}")
        return 1
    token = payload["data"]["access_token"]

    status, payload = call("GET", "/admin/interview-docs?page=1&page_size=10", token=token)
    docs = payload["data"]["list"]
    if not docs:
        print("资料库是空的，先在管理端上传一份 PDF/MD")
        return 1

    for item in docs:
        print(f"  文档 {item['id']}：{STATUS_TEXT.get(item['status'], item['status'])}  {item['file_name']}")

    target = doc_id or docs[0]["id"]

    print(f"\n触发重新处理 doc={target} …")
    status, payload = call("POST", f"/admin/interview-docs/{target}/processing-jobs", token=token)
    print(f"  {status} {payload.get('data') if status < 400 else payload}")

    final = None
    for tick in range(40):
        time.sleep(2)
        status, payload = call("GET", f"/admin/interview-docs/{target}", token=token)
        data = payload["data"]
        final = data["status"]
        reason = data.get("failure_reason") or ""
        print(f"  +{(tick + 1) * 2:>3}s  {STATUS_TEXT.get(final, final)}  {reason[:80]}")
        if final in (3, 4):
            break

    if final != 3:
        print("\nFAIL 入库未成功，看上面 failure_reason，或后端日志")
        return 1

    print("\n检索测试：")
    status, payload = call("GET", "/admin/retrieval-tests?query=Python&top_k=3", token=token)
    data = payload.get("data") or []
    if isinstance(data, dict):
        data = data.get("items") or data.get("list") or data
    print(f"  {status}，命中 {len(data) if hasattr(data, '__len__') else '?'} 条")
    for row in (data if isinstance(data, list) else [])[:3]:
        print(f"  - {str(row)[:160]}")

    return 0 if data else 1


if __name__ == "__main__":
    sys.exit(main())
