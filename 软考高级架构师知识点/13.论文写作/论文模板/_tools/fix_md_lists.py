# -*- coding: utf-8 -*-
"""
修复 Markdown 中「段落行紧贴列表项」导致的渲染合并问题。

问题：CommonMark 严格要求列表前有空行，否则
      `**写什么**：` 换行后紧跟 `- 项目名称…` 会被当成同一段落，
      列表符号 `-` 原样显示。

用法：
    python fix_md_lists.py --dry     # 只统计，不改文件
    python fix_md_lists.py           # 实际修改
"""
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent

LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def scan(text):
    """返回需要插入空行的行号列表（1-based），以及修复后的文本"""
    lines = text.split("\n")
    out = []
    hits = []
    in_code = False

    for idx, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_code = not in_code
            out.append(line)
            continue

        if in_code:
            out.append(line)
            continue

        if LIST_RE.match(line) and out:
            prev = out[-1]
            ps = prev.strip()
            # 上一行非空、不是列表、不是表格、不是引用、不是标题
            # 且上一行必须顶格——缩进的行是列表项的续行，其后不能插空行
            if (
                ps
                and not LIST_RE.match(prev)
                and not ps.startswith("|")
                and not ps.startswith(">")
                and not ps.startswith("#")
                and prev == prev.lstrip()
            ):
                out.append("")
                hits.append((idx, ps[:60]))

        out.append(line)

    return hits, "\n".join(out)


def main():
    dry = "--dry" in sys.argv
    total_files, total_hits = 0, 0

    for md in sorted(SRC_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        hits, fixed = scan(text)
        if not hits:
            continue
        total_files += 1
        total_hits += len(hits)
        print(f"\n{md.name}  →  需修复 {len(hits)} 处")
        for lineno, preview in hits[:8]:
            print(f"    行 {lineno:>4}: {preview}")
        if len(hits) > 8:
            print(f"    … 其余 {len(hits) - 8} 处")
        if not dry:
            md.write_text(fixed, encoding="utf-8")

    print("\n" + "=" * 60)
    mode = "扫描（未修改）" if dry else "已修复"
    print(f"{mode}：{total_files} 个文件，{total_hits} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
