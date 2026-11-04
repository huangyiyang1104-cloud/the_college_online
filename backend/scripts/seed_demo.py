"""演示数据：三个学科 + 各自的学习路径课程（幂等，按学科名去重）。

⚠️ 该脚本会写入真实的学科与课程数据，执行前必须先与项目负责人确认，
   不要默认认为"库里空的就该灌数据"。



用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\seed_demo.py
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
VIDEO = "https://www.bilibili.com/video/BV1WWYE6LEzx"

DEMO = [
    {
        "name": "AI 全栈开发",
        "icon": "🧠",
        "description": "从语法到接口，把 AI 应用的后端骨架搭起来",
        "keywords": ["python", "fastapi", "llm"],
        "courses": [
            ("Python 环境搭建与基础语法", 52, "装好环境，跑通第一个脚本"),
            ("数据结构与算法入门", 65, "列表、字典、栈与队列的取舍"),
            ("HTTP 协议与接口设计基础", 48, "请求响应、状态码与 REST 语义"),
            ("FastAPI 快速上手", 60, "路由、依赖注入与自动文档"),
        ],
    },
    {
        "name": "Agent 开发",
        "icon": "🤖",
        "description": "围绕大模型构建可落地的智能体应用",
        "keywords": ["agent", "rag", "prompt"],
        "courses": [
            ("LLM 基础与提示词工程", 45, "上下文、温度与提示词结构"),
            ("RAG 检索增强实战", 70, "切分、向量化与召回融合"),
            ("Agent 编排与工具调用", 55, "任务拆解、工具协议与失败重试"),
        ],
    },
    {
        "name": "Java 开发",
        "icon": "☕",
        "description": "后端主流技术栈的完整入门路径",
        "keywords": ["java", "spring", "mybatis"],
        "courses": [
            ("Java 基础语法与面向对象", 68, "类型系统、集合与继承"),
            ("Spring Boot 入门", 72, "自动装配、配置与启动流程"),
            ("MyBatis 与数据库访问", 55, "映射、动态 SQL 与事务"),
        ],
    },
]


def call(method: str, path: str, body: dict | None = None, token: str = ""):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else None)


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if status != 200 or not token:
        print(f"管理员登录失败：{payload}")
        return 1

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    existing = {item["name"]: item["id"] for item in payload["data"]["list"]}

    created_subjects = 0
    created_courses = 0

    for subject in DEMO:
        subject_id = existing.get(subject["name"])
        if not subject_id:
            status, payload = call(
                "POST",
                "/admin/subjects",
                {
                    "name": subject["name"],
                    "icon": subject["icon"],
                    "description": subject["description"],
                    "keywords": subject["keywords"],
                },
                token,
            )
            if status != 201:
                print(f"创建学科失败：{subject['name']} {payload}")
                continue
            subject_id = payload["data"]["id"]
            created_subjects += 1

        status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
        titles = {item["title"] for item in payload["data"]["list"]} if status == 200 else set()

        for title, minutes, description in subject["courses"]:
            if title in titles:
                continue
            status, _ = call(
                "POST",
                f"/admin/subjects/{subject_id}/courses",
                {
                    "title": title,
                    "duration_minutes": minutes,
                    "description": description,
                    "bilibili_url": VIDEO,
                },
                token,
            )
            if status == 201:
                created_courses += 1

    print(f"OK   新增学科 {created_subjects} 个，新增课程 {created_courses} 门")
    print("     已有数据不会重复创建，可反复执行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
