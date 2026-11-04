"""PDF 文字提取（本地 PyMuPDF）。

为什么不用 MinerU：
  简历通常是文字型 PDF，本地提取是毫秒级、零成本、不依赖外网；
  MinerU 是异步任务（提交 → 轮询 → 下载压缩包），链路长、要排队，
  简历场景的收益抵不上复杂度。配置项保留，将来遇到扫描件或复杂排版可切换。

扫描件兜底：提取到的字符过少直接判失败并提示上传文字版，
不把一堆乱码送去切分和向量化（那样出的面试题会完全跑偏）。
"""

import logging

import pymupdf

logger = logging.getLogger("yunshu.pdf")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

MIN_CHARS = 100  # 低于这个字数基本是扫描件或空文件


class PdfParseError(Exception):
    """PDF 无法解析（损坏、加密、扫描件）。"""


def extract_text(pdf_bytes: bytes) -> str:
    """提取 PDF 全文；失败抛 PdfParseError。"""
    if not pdf_bytes:
        raise PdfParseError("文件为空")

    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PdfParseError(f"PDF 无法打开：{type(exc).__name__}") from exc

    try:
        if document.is_encrypted and not document.authenticate(""):
            raise PdfParseError("PDF 已加密，请先解除密码")

        pages = [page.get_text("text") for page in document]
        text = "\n".join(pages).strip()
    finally:
        document.close()

    if len(text) < MIN_CHARS:
        logger.warning("PDF 提取文字过少：%s 字", len(text))
        raise PdfParseError("未提取到有效文字，可能是扫描件或图片版，请上传文字版 PDF")

    logger.info("PDF 提取完成：%s 页 / %s 字", len(pages), len(text))
    return text
