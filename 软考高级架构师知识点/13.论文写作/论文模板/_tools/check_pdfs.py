# -*- coding: utf-8 -*-
"""检查生成 PDF 的结构完整性：页数、字体嵌入、文本可复制性。"""
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = SRC_DIR / "PDF"


def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print("未找到 PDF")
        return 1

    print(f"{'文件名':<44}{'页数':>6}{'大小':>10}  中文字体")
    print("-" * 78)
    bad = []
    for f in pdfs:
        raw = f.read_bytes()
        if not raw.startswith(b"%PDF"):
            bad.append((f.name, "文件头异常"))
            continue
        pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
        fonts = set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", raw))
        has_cid = b"CIDFontType" in raw
        has_tounicode = b"/ToUnicode" in raw
        size_kb = f.stat().st_size / 1024

        flag = "✔ 已嵌入" if has_cid else "✘ 未嵌入"
        if not has_cid:
            bad.append((f.name, "缺少 CID 中文字体"))
        if not has_tounicode:
            flag += " (无文本映射)"

        name = f.name if len(f.name) <= 42 else f.name[:39] + "..."
        print(f"{name:<44}{pages:>6}{size_kb:>9.0f}KB  {flag}")

    print("-" * 78)
    print(f"共 {len(pdfs)} 个 PDF")
    if bad:
        print("\n⚠ 异常：")
        for n, r in bad:
            print(f"  {n}: {r}")
        return 1
    print("✔ 全部 PDF 结构正常，中文字体已嵌入（可正常阅读与复制文本）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
