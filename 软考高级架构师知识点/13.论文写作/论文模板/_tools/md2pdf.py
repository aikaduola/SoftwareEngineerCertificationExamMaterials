# -*- coding: utf-8 -*-
"""
Markdown -> HTML -> PDF 批量转换（中文优化 + 自动加页码）

处理两个位置：
  1. 论文模板/          —— 写作指导类文档（README、素材库、9 个主题模板）
  2. 论文模板/完整论文/  —— 可直接背诵的完整论文范文

每个位置各自输出 PDF/ 与 HTML/ 子目录，并生成一个合并「全本」。

依赖：Python 3.x + markdown + pypdf + reportlab + Microsoft Edge（或 Chrome）
用法：
      python md2pdf.py            # 全部转换
      python md2pdf.py 01         # 只转文件名含 "01" 的
      python md2pdf.py --no-page-number   # 不添加页码
"""
import re
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

import markdown

from add_page_numbers import add_page_numbers

LINE_IS_LIST = re.compile(r"^\s*([-*+]|\d+\.)\s+")

# ---------------- 配置 ----------------
SRC_DIR = Path(__file__).resolve().parent.parent          # 论文模板/
PAPER_DIR = SRC_DIR / "完整论文"                            # 论文模板/完整论文/

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "attr_list", "md_in_html"]

# 根目录排序：README 与素材库置顶
ORDER = ["README-使用说明.md", "00-项目素材库.md"]

# ---------------- 打印样式 ----------------
CSS = """
@page { size: A4; margin: 15mm 13mm; }

* { box-sizing: border-box; }

body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Hiragino Sans GB",
               "Segoe UI", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif;
  font-size: 10.5pt;
  line-height: 1.72;
  color: #24292f;
  margin: 0;
  padding: 0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

h1, h2, h3, h4, h5 { line-height: 1.35; font-weight: 700; }

h1 {
  font-size: 19pt;
  color: #14417a;
  border-bottom: 3px solid #14417a;
  padding-bottom: 7px;
  margin: 0 0 16px;
  page-break-before: always;
  page-break-after: avoid;
}
h1:first-of-type { page-break-before: avoid; }

h2 {
  font-size: 13.5pt;
  color: #14417a;
  border-left: 5px solid #14417a;
  padding-left: 10px;
  margin: 20px 0 10px;
  page-break-after: avoid;
}

h3 {
  font-size: 11.5pt;
  color: #2c3e50;
  margin: 15px 0 7px;
  page-break-after: avoid;
}

h4 {
  font-size: 10.5pt;
  color: #4a5568;
  margin: 12px 0 6px;
  page-break-after: avoid;
}

p { margin: 7px 0; }

/* 表格：允许跨页，但表头重复、单行不拆 */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0 14px;
  font-size: 9.3pt;
  page-break-inside: auto;
}
thead { display: table-header-group; }
tr { page-break-inside: avoid; }

th {
  background: #14417a;
  color: #ffffff;
  padding: 6px 8px;
  border: 1px solid #a9b8cc;
  text-align: left;
  font-weight: 700;
}
td {
  padding: 5px 8px;
  border: 1px solid #d0d7de;
  vertical-align: top;
}
tbody tr:nth-child(even) td { background: #f6f8fa; }

/* 行内代码 */
code {
  background: #f0f2f5;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
  font-size: 9.3pt;
  color: #b5305a;
  word-break: break-word;
}

/* 代码块 */
pre {
  background: #f6f8fa;
  border: 1px solid #d0d7de;
  border-radius: 5px;
  padding: 10px 13px;
  margin: 10px 0;
  overflow-x: auto;
  page-break-inside: avoid;
  white-space: pre-wrap;
  word-break: break-word;
}
pre code {
  background: none;
  padding: 0;
  color: #24292f;
  font-size: 8.8pt;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* 引用块 */
blockquote {
  border-left: 4px solid #e0a800;
  background: #fffbf0;
  margin: 11px 0;
  padding: 9px 15px;
  color: #5a4a1a;
  page-break-inside: avoid;
}
blockquote p { margin: 4px 0; }

hr {
  border: none;
  border-top: 1px solid #d8dee4;
  margin: 18px 0;
}

ul, ol { padding-left: 23px; margin: 7px 0; }
li { margin: 3px 0; }

a { color: #14417a; text-decoration: none; }

strong { color: #16191d; font-weight: 700; }

img { max-width: 100%; }

/* 封面（仅全本使用） */
.cover {
  height: 245mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  page-break-after: always;
}
.cover .c-title {
  font-size: 30pt;
  font-weight: 700;
  color: #14417a;
  letter-spacing: 2px;
  margin-bottom: 14px;
}
.cover .c-sub {
  font-size: 14pt;
  color: #4a5568;
  margin-bottom: 42px;
}
.cover .c-line {
  width: 130px;
  height: 4px;
  background: #14417a;
  margin-bottom: 42px;
}
.cover .c-meta {
  font-size: 11.5pt;
  color: #4a5568;
  line-height: 2.1;
}
"""

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def find_browser():
    for b in BROWSERS:
        if Path(b).exists():
            return b
    return None


def preprocess(md_text):
    """兜底预处理：CommonMark 要求列表前有空行，
    否则 `**标题**：` 换行后紧跟 `- 项` 会被合并成同一段落。"""
    lines = md_text.split("\n")
    out, in_code = [], False
    for line in lines:
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_code = not in_code
            out.append(line)
            continue
        if not in_code and LINE_IS_LIST.match(line) and out:
            prev = out[-1]
            ps = prev.strip()
            if (
                ps
                and not LINE_IS_LIST.match(prev)
                and not ps.startswith(("|", ">", "#"))
                and prev == prev.lstrip()
            ):
                out.append("")
        out.append(line)
    return "\n".join(out)


def render(md_text):
    return markdown.markdown(preprocess(md_text), extensions=MD_EXTENSIONS)


def write_html(html_path, title, body):
    html_path.write_text(
        HTML_TPL.format(title=title, css=CSS, body=body), encoding="utf-8"
    )


def html_to_pdf(browser, html_path, pdf_path, user_data_dir):
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=8000",
        f"--user-data-dir={user_data_dir}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240
    )
    return proc.returncode, (proc.stderr or "") + (proc.stdout or "")


def collect_md_files(src_dir, keyword=None, pin_first=True):
    files = [f for f in src_dir.glob("*.md")]
    if keyword:
        files = [f for f in files if keyword in f.name]

    def sort_key(p):
        if pin_first and p.name in ORDER:
            return (0, ORDER.index(p.name), "")
        return (1, 0, p.name)

    return sorted(files, key=sort_key)


def process_dir(browser, src_dir, tmp_profile, keyword=None,
                make_full=False, cover=None, page_number=True):
    """处理一个目录：生成单篇 PDF/HTML，可选生成全本"""
    if not src_dir.exists():
        return 0, []

    files = collect_md_files(src_dir, keyword)
    if not files:
        return 0, []

    pdf_dir = src_dir / "PDF"
    html_dir = src_dir / "HTML"
    pdf_dir.mkdir(exist_ok=True)
    html_dir.mkdir(exist_ok=True)

    print(f"\n{'=' * 66}\n【{src_dir.name}】共 {len(files)} 篇\n{'=' * 66}")
    ok, fail = 0, []

    for md_file in files:
        print(f"\n→ {md_file.name}")
        body = render(md_file.read_text(encoding="utf-8"))
        html_path = html_dir / (md_file.stem + ".html")
        pdf_path = pdf_dir / (md_file.stem + ".pdf")

        write_html(html_path, md_file.stem, body)

        rc, log = html_to_pdf(browser, html_path, pdf_path, tmp_profile)
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            note = ""
            if page_number:
                try:
                    n = add_page_numbers(pdf_path)
                    note = f"，{n} 页"
                except Exception as e:
                    note = f"，加页码失败({e})"
            size = pdf_path.stat().st_size / 1024
            print(f"   ✔ PDF ({size:.0f} KB{note})")
            ok += 1
        else:
            print(f"   ✘ PDF 失败 (rc={rc})")
            if log.strip():
                print("   " + log.strip()[:300])
            fail.append(md_file.name)

    # 全本
    if make_full and len(files) > 1:
        print(f"\n→ 生成全本（{len(files)} 篇合并）")
        parts = [f'<div class="chapter">{render(f.read_text(encoding="utf-8"))}</div>'
                 for f in files]
        cover_html = ""
        if cover:
            cover_html = (
                '<div class="cover">'
                f'<div class="c-title">{cover["title"]}</div>'
                f'<div class="c-sub">{cover["sub"]}</div>'
                '<div class="c-line"></div>'
                f'<div class="c-meta">{cover["meta"]}<br>共 {len(files)} 篇</div>'
                '</div>'
            )
        full_stem = cover["file"] if cover else "【全本】"
        full_html = html_dir / f"{full_stem}.html"
        write_html(full_html, cover["title"] if cover else "全本", cover_html + "".join(parts))

        full_pdf = pdf_dir / f"{full_stem}.pdf"
        rc, log = html_to_pdf(browser, full_html, full_pdf, tmp_profile)
        if full_pdf.exists() and full_pdf.stat().st_size > 1000:
            note = ""
            if page_number:
                try:
                    n = add_page_numbers(full_pdf)
                    note = f"，{n} 页"
                except Exception as e:
                    note = f"，加页码失败({e})"
            size = full_pdf.stat().st_size / 1024
            print(f"   ✔ 全本 PDF ({size:.0f} KB{note})")
            ok += 1
        else:
            print(f"   ✘ 全本 PDF 失败 (rc={rc})")
            if log.strip():
                print("   " + log.strip()[:300])
            fail.append("【全本】")

    return ok, fail


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    page_number = "--no-page-number" not in sys.argv
    keyword = args[0] if args else None

    browser = find_browser()
    if not browser:
        print("❌ 未找到 Edge 或 Chrome")
        return 1
    print(f"✔ 浏览器: {browser}")
    print(f"✔ 页码: {'添加' if page_number else '不添加'}")

    tmp_profile = tempfile.mkdtemp(prefix="md2pdf_")
    total_ok, all_fail = 0, []
    try:
        # 1) 根目录：写作指导文档
        ok, fail = process_dir(
            browser, SRC_DIR, tmp_profile, keyword,
            make_full=not keyword,
            cover={
                "title": "软考系统架构设计师",
                "sub": "论文模板全集（基于 H.I.S. BASE HOME 项目）",
                "meta": "含使用说明、项目素材库与 9 大主题模板<br>阅读顺序：先读《使用说明》与《项目素材库》，再按主题查阅",
                "file": "【全本】软考架构师论文模板",
            },
            page_number=page_number,
        )
        total_ok += ok
        all_fail += fail

        # 2) 完整论文目录
        ok, fail = process_dir(
            browser, PAPER_DIR, tmp_profile, keyword,
            make_full=not keyword,
            cover={
                "title": "软考系统架构设计师",
                "sub": "完整论文范文集",
                "meta": "基于 H.I.S. BASE HOME 项目真实架构撰写<br>每篇含试题、摘要与正文，约 2800 字",
                "file": "【全本】软考架构师论文范文",
            },
            page_number=page_number,
        )
        total_ok += ok
        all_fail += fail
    finally:
        shutil.rmtree(tmp_profile, ignore_errors=True)

    print("\n" + "=" * 66)
    print(f"完成：成功 {total_ok} 个，失败 {len(all_fail)} 个")
    if all_fail:
        print("失败：" + "、".join(all_fail))
    return 0 if not all_fail else 1


if __name__ == "__main__":
    sys.exit(main())
