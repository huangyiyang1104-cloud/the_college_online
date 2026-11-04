"""简历链路自检：造 PDF → 上传 → 轮询解析 → 发起简历面试。

不依赖外部素材，脚本自己生成一份测试简历，可反复执行。
用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/check_resume.py
"""

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
PHONE = "19880836572"
PASSWORD = "Abc123456"

RESUME_TEXT = """张三
求职意向：Java 后端开发工程师
电话：138-0000-0000  邮箱：zhangsan@example.com

教育背景
2019.09 - 2023.06  某某大学  计算机科学与技术  本科

专业技能
熟悉 Java 并发编程与 JVM 调优，掌握 Spring Boot、MyBatis、Redis、Kafka。
熟悉 MySQL 索引优化与分库分表，了解 Docker 与 Kubernetes 基础运维。

项目经历
校园二手交易平台（2022.03 - 2022.09）
担任后端负责人，使用 Spring Boot + MyBatis + MySQL 实现商品、订单、支付三个模块。
用 Redis 缓存热门商品列表，接口平均响应从 320ms 降到 80ms。
订单模块用本地消息表加定时补偿保证最终一致性，上线后未出现漏单。

企业级权限管理系统（2022.10 - 2023.03）
负责权限模型设计与实现，采用 RBAC 三级模型，支持租户隔离。
使用 Spring Security 做鉴权，把权限点缓存到 Redis，QPS 提升约 3 倍。
解决了跨租户越权问题，通过拦截器统一注入租户上下文。

日志采集与监控平台（2023.04 - 2023.08）
基于 Kafka + Elasticsearch 搭建日志采集链路，日均处理 2000 万条日志。
自研限流组件，用令牌桶算法保护下游 ES，避免写入抖动导致查询超时。
用 Kibana 做可视化看板，把错误率告警接入企业微信，平均故障发现时间从 20 分钟降到 3 分钟。

实习经历
2022.07 - 2022.09  某某科技  后端开发实习生
参与订单中心重构，把单体服务拆成订单、库存、支付三个模块，接口超时率下降 60%。
编写单元测试覆盖核心链路，覆盖率从 35% 提升到 78%。

自我评价
习惯先想清楚边界条件再动手，遇到线上问题会先定位根因再修复，不喜欢用重试掩盖异常。
"""


def multipart(fields: dict, filename: str, content: bytes, content_type: str):
    boundary = "----yunshuBoundary7d3"
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode(
                "utf-8"
            )
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call(method: str, path: str, body: dict | None = None, token: str = "", raw: tuple | None = None):
    if raw is not None:
        payload, content_type = raw
    elif body is not None:
        payload, content_type = json.dumps(body).encode("utf-8"), "application/json"
    else:
        payload, content_type = None, None

    request = urllib.request.Request(BASE + path, data=payload, method=method)
    if content_type:
        request.add_header("Content-Type", content_type)
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
            return response.status, (json.loads(data) if data else None)
    except urllib.error.HTTPError as exc:
        data = exc.read()
        return exc.code, (json.loads(data) if data else None)


def build_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    rect = pymupdf.Rect(56, 56, 540, 780)
    page.insert_textbox(rect, RESUME_TEXT, fontsize=10.5, fontname="china-s", lineheight=1.5)
    content = document.tobytes()
    document.close()
    return content


def main() -> int:
    status, payload = call("POST", "/auth/login", {"phone": PHONE, "password": PASSWORD})
    if status != 200:
        print(f"FAIL 登录失败 {status}")
        return 1
    token = payload["data"]["access_token"]

    pdf = build_pdf()
    print(f"生成测试简历：{len(pdf)} 字节")

    body, content_type = multipart({}, "张三-Java后端.pdf", pdf, "application/pdf")
    status, payload = call("POST", "/resumes", token=token, raw=(body, content_type))
    if status != 201:
        print(f"FAIL 上传失败 {status} {payload}")
        return 1
    resume_id = payload["data"]["id"]
    print(f"上传成功 id={resume_id} status={payload['data']['status']}")

    # 解析在后台跑，轮询到就绪或失败
    final = None
    for _ in range(20):
        time.sleep(1.5)
        status, payload = call("GET", "/resumes/current", token=token)
        if status != 200:
            print(f"FAIL 查询失败 {status} {payload}")
            return 1
        data = payload["data"]
        if data["status"] in (3, 4):
            final = data
            break

    if not final:
        print("FAIL 解析超时（30 秒未完成）")
        return 1
    if final["status"] == 4:
        print(f"FAIL 解析失败：{final['failure_reason']}")
        return 1

    print(f"解析完成：status={final['status']} parsed_at={final['parsed_at']}")

    print("\n发起简历面试（source=2）…")
    status, payload = call("POST", "/interviews", {"source": 2}, token=token)
    if status != 201:
        print(f"FAIL 发起失败 {status} {payload}")
        return 1

    data = payload["data"]
    print(f"会话 {data['id']}，{data['question_count']} 题：")
    for item in data["questions"]:
        print(f"  {item['question_index']}. {item['question_text'][:60]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
