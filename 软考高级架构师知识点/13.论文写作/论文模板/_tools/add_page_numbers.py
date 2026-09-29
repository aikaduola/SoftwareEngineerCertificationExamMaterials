# -*- coding: utf-8 -*-
"""给 PDF 添加页脚页码。

背景：Chrome/Edge 的 --print-to-pdf 不支持 CSS 分页页码
（CSS Paged Media 的 @bottom-center / counter(page) 在 Chromium 中未实现），
因此改为 PDF 生成后用 reportlab + pypdf 叠加页码。

用法：
    python add_page_numbers.py <pdf路径> [pdf路径2 ...]
    python add_page_numbers.py --all          # 处理所有 PDF/ 目录下的 pdf
"""
import io
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 页码字体（宋体优先，回退黑体）
FONT_CANDIDATES = [
    ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
]
FONT_NAME = None

FONT_SIZE = 9
BOTTOM_MARGIN_PT = 26  # 距页面底部（pt），落在 @page 15mm 页边距内


def _ensure_font():
    global FONT_NAME
    if FONT_NAME:
        return FONT_NAME
    for name, path in FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            # ttc 为字体集合，需指定 subfontIndex
            if path.lower().endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont(name, path))
            FONT_NAME = name
            return name
        except Exception:
            continue
    raise RuntimeError("未找到可用的中文字体（simsun.ttc / simhei.ttf）")


def add_page_numbers(pdf_path, out_path=None):
    """在 PDF 每页页脚居中写入「第 X 页 / 共 Y 页」。原地覆盖或另存。"""
    font = _ensure_font()
    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    if total == 0:
        return 0

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont(font, FONT_SIZE)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawCentredString(width / 2.0, BOTTOM_MARGIN_PT, f"第 {i + 1} 页 / 共 {total} 页")
        c.save()
        packet.seek(0)

        page.merge_page(PdfReader(packet).pages[0])
        writer.add_page(page)

    # 保留原文档大纲（书签）等元信息
    try:
        if reader.outline:
            writer.add_outline_item("返回目录", 0)
    except Exception:
        pass
    if reader.metadata:
        writer.add_metadata(
            {k: v for k, v in reader.metadata.items() if isinstance(v, str)}
        )

    with open(out_path, "wb") as f:
        writer.write(f)
    return total


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    if sys.argv[1] == "--all":
        root = Path(__file__).resolve().parent.parent
        targets = sorted(root.rglob("PDF/*.pdf"))
    else:
        targets = [Path(p) for p in sys.argv[1:]]

    ok, fail = 0, []
    for t in targets:
        if not t.exists():
            print(f"  ✘ 不存在: {t}")
            fail.append(t.name)
            continue
        try:
            n = add_page_numbers(t)
            print(f"  ✔ {t.name}  ({n} 页)")
            ok += 1
        except Exception as e:
            print(f"  ✘ {t.name}: {e}")
            fail.append(t.name)

    print(f"\n完成：成功 {ok}，失败 {len(fail)}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
