"""生成题库导入模板（docs/题库导入模板.xlsx）。

模板与 app/services/import_parser.py 的解析规则严格一致，
表头不能改名，填好直接在管理端「题库 → 批量导入」上传即可。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\make_question_template.py
"""

import pathlib
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUTPUT = pathlib.Path(__file__).resolve().parents[2] / "docs" / "题库导入模板.xlsx"

HEADERS = [
    "题干",
    "分类",
    "题型",
    "难度",
    "选项A",
    "选项B",
    "选项C",
    "选项D",
    "选项E",
    "选项F",
    "正确答案",
    "解析",
    "标签",
]

SAMPLES = [
    [
        "Python 中列表是可变对象，元组是不可变对象。",
        "基础",
        "判断",
        "简单",
        "正确",
        "错误",
        "",
        "",
        "",
        "",
        "A",
        "list 支持增删改，tuple 创建后不可修改。",
        "python,基础",
    ],
    [
        "Python 常用的包管理工具是？",
        "基础",
        "单选",
        "简单",
        "pip",
        "npm",
        "maven",
        "gradle",
        "",
        "",
        "A",
        "pip 是 Python 的包管理工具，npm 属于 Node.js。",
        "python,工具",
    ],
    [
        "以下哪些属于 HTTP 常见方法？",
        "基础",
        "多选",
        "中等",
        "GET",
        "POST",
        "FETCH",
        "SEND",
        "",
        "",
        "A,B",
        "GET/POST/PUT/DELETE/PATCH 是标准方法，FETCH 不是。",
        "http",
    ],
    [
        "简述列表与元组的区别。",
        "基础",
        "简答",
        "中等",
        "",
        "",
        "",
        "",
        "",
        "",
        "列表可变，元组不可变；列表用方括号、元组用圆括号；元组可作为字典键。",
        "按要点给分，覆盖主要区别即可。",
        "python",
    ],
]

GUIDE = [
    ("表头", "第一行表头不能改名、不能删列，从第 2 行开始每行一道题。"),
    ("题干", "必填。可含换行（Alt+Enter），最多 20000 字。"),
    ("分类", "选填，最多 64 字，用于题库列表筛选展示。"),
    ("题型", "必填，只能填：判断 / 单选 / 多选 / 简答（或判断题、单选题…也识别）。"),
    ("难度", "选填：简单 / 中等 / 困难，留空默认「中等」。"),
    ("选项A~F", "客观题必填至少两个；简答题留空。选项内容最多 512 字。"),
    ("正确答案（判断）", "填 A 或 B：A = 「正确」，B = 「错误」（选项 A/B 已固定为这两个词）。"),
    ("正确答案（单选）", "填一个字母，如 A。"),
    ("正确答案（多选）", "填多个字母，用英文逗号分隔，如 A,C；必须完全一致才判对。"),
    ("正确答案（简答）", "填参考答案正文，最多 20000 字；AI 按此答案的要点给分。"),
    ("解析", "选填，判分后展示给学员。"),
    ("标签", "选填，逗号分隔，最多 10 个，用于按标签筛选。"),
    ("导入方式", "管理端 → 题库 → 选择学科 → 批量导入 → 上传本文件 → 预览确认。"),
    ("注意事项", "同一个文件请只放一个学科的题目；导入按题干去重，重复的会自动跳过。"),
    ("分值规则", "系统自动定分：判断题 5 分、单选题 5 分、多选题 10 分、简答题 20 分。"),
]

FILL = PatternFill("solid", fgColor="EEF0FF")
THIN = Side(style="thin", color="D9DCE8")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def build():
    book = Workbook()

    sheet = book.active
    sheet.title = "题目数据"
    sheet.append(HEADERS)
    for row in SAMPLES:
        sheet.append(row)

    for column, width in enumerate([48, 16, 10, 10, 22, 22, 22, 22, 22, 22, 34, 40, 18], start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width

    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    sheet.freeze_panes = "A2"

    for row in sheet.iter_rows(min_row=2, max_row=len(SAMPLES) + 1):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BORDER

    guide = book.create_sheet("填写说明")
    guide.append(["字段", "说明"])
    for cell in guide[1]:
        cell.font = Font(bold=True)
        cell.fill = FILL
        cell.border = BORDER
    for row in GUIDE:
        guide.append(list(row))
    guide.column_dimensions["A"].width = 20
    guide.column_dimensions["B"].width = 90
    for row in guide.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BORDER

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    book.save(OUTPUT)
    print(f"已生成：{OUTPUT}")
    print(f"  表头 {len(HEADERS)} 列，含 4 行示例（判断/单选/多选/简答各一）")
    print(f"  第二个 sheet「填写说明」写了每种题型的正确答案填法")


if __name__ == "__main__":
    sys.exit(build())
