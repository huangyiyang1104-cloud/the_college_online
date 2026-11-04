"""给指定学科灌一套演示题（4 判断 / 8 单选 / 4 多选 / 4 简答，共 20 道）。

幂等：按题干去重，重复执行只补缺失的题目。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\seed_questions.py "AI全栈开发"
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
DEFAULT_SUBJECT = "AI全栈开发"

JUDGE = [
    ("Python 中列表是可变对象，元组是不可变对象。", True, "list 支持增删改，tuple 创建后不可修改。"),
    ("Python 的字典键必须是可哈希对象。", True, "不可哈希的对象（如 list）不能作为字典键。"),
    ("HTTP 状态码 404 表示服务器内部错误。", False, "404 是资源不存在，500 才是服务器内部错误。"),
    ("数据库索引建得越多，写入性能越好。", False, "索引会拖慢写入，需要按查询场景权衡。"),
]

SINGLE = [
    ("Python 中用哪个关键字定义函数？", ["def", "func", "function", "lambda"], "A", "def 是定义函数的关键字，lambda 是匿名函数。"),
    ("下列哪个不是 Python 的内置数据类型？", ["list", "dict", "array", "tuple"], "C", "array 来自 array 模块，不是内置类型。"),
    ("HTTP 中用于获取资源的方法是？", ["GET", "POST", "PUT", "DELETE"], "A", "GET 用于读取资源，且应当是幂等的。"),
    ("Python 常用的包管理工具是？", ["pip", "npm", "maven", "gradle"], "A", "pip 是 Python 的包管理工具，npm 属于 Node.js。"),
    ("SQL 中用于筛选分组结果的子句是？", ["WHERE", "HAVING", "ORDER BY", "LIMIT"], "B", "WHERE 过滤行，HAVING 过滤分组后的结果。"),
    ("下列哪种数据结构遵循先进先出？", ["栈", "队列", "堆", "树"], "B", "队列是 FIFO，栈是 LIFO。"),
    ("Python 中 with 语句的主要作用是？", ["自动管理资源释放", "提高循环速度", "定义匿名函数", "实现多继承"], "A", "with 依赖上下文管理器，退出时自动释放资源。"),
    ("HTTP 状态码 401 表示？", ["请求成功", "未认证", "资源不存在", "服务器错误"], "B", "401 未认证，403 才是已认证但无权限。"),
]

MULTI = [
    ("以下哪些属于 HTTP 常见方法？", ["GET", "POST", "PUT", "FETCH"], ["A", "B", "C"], "GET/POST/PUT/DELETE/PATCH 是标准方法，FETCH 不是。"),
    ("以下哪些是 Python 的不可变类型？", ["str", "tuple", "list", "int"], ["A", "B", "D"], "list 可变，其余不可变。"),
    ("以下哪些属于关系型数据库？", ["MySQL", "PostgreSQL", "Redis", "MongoDB"], ["A", "B"], "Redis 是键值库，MongoDB 是文档库。"),
    ("以下哪些符合 RESTful 设计原则？", ["用名词表示资源", "用 HTTP 方法表达动作", "URL 中直接写动词", "无状态请求"], ["A", "B", "D"], "URL 里写动词（如 /getUser）不符合 REST 风格。"),
]

SHORT = [
    (
        "简述列表与元组的区别。",
        "列表可变，元组不可变；列表用方括号、元组用圆括号；元组可作为字典键，列表不行；元组内存开销更小。",
    ),
    (
        "简述 HTTP 与 HTTPS 的区别。",
        "HTTPS 在 HTTP 与 TCP 之间加入 TLS，提供加密、完整性校验与身份认证；默认端口 443 与 80；HTTPS 需要证书。",
    ),
    (
        "简述数据库索引的作用与代价。",
        "作用：加速查询与排序，减少全表扫描。代价：占用额外存储、拖慢写入（增删改需要维护索引）、不当索引可能失效。",
    ),
    (
        "简述 RESTful API 的核心设计原则。",
        "以资源为中心，用名词表示资源路径；用 HTTP 方法表达动作；接口无状态；统一响应格式与状态码；支持幂等操作。",
    ),
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


def build_payloads(subject_id: str) -> list[dict]:
    payloads = []

    for title, correct, analysis in JUDGE:
        payloads.append(
            {
                "subject_id": subject_id,
                "type": 1,
                "difficulty": 1,
                "title": title,
                "score": 5,
                "analysis": analysis,
                "options": [
                    {"option_key": "A", "content": "正确", "is_correct": 1 if correct else 0},
                    {"option_key": "B", "content": "错误", "is_correct": 0 if correct else 1},
                ],
                "tags": ["基础"],
            }
        )

    for title, options, answer, analysis in SINGLE:
        payloads.append(
            {
                "subject_id": subject_id,
                "type": 2,
                "difficulty": 2,
                "title": title,
                "score": 5,
                "analysis": analysis,
                "options": [
                    {"option_key": key, "content": content, "is_correct": 1 if key == answer else 0}
                    for key, content in zip("ABCD", options)
                ],
                "tags": ["基础"],
            }
        )

    for title, options, correct_keys, analysis in MULTI:
        payloads.append(
            {
                "subject_id": subject_id,
                "type": 3,
                "difficulty": 3,
                "title": title,
                "score": 10,
                "analysis": analysis,
                "options": [
                    {"option_key": key, "content": content, "is_correct": 1 if key in correct_keys else 0}
                    for key, content in zip("ABCD", options)
                ],
                "tags": ["进阶"],
            }
        )

    for title, reference in SHORT:
        payloads.append(
            {
                "subject_id": subject_id,
                "type": 4,
                "difficulty": 3,
                "title": title,
                "score": 20,
                "reference_answer": reference,
                "analysis": "按参考要点给分，覆盖主要要点即可拿高分。",
                "options": [],
                "tags": ["简答"],
            }
        )

    return payloads


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUBJECT

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    matched = [item for item in payload["data"]["list"] if item["name"] == name]
    if not matched:
        print(f"没有名为「{name}」的学科；当前学科：{[i['name'] for i in payload['data']['list']]}")
        return 1
    subject_id = matched[0]["id"]

    status, payload = call(
        "GET", f"/admin/questions?subject_id={subject_id}&page=1&page_size=100", token=token
    )
    existing = {item["title"] for item in payload["data"]["list"]} if status == 200 else set()

    created = 0
    for body in build_payloads(subject_id):
        if body["title"] in existing:
            continue
        status, result = call("POST", "/admin/questions", body, token)
        if status != 201:
            print(f"创建失败：{body['title']} → {result}")
            continue
        created += 1

    print(f"OK   学科「{name}」新增题目 {created} 道（已有 {len(existing)} 道，跳过重复）")
    status, payload = call(
        "GET", f"/admin/questions?subject_id={subject_id}&page=1&page_size=100", token=token
    )
    print(f"     当前题池共 {payload['data']['total'] if status == 200 else '?'} 道")
    return 0


if __name__ == "__main__":
    sys.exit(main())
