"""依次跑全部冒烟套件并汇总结果。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/run_all_smoke.py
    .venv\\Scripts\\python.exe scripts/run_all_smoke.py --only admin,student
"""

import re
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 GBK，打印中文前先切到 UTF-8，避免 UnicodeEncodeError
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

SUITES = [
    ("admin", "管理端（学科/课程/题库/账号/日志/资料库）"),
    ("student", "C1 认证（发码/注册/登录/刷新/退出/资料）"),
    ("catalog", "C2+C3（节点图/点亮/学习记录）"),
    ("practice", "C4 刷题（组卷/判分/答卷）"),
    ("wrong", "C5 错题本（列表/重做/移除）"),
    ("import", "B2 导入（课程/题库 Excel）"),
    ("interview", "C6 面试（出题/作答/追问/结束/报告）"),
]

RESULT = re.compile(r"通过\s*(\d+)\s*项，失败\s*(\d+)\s*项")


def run_one(name: str) -> tuple[int, int] | None:
    script = ROOT / "scripts" / f"smoke_{name}.py"
    if not script.exists():
        return None

    proc = subprocess.run([str(PYTHON), str(script)], cwd=str(ROOT), capture_output=True)

    # 子进程可能按 GBK 或 UTF-8 输出，两种都试，取能匹配汇总行的那个
    output = ""
    for encoding in ("utf-8", "gbk"):
        try:
            text = proc.stdout.decode(encoding)
        except Exception:
            continue
        if RESULT.search(text):
            output = text
            break
        output = output or text

    match = RESULT.search(output)
    if not match:
        tail = "\n".join(output.strip().splitlines()[-6:]) or "(无输出)"
        print(f"  ! 未匹配到汇总行，退出码 {proc.returncode}")
        print(f"    {tail}")
        return (0, 1)
    return int(match.group(1)), int(match.group(2))


def main() -> int:
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    total_pass = 0
    total_fail = 0

    for name, label in SUITES:
        if only and name not in only:
            continue
        print(f"[{name}] {label} …")
        result = run_one(name)
        if result is None:
            print("  跳过（脚本不存在）")
            continue
        passed, failed = result
        total_pass += passed
        total_fail += failed
        flag = "OK" if failed == 0 else "FAIL"
        print(f"  {flag} 通过 {passed}，失败 {failed}\n")

    print("=" * 44)
    print(f"合计：通过 {total_pass} 项，失败 {total_fail} 项")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
