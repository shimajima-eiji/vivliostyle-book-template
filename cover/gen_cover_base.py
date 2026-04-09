"""
書籍表紙生成ベースモジュール（book-template 共通）
描画ロジックのみ。タイトル・著者・フォントサイズは各書籍の cover-data.py で定義する。

各書籍の cover-data.py から呼び出す:
  from pathlib import Path
  import sys
  sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "cover"))
  from gen_cover_base import generate

  generate(
      bg_path="cover/bg_draft.png",
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

W, H = 1240, 1754


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


def generate(
    bg_path: str,
    title_line1: str,
    title_line2: str,
    subtitle_line1: str,
    subtitle_line2: str,
    author: str,
    font_size_title: int = 110,
    out_file: str = "cover/cover-book.png",
) -> None:
    """背景画像にテキストを合成して表紙画像を生成する。"""
    if os.path.exists(bg_path):
        img = Image.open(bg_path).convert("RGBA")
        img = ImageOps.fit(img, (W, H), Image.Resampling.LANCZOS)
    else:
        print(f"背景画像なし（{bg_path}）。チャコールグレーで生成します。")
        img = Image.new("RGBA", (W, H), (26, 26, 27, 255))

    draw = ImageDraw.Draw(img)

    f_title = load_font(font_size_title)
    f_sub   = load_font(48)
    f_auth  = load_font(45)

    def cx(text, font):
        return (W - draw.textbbox((0, 0), text, font=font)[2]) // 2

    def rx(text, font, margin=150):
        return W - draw.textbbox((0, 0), text, font=font)[2] - margin

    _draw_shadow(draw, title_line1, (cx(title_line1, f_title), int(H * 0.12)), f_title, (245, 245, 245))
    _draw_shadow(draw, title_line2, (cx(title_line2, f_title), int(H * 0.12) + font_size_title + 20), f_title, (245, 245, 245))
    _draw_shadow(draw, subtitle_line1, (cx(subtitle_line1, f_sub), int(H * 0.77)), f_sub, (230, 230, 230))
    _draw_shadow(draw, subtitle_line2, (cx(subtitle_line2, f_sub), int(H * 0.815)), f_sub, (230, 230, 230))
    _draw_shadow(draw, author, (rx(author, f_auth), H - 150), f_auth, (230, 230, 230))

    img.convert("RGB").save(out_file, "PNG")
    print(f"生成: {out_file}")
