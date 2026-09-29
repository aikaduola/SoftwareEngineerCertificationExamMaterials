# -*- coding: utf-8 -*-
"""探查参考 PDF 的结构：页数、是否为文字版、范文的格式特征。

用法：python probe_pdf.py "<pdf路径>" [起始页] [页数]
"""
import sys
import re
from pathlib import Path

from pypdf import PdfReader


def main():
    if len(sys.argv) < 2:
        print("用法: python probe_pdf.py <pdf路径> [起始页] [页数]")
        return 1

    path = Path(sys.argv[1])
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    reader = PdfReader(str(path))
    total = len(reader.pages)
    print(f"文件: {path.name}")
    print(f"总页数: {total}")
    print("=" * 72)

    # 统计全文文本量，判断是否文字版
    sample_idx = list(range(0, min(total, 12)))
    chars, empty = 0, 0
    for i in sample_idx:
        t = reader.pages[i].extract_text() or ""
        chars += len(t.strip())
        if not t.strip():
            empty += 1
    print(f"前 {len(sample_idx)} 页：提取到 {chars} 字符，空白页 {empty} 页")
    print(f"判断: {'文字版 PDF ✔' if chars > 200 else '疑似扫描版（需 OCR）✘'}")
    print("=" * 72)

    end = min(start + count, total)
    for i in range(start, end):
        page = reader.pages[i]
        text = page.extract_text() or ""
        print(f"\n----- 第 {i + 1} 页（{len(text)} 字符）-----")
        print(text[:2600])

    return 0


if __name__ == "__main__":
    sys.exit(main())
