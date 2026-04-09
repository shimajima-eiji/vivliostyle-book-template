"""
章扉画像生成ベースモジュール（book-template 共通）
レイアウトロジックのみ。PALETTES/CHAPTERS/TITLE_LINES は各書籍の chapter-data.py で定義する。

各書籍の chapter-data.py から呼び出す:
  from pathlib import Path
  import sys
  sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "assets"))
  from gen_chapter_covers_base import render_all
  render_all(PALETTES, CHAPTERS, TITLE_LINES, out_dir=Path(__file__).parent)
"""

import os
import platform
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1240, 1754
SPLIT = W // 3


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Windows / macOS 両対応フォント取得。"""
    if platform.system() == "Windows":
        candidates = (
            ["C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/NotoSansJP-VF.ttf"]
            if bold else
            ["C:/Windows/Fonts/yumin.ttf", "C:/Windows/Fonts/NotoSerifJP-VF.ttf"]
        )
    else:
        candidates = (
            ["/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
             "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"]
            if bold else
            ["/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc",
             "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"]
        )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_chapter_cover(
    num: str,
    chapter_label: str,
    subcopy: str,
    tag: str,
    palette: dict,
    title_lines: list[str],
) -> Image.Image:
    img = Image.new("RGB", (W, H), palette["bg"])
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, SPLIT, H], fill=palette["accent"])

    f_tag = get_font(180, bold=True)
    tw = draw.textlength(tag, font=f_tag)
    draw.text(((SPLIT - tw) // 2, (H - f_tag.size) // 2 - 10), tag,
              font=f_tag, fill=(255, 255, 255))

    mx = SPLIT + 60
    mr = W - 60

    f_chap  = get_font(32, bold=True)
    f_title = get_font(56)
    f_sub   = get_font(28)

    sub_lines = textwrap.wrap(subcopy, 22)

    CHAP_H   = 42
    GAP_CR   = 20
    RULE_H   = 3
    GAP_RT   = 28
    TITLE_LH = 80
    title_h  = len(title_lines) * TITLE_LH
    GAP_TR   = 24
    GAP_RS   = 26
    SUB_LH   = 48
    sub_h    = len(sub_lines) * SUB_LH

    block_h = CHAP_H + GAP_CR + RULE_H + GAP_RT + title_h + GAP_TR + RULE_H + GAP_RS + sub_h
    top = (H - block_h) // 2

    draw.text((mx, top), chapter_label, font=f_chap, fill=palette["accent"])

    rule1_y = top + CHAP_H + GAP_CR
    draw.line([(mx, rule1_y), (mr, rule1_y)], fill=palette["accent"], width=RULE_H)

    ty = rule1_y + GAP_RT
    for line in title_lines:
        draw.text((mx, ty), line, font=f_title, fill=palette["text"])
        ty += TITLE_LH

    rule2_y = ty + GAP_TR
    draw.line([(mx, rule2_y), (mr, rule2_y)], fill=palette["accent"], width=RULE_H)

    sy = rule2_y + GAP_RS
    for line in sub_lines:
        draw.text((mx, sy), line, font=f_sub, fill=palette["text"])
        sy += SUB_LH

    return img


def render_all(
    palettes: dict,
    chapters: list[tuple],
    title_lines: dict,
    out_dir: Path,
) -> None:
    """全章の章扉画像を生成して out_dir に保存する。"""
    for num, chapter_label, _title, subcopy, tag, palette_name in chapters:
        palette = palettes[palette_name]
        lines = title_lines[num]
        img = make_chapter_cover(num, chapter_label, subcopy, tag, palette, lines)
        path = out_dir / f"chapter-{num}.png"
        img.save(path, "PNG")
        print(f"  {num} [{tag}]: {path}")
    print(f"\n  {len(chapters)}枚 -> {out_dir}/chapter-XX.png")
