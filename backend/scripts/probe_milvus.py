"""Milvus 连通性 + 读写测试（用真实 embedding，写入后检索再清理）。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\probe_milvus.py
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache as settings
from app.integrations import vector_store
from app.integrations.embedding import embed_texts

TEST_DOC_ID = 999999
SAMPLES = [
    ("Redis 持久化", "Redis 提供 RDB 与 AOF 两种持久化方式：RDB 是快照，恢复快但可能丢数据；AOF 记录写命令，更安全但文件更大。"),
    ("Kubernetes 基础", "Kubernetes 中最小的调度单元是 Pod，一个 Pod 可包含一个或多个容器，共享网络与存储。"),
    ("MySQL 索引", "MySQL 的 InnoDB 使用 B+ 树索引，主键索引即聚簇索引，二级索引需要回表查询。"),
]


def main() -> int:
    name = settings.milvus_collection_docs
    print("=== Milvus 读写测试 ===")
    print(f"地址 : {settings.milvus_host}:{settings.milvus_port}")
    print(f"集合 : {name}\n")

    try:
        collection = vector_store.ensure_collection(name)
        print(f"OK   集合就绪，当前实体数 {collection.num_entities}")
    except Exception as exc:
        print(f"FAIL 建集合失败：{type(exc).__name__} {exc}")
        return 1

    texts = [item[1] for item in SAMPLES]
    vectors = embed_texts(texts)
    print(f"OK   向量化完成：{len(vectors)} 条，维度 {len(vectors[0])}")

    chunks = [
        {"index": index, "title": title, "content": content}
        for index, (title, content) in enumerate(SAMPLES)
    ]
    count = vector_store.replace_doc_chunks(name, TEST_DOC_ID, chunks, vectors)
    print(f"OK   写入 {count} 条切片（doc_id={TEST_DOC_ID}）")

    query_vector = embed_texts(["Redis 怎么保证数据不丢"])[0]
    hits = vector_store.search(name, query_vector, top_k=3)
    print("\n检索「Redis 怎么保证数据不丢」：")
    for hit in hits:
        print(f"  {hit['score']:.4f}  [{hit['title']}] {hit['content'][:36]}…")

    top_title = hits[0]["title"] if hits else ""
    print(f"\n命中预期（Redis 持久化）：{'是' if top_title == 'Redis 持久化' else '否 → ' + top_title}")

    vector_store.delete_doc(name, TEST_DOC_ID)
    print(f"清理：已删除 doc_id={TEST_DOC_ID} 的测试切片")
    print(f"集合实体数：{vector_store.collection_stats(name)['entities']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
