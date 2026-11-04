"""整理学科课程：同主题只保留发布最新的一门，并按学习路径重排节点顺序。

保留依据：B 站视频发布时间（拿不到时退回时长最长）。
安全策略：
  - 只在「同主题教程」范围内去重；
  - 含"项目/实战案例/《书名》"的课程一律不参与去重（每个项目都是独立内容）；
  - 删除为软删，可恢复。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\dedup_courses.py --dry-run   # 只看方案
    .venv\\Scripts\\python.exe scripts\\dedup_courses.py              # 执行
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
SUBJECT = "AI应用与智能体开发"

# 学习路径阶段：序号越小越靠前
STAGES = [
    (10, ("javase", "java零基础", "java入门", "java基础", "java小白", "从小白", "9天java",
          "java全套", "零基础入门", "java视频教程", "java教程", "java实战项目")),
    (20, ("多线程", "并发", "jvm", "集合", "泛型", "nio", "bio", "netty", "函数式")),
    (25, ("数据结构", "算法")),
    (30, ("mysql", "oracle", "数据库")),
    (35, ("mybatis", "jdbc", "sharding", "mycat")),
    (40, ("html", "css", "javascript", "jquery", "vue", "react", "前端")),
    (45, ("javaweb", "servlet", "jsp", "struts")),
    (50, ("springboot", "spring boot")),
    (55, ("springcloud", "spring cloud", "dubbo", "nacos", "sentinel")),
    (60, ("ssm", "springmvc", "spring注解", "spring视频", "spring框架", "spring零基础",
          "spring security", "spring data", "安全框架")),
    (70, ("redis", "rabbitmq", "rocketmq", "kafka", "activemq", "zookeeper", "nginx",
          "elastic", "elk", "搜索", "中间件")),
    (80, ("maven", "gradle", "git", "docker", "jenkins", "tomcat", "linux", "arthas",
          "gradle", "部署", "日志框架", "分库分表", "分布式事务", "任务调度", "quartz")),
    (85, ("python", "爬虫", "django", "flask", "fastapi", "数据分析", "大模型")),
    (90, ("鸿蒙", "harmonyos", "arkts")),
    (95, ("项目实战", "项目", "《", "毕业设计", "实战")),
    (99, ("面试", "八股")),
]
DEFAULT_STAGE = 50

# 去重桶：**顺序敏感**，具体技术在前、宽泛的“基础”桶在后
DEDUP_ORDER = [
    ("ssm", ("ssm",)),
    ("springcloud", ("springcloud", "spring cloud")),
    ("springboot", ("springboot",)),
    ("javaweb", ("javaweb",)),
    ("mybatis", ("mybatis",)),
    ("redis", ("redis",)),
    ("rabbitmq", ("rabbitmq",)),
    ("jvm", ("jvm",)),
    ("maven", ("maven",)),
    ("git", ("git",)),
    ("数据结构算法", ("数据结构与", "算法全套", "数据结构与java算法")),
    ("鸿蒙", ("鸿蒙", "harmonyos")),
    ("面试", ("面试专题", "面试题", "八股")),
    ("python基础", ("python零基础", "python小白", "python教程", "python基础入门", "python入门到精通")),
    ("spring", ("spring视频", "spring零基础", "spring注解", "spring框架", "新版spring")),
    ("java基础", ("java零基础", "java入门", "java基础入门", "javase", "java全套", "java视频教程", "java从小白")),
]

# 命中这些词的是「单点专题课」，内容各不相同，一律不参与去重
TOPIC_PATTERNS = (
    "jdk", "threadlocal", "skywalking", "activemq", "apollo", "stringtable", "泛型", "强转",
    "类加载器", "垃圾回收", "内存结构", "编码与解码", "百度地图", "报表", "加密", "分页",
    "源码", "剖析", "精讲", "新特性", "volatile", "hashmap", "arraylist", "linkedlist",
    "treemap", "字节码", "webservice", "quartz", "activiti", "shiro", "sentinel", "elk",
    "elastic", "sharding", "couchdb", "tair", "emq", "netty", "nio", "实例", "日志框架",
    "图形化界面", "爬虫", "数据分析", "大模型", "fastapi", "django", "flask",
    # 上/下篇是同一套课的两部分，拆开去重会断档
    "上篇", "下篇", "上部", "下部", "上集", "下集",
)

# 命中这些词的课程不参与去重（独立项目）
KEEP_ALL_PATTERNS = ("项目实战", "项目", "《", "毕业设计", "苍穹", "瑞吉", "头条", "学成",
                     "品达", "集信达", "闪聚", "传智", "万信", "好客", "ihrm", "美多",
                     "支付", "权限", "商城", "短信", "办公", "健康", "租房")

PUBDATE_CACHE: dict[str, int] = {}


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


def bvid_of(url: str) -> str:
    return url.rstrip("/").split("/")[-1].split("?")[0]


def pubdate(bvid: str) -> int:
    """返回 B 站发布时时间戳；失败返回 0。"""
    if bvid in PUBDATE_CACHE:
        return PUBDATE_CACHE[bvid]

    value = 0
    try:
        request = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode())
        if data.get("code") == 0:
            value = int(data["data"].get("pubdate") or 0)
    except Exception:
        value = 0

    PUBDATE_CACHE[bvid] = value
    time.sleep(0.25)
    return value


def bucket_of(title: str) -> str | None:
    """先排除专题课与独立项目，再按「具体技术优先」归桶。"""
    lowered = title.lower()
    if any(pattern in lowered for pattern in KEEP_ALL_PATTERNS):
        return None
    if any(pattern in lowered for pattern in TOPIC_PATTERNS):
        return None
    for name, keywords in DEDUP_ORDER:
        if any(keyword in lowered for keyword in keywords):
            return name
    return None


def pick_keep(scored: list[tuple[int, int, dict]]) -> dict:
    """保留策略：按你的要求取发布时间最新的一门；时间拿不到时退回时长最长的。

    scored 已按 (发布时间, 时长) 倒序排列，取首项即可。
    """
    return scored[0][2]


# 具体技术 → 学习阶段（顺序在前面的优先；都不命中才落到「基础」）
TECH_STAGES = [
    (70, ("redis", "rabbitmq", "rocketmq", "kafka", "activemq", "nginx", "elastic", "elk", "消息中间件")),
    (55, ("springcloud", "spring cloud", "dubbo", "nacos", "sentinel", "zookeeper", "微服务")),
    (50, ("springboot", "spring boot")),
    (60, ("ssm", "springmvc", "spring", "shiro", "security")),
    (35, ("mybatis", "jdbc")),
    (30, ("mysql", "oracle", "数据库", "mycat", "sharding")),
    (45, ("javaweb", "servlet", "jsp", "struts")),
    (20, ("多线程", "并发", "jvm", "泛型", "nio", "netty", "threadlocal", "arraylist", "hashmap",
          "函数式", "集合", "反射", "注解")),
    (25, ("数据结构", "算法")),
    (40, ("html", "css", "javascript", "jquery", "vue", "react", "前端")),
    (80, ("maven", "gradle", "git", "docker", "jenkins", "tomcat", "linux", "arthas",
          "日志框架", "分布式事务", "任务调度", "quartz", "activiti", "webservice", "apollo",
          "skywalking", "jdk", "字节码", "编码与解码")),
    (85, ("python", "django", "flask", "fastapi", "爬虫", "数据分析", "大模型")),
    (90, ("鸿蒙", "harmonyos", "arkts", "vibe")),
]


def stage_of(title: str) -> int:
    """先判项目与面试（放最后），再按具体技术定位，最后才落到基础。"""
    lowered = title.lower()
    if any(keyword in lowered for keyword in ("项目实战", "项目", "《", "毕业设计")):
        return 95
    if any(keyword in lowered for keyword in ("面试", "八股")):
        return 99
    for stage, keywords in TECH_STAGES:
        if any(keyword in lowered for keyword in keywords):
            return stage
    # 没命中具体技术：先进阶、再基础，其余视为拓展专题排到最后
    if any(keyword in lowered for keyword in ("进阶", "高级")):
        return 20
    if any(keyword in lowered for keyword in ("零基础", "入门", "基础", "javase", "小白", "从0")):
        return 10
    return 96


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    subject = next((item for item in payload["data"]["list"] if item["name"] == SUBJECT), None)
    if not subject:
        print(f"学科「{SUBJECT}」不存在")
        return 1

    subject_id = subject["id"]
    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    courses = payload["data"]["list"]
    print(f"「{SUBJECT}」共 {len(courses)} 门课程\n")

    # ---------- 分组 ----------
    buckets: dict[str, list[dict]] = {}
    for item in courses:
        name = bucket_of(item["title"])
        if name:
            buckets.setdefault(name, []).append(item)

    drop_ids: list[int] = []
    print("=== 重复组处理 ===")
    for name, items in sorted(buckets.items()):
        if len(items) < 2:
            continue

        # 查发布时间，选最新；都拿不到就选时长最长的
        scored = []
        for item in items:
            stamp = pubdate(bvid_of(item["bilibili_url"]))
            scored.append((stamp, item["duration_minutes"], item))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        keep = pick_keep(scored)
        drop = [row[2] for row in scored if row[2]["id"] != keep["id"]]

        print(f"\n[{name}] 共 {len(items)} 门 → 保留 1 门")
        for stamp, _duration, item in scored:
            mark = "保留" if item["id"] == keep["id"] else "删除"
            date = time.strftime("%Y-%m-%d", time.localtime(stamp)) if stamp else "未知"
            print(f"  {mark} [{item['id']}] {date} | {item['duration_minutes']:>5}分 | {item['title'][:44]}")
        drop_ids.extend(item["id"] for item in drop)

    print(f"\n=== 汇总 ===\n去重删除 {len(drop_ids)} 门，保留 {len(courses) - len(drop_ids)} 门")

    if dry_run:
        print("（--dry-run：未执行删除与排序）")
        return 0

    # ---------- 删除 ----------
    removed = 0
    for course_id in drop_ids:
        status, _ = call("DELETE", f"/admin/courses/{course_id}", token=token)
        if status == 204:
            removed += 1
    print(f"已删除 {removed} 门重复课程")

    # ---------- 重排 ----------
    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    remaining = payload["data"]["list"]
    def level_of(title: str) -> int:
        """同一阶段内再分「先基础、后进阶」。"""
        lowered = title.lower()
        if any(key in lowered for key in ("零基础", "入门", "基础", "小白", "从0", "全套")):
            return 0
        if any(key in lowered for key in ("进阶", "高级", "深入", "强化", "源码", "原理")):
            return 2
        return 1

    remaining.sort(
        key=lambda item: (
            stage_of(item["title"]),
            level_of(item["title"]),
            -item["duration_minutes"],
        )
    )
    order = [item["id"] for item in remaining]

    status, payload = call(
        "PUT", f"/admin/subjects/{subject_id}/courses/order", {"course_ids": order}, token
    )
    print(f"重排课程顺序：{payload['data']['updated'] if status == 200 else payload} 门")

    print("\n=== 新学习路径（前 25 个节点）===")
    for index, item in enumerate(remaining[:25], start=1):
        print(f"  {index:2d}. {item['title'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
