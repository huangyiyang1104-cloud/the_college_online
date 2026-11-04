"""探测 DashScope Embedding 接口：确认可用模型名与真实向量维度。

背景：.env 里的 EMBEDDING_MODEL 是占位值，维度必须与 Milvus 集合一致，
所以先实测再定，避免建完集合才发现维度不匹配。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\probe_embedding.py
"""

import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache as settings

# 先试配置值，再试常见候选（text-embedding-v3/v4 是 DashScope 一直在用的）
CANDIDATES = [
    settings.embedding_model,
    "text-embedding-v4",
    "text-embedding-v3",
    "text-embedding-v2",
    "text-embedding-v1",
]


def post_json(url: str, payload: dict, api_key: str, timeout: int = 30):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        return exc.code, raw[:400]
    except Exception as exc:
        return -1, f"{type(exc).__name__}: {exc}"


def main() -> int:
    base = settings.embedding_base_url.rstrip("/")
    url = f"{base}/embeddings"
    api_key = settings.dashscope_api_key

    print("=== Embedding 探测 ===")
    print(f"接口 : {url}")
    print(f"密钥 : {'已配置 ' + api_key[:6] + '…' if api_key else '空'}")
    print(f"配置模型 : {settings.embedding_model}（配置维度 {settings.embedding_dim}）\n")

    if not api_key:
        print("失败：DASHSCOPE_API_KEY 为空")
        return 1

    seen = set()
    ok_model = ""
    ok_dim = 0

    for model in CANDIDATES:
        if model in seen:
            continue
        seen.add(model)

        status, body = post_json(
            url, {"model": model, "input": ["云枢智学 embedding 连通性测试"]}, api_key
        )

        if status == 200 and isinstance(body, dict):
            vector = body["data"][0]["embedding"]
            ok_model, ok_dim = model, len(vector)
            print(f"OK   {model:<24} 维度 {ok_dim}  前3值 {[round(v, 4) for v in vector[:3]]}")
            break

        detail = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)[:200]
        print(f"FAIL {model:<24} HTTP {status}  {detail}")

    if not ok_model:
        print("\n没有可用模型，请到阿里云百炼控制台确认已开通的 embedding 模型")
        return 1

    print("\n=== 结论 ===")
    print(f"可用模型 : {ok_model}")
    print(f"真实维度 : {ok_dim}")
    if ok_dim != settings.embedding_dim:
        print(
            f"注意：与配置的 EMBEDDING_DIM={settings.embedding_dim} 不一致，"
            f"需要改成 {ok_dim}，否则 Milvus 集合维度会不匹配"
        )
    else:
        print("与配置维度一致，可直接建集合")

    # 验证 dimensions 参数是否被支持（text-embedding-v3/v4 可指定输出维度）
    status, body = post_json(
        url,
        {"model": ok_model, "input": ["维度参数测试"], "dimensions": 1024},
        api_key,
    )
    if status == 200 and isinstance(body, dict):
        dim = len(body["data"][0]["embedding"])
        print(f"dimensions=1024 生效，返回 {dim} 维")
    else:
        print("dimensions 参数不被支持（会忽略），只能使用模型默认维度")

    return 0


if __name__ == "__main__":
    sys.exit(main())
