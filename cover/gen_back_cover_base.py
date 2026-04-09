"""
書籍裏表紙生成ベースモジュール（book-template 共通）
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
    if text.strip() == "":
        return
    draw.text((pos[0] + offset[0], pos[1] + offset[1]), text, font=font, fill=shadow)
    draw.text(pos, text, font=font, fill=fill)

def generate(
    bg_path: str,
    summary_lines: list[str],
    isbn_text: str = "",
    out_file: str = "cover/back-book.png",
) -> None:
    """Pillowのみでシンプルな裏表紙画像を生成する。"""
    # 華美な背景を使わず、シンプルな単色背景（オフホワイト）にする
    img = Image.new("RGBA", (W, H), (250, 250, 250, 255))
    draw = ImageDraw.Draw(img)

    f_body = load_font(46)
    f_isbn = load_font(28)

    # 上下部に控えめなアクセントライン
    draw.rectangle([0, 0, W, 20], fill=(60, 60, 60, 255))
    draw.rectangle([0, H-20, W, H], fill=(60, 60, 60, 255))
    
    # 縁取り（薄いグレー）
    draw.rectangle([20, 20, W-20, H-20], outline=(200, 200, 200, 255), width=2)

    # サマリー描画
    start_y = int(H * 0.2)
    text_color = (40, 40, 40, 255)
    
    for i, line in enumerate(summary_lines):
        x = int(W * 0.12)
        y = start_y + i * (46 + 40)
        if line.strip() != "":
            draw.text((x, y), line, font=f_body, fill=text_color)

    # ISBN枠描画
    if isbn_text:
        x = W - 380
        y = H - 250
        box_w, box_h = 320, 100
        draw.rectangle([x, y, x + box_w, y + box_h], fill="white", outline=(150, 150, 150), width=2)
        
        bbox = draw.textbbox((0, 0), isbn_text, font=f_isbn)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = x + (box_w - text_w) / 2
        text_y = y + (box_h - text_h) / 2
        draw.text((text_x, text_y), isbn_text, font=f_isbn, fill=(0, 0, 0))

    img.convert("RGB").save(out_file, "PNG")
    print(f"生成（シンプル版）: {out_file}")
