"""
書籍表紙生成ベースモジュール（book-template 共通）
描画ロジックのみ。タイトル・著者・フォントサイズは各書籍の cover-data.py で定義する。

各書籍の cover-data.py から呼び出す:
  from pathlib import Path
  import sys
  sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "cover"))
  from gen_cover_base import generate

  generate(
      bg_path="cover/_fixed/front-source.png",
      title_line1="書名行1",
      title_line2="書名行2",
      subtitle_line1="サブタイトル1",
      subtitle_line2="サブタイトル2",
      author="著：nomuraya",
      font_size_title=110,
      out_file="cover/cover-book.png",
  )
"""

import os
import platform

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import print_specs
    W, H = print_specs.TRIM_W_PX, print_specs.TRIM_H_PX
except:
    W, H = 1748, 2480 # Fallback 300dpi


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Windows / macOS 両対応フォント取得。"""
    if platform.system() == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\yumin.ttf",
            "C:\\Windows\\Fonts\\msmincho.ttc",
            "C:\\Windows\\Fonts\\meiryob.ttc" if bold else "C:\\Windows\\Fonts\\meiryo.ttc",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold
            else "/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_shadow(draw, text, pos, font, fill, shadow=(0, 0, 0, 100), offset=(2, 2)):
    draw.text((pos[0] + offset[0], pos[1] + offset[1]), text, font=font, fill=shadow)
    draw.text(pos, text, font=font, fill=fill)


def _apply_overlay_rectangles(img, overlay_rectangles):
    if not overlay_rectangles:
        return img
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for rect in overlay_rectangles:
        draw.rectangle(rect["box"], fill=rect["fill"])
    return Image.alpha_composite(img, layer)


def generate(
    bg_path: str,
    title_line1: str,
    title_line2: str,
    subtitle_line1: str,
    subtitle_line2: str,
    author: str,
    font_size_title: int = 110,
    out_file: str = "cover/cover-book.png",
    title_lines: list[str] | None = None,
    subtitle_lines: list[str] | None = None,
    title_top_ratio: float = 0.12,
    title_gap: int = 20,
    subtitle_top_ratio: float = 0.77,
    subtitle_gap: int = 10,
    font_size_sub: int = 48,
    author_margin_right: int = 150,
    author_bottom_margin: int = 150,
    overlay_rectangles: list[dict] | None = None,
) -> None:
    """背景画像にテキストを合成して表紙画像を生成する。"""
    if os.path.exists(bg_path):
        img = Image.open(bg_path).convert("RGBA")
        img = ImageOps.fit(img, (W, H), Image.Resampling.LANCZOS)
    else:
        print(f"背景画像なし（{bg_path}）。チャコールグレーで生成します。")
        img = Image.new("RGBA", (W, H), (26, 26, 27, 255))

    img = _apply_overlay_rectangles(img, overlay_rectangles)

    draw = ImageDraw.Draw(img)

    f_title = load_font(font_size_title)
    f_sub   = load_font(font_size_sub)
    f_auth  = load_font(45)

    resolved_title_lines = title_lines or [line for line in (title_line1, title_line2) if line]
    resolved_subtitle_lines = subtitle_lines or [line for line in (subtitle_line1, subtitle_line2) if line]

    def cx(text, font):
        return (W - draw.textbbox((0, 0), text, font=font)[2]) // 2

    def rx(text, font, margin=150):
        return W - draw.textbbox((0, 0), text, font=font)[2] - margin

    y = int(H * title_top_ratio)
    for line in resolved_title_lines:
        _draw_shadow(draw, line, (cx(line, f_title), y), f_title, (245, 245, 245))
        bbox = draw.textbbox((0, 0), line, font=f_title)
        y += (bbox[3] - bbox[1]) + title_gap

    y = int(H * subtitle_top_ratio)
    for line in resolved_subtitle_lines:
        _draw_shadow(draw, line, (cx(line, f_sub), y), f_sub, (230, 230, 230))
        bbox = draw.textbbox((0, 0), line, font=f_sub)
        y += (bbox[3] - bbox[1]) + subtitle_gap

    _draw_shadow(draw, author, (rx(author, f_auth, margin=author_margin_right), H - author_bottom_margin), f_auth, (230, 230, 230))

    img.convert("RGB").save(out_file, "PNG")
    print(f"生成: {out_file}")
