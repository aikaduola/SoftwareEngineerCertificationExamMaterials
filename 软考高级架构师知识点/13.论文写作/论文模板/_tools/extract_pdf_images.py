# -*- coding: utf-8 -*-
"""从扫描版 PDF 提取内嵌页面图像（用于查看内容）。

用法：python extract_pdf_images.py <pdf路径> <起始页> <页数> [输出目录]
页码从 1 开始。
"""
import sys
from pathlib import Path

from pypdf import PdfReader

DEFAULT_OUT = Path(__file__).resolve().parent / "_scan_out"


def main():
    if len(sys.argv) < 4:
        print("用法: python extract_pdf_images.py <pdf> <起始页> <页数> [输出目录]")
        return 1

    pdf = Path(sys.argv[1])
    start = int(sys.argv[2]) - 1
    count = int(sys.argv[3])
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_OUT
    outdir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf))
    total = len(reader.pages)
    end = min(start + count, total)

    print(f"PDF: {pdf.name}  共 {total} 页，提取第 {start + 1}~{end} 页")
    print("-" * 68)

    for i in range(start, end):
        page = reader.pages[i]
        imgs = list(page.images)
        if not imgs:
            print(f"  第 {i + 1} 页：未找到内嵌图像")
            continue
        for j, im in enumerate(imgs):
            suffix = Path(im.name).suffix or ".png"
            if suffix.lower() not in (".png", ".jpg", ".jpeg"):
                suffix = ".png"
            out = outdir / f"p{i + 1:03d}_{j}{suffix}"
            out.write_bytes(im.data)
            size_kb = len(im.data) / 1024
            print(f"  第 {i + 1} 页 → {out.name}  ({size_kb:.0f} KB)")
    print("-" * 68)
    print(f"输出目录: {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
