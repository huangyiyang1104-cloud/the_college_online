"""MinIO 对象存储适配：上传原始资料。

线上切阿里云 OSS 时按 STORAGE_BACKEND 换实现，业务层不感知。
"""

import uuid
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings_cache
from app.core.errors import api_error

INTERVIEW_PREFIX = "interview/"


def _client() -> Minio:
    # MinIO SDK 只接受 host:port，带 http:// 前缀会解析失败（容器部署时踩过）
    endpoint = (settings_cache.minio_endpoint or "").strip()
    for prefix in ("http://", "https://"):
        if endpoint.startswith(prefix):
            endpoint = endpoint[len(prefix) :]
            break
    endpoint = endpoint.rstrip("/")

    return Minio(
        endpoint,
        access_key=settings_cache.minio_access_key,
        secret_key=settings_cache.minio_secret_key,
        secure=settings_cache.minio_secure,
    )


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings_cache.minio_bucket):
        client.make_bucket(settings_cache.minio_bucket)


def download(object_key: str) -> bytes:
    """按 object key 取回原始文件；失败统一抛 10008。"""
    try:
        client = _client()
        response = client.get_object(settings_cache.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error:
        raise api_error(10008, "文件读取失败，请稍后重试", 503)


def upload(content: bytes, suffix: str, content_type: str | None = None) -> str:
    """上传字节流并返回 object key；失败统一抛 10008。"""
    object_key = f"{INTERVIEW_PREFIX}{uuid.uuid4().hex}{suffix}"
    return upload_at(object_key, content, content_type)


def upload_at(object_key: str, content: bytes, content_type: str | None = None) -> str:
    """按指定 key 上传（覆盖同名对象），用于可推导路径的音频等资源。"""
    try:
        client = _client()
        _ensure_bucket(client)
        client.put_object(
            settings_cache.minio_bucket,
            object_key,
            BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )
    except S3Error:
        raise api_error(10008, "对象存储不可用，请稍后重试", 503)
    return object_key


def exists(object_key: str) -> bool:
    try:
        _client().stat_object(settings_cache.minio_bucket, object_key)
        return True
    except Exception:
        return False
