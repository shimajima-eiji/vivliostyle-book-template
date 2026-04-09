"""
書籍裏表紙生成ベースモジュール（book-template 共通）
商業同人誌向けプロフェッショナルデザイン
"""

import os
import platform

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W, H = 1240, 1754

def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Windows / macOS 両対応フォント取得。"""
    if platform.system() == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\meiryob.ttc" if bold else "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\yumin.ttf",
            "C:\\Windows\\Fonts\\msmincho.ttc",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold
            else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_dummy_qr(draw: ImageDraw.Draw, x: int, y: int, size: int):
    """シンプルなQRコードプレースホルダーを描画"""
    draw.rectangle([x, y, x + size, y + size], fill="white", outline=(200, 200, 200), width=2)
    margin = 15
    draw.rectangle([x+margin, y+margin, x+margin+30, y+margin+30], fill=(40, 40, 40))
    draw.rectangle([x+size-margin-30, y+margin, x+size-margin, y+margin+30], fill=(40, 40, 40))
    draw.rectangle([x+margin, y+size-margin-30, x+margin+30, y+size-margin], fill=(40, 40, 40))
    f_small = load_font(20, bold=True)
    draw.text((x + size/2 - 45, y + size/2 - 10), "QR CODE", fill=(120, 120, 120), font=f_small)

def generate(
    bg_path: str,
    catchphrase_lines: list[str],
    accent_color: tuple = (70, 130, 250, 255),
    url_text: str = "https://nomuraya.com",
    out_file: str = "cover/back-book.png",
) -> None:
    # 完全に一律ではなく、各書籍の表紙背景画像を取り込む
    if os.path.exists(bg_path):
        src = Image.open(bg_path).convert("RGBA")
        img = ImageOps.fit(src, (W, H), Image.Resampling.LANCZOS)
        # 表紙ほど華美にせずテキストの視認性を確保するため、全体をぼかしてダークレイヤーを重ねる
        img = img.filter(ImageFilter.GaussianBlur(15))
        overlay = Image.new("RGBA", (W, H), (20, 20, 25, 210)) # 黒を強めに透過で重ねる
        img = Image.alpha_composite(img, overlay)
    else:
        # 背景がない場合のフォールバック
        img = Image.new("RGBA", (W, H), (28, 28, 30, 255))

    draw = ImageDraw.Draw(img)
    text_color = (245, 245, 245, 255)

    f_catch = load_font(60, bold=True)
    f_info = load_font(32, bold=False)
    f_logo = load_font(40, bold=True)

    # 1. キャッチフレーズ
    start_y = int(H * 0.38)
    for i, line in enumerate(catchphrase_lines):
        x = int(W * 0.15)
        y = start_y + i * (60 + 40)
        draw.text((x, y), line, font=f_catch, fill=text_color)
        
    # 書籍ごとに異なるアクセントカラーのライン
    line_h = len(catchphrase_lines) * 100 - 40
    draw.rectangle([int(W * 0.15) - 35, start_y + 5, int(W * 0.15) - 20, start_y + line_h], fill=accent_color)

    # 2. サークル情報（左下）
    info_y = H - 300
    draw.text((int(W * 0.15), info_y), "Published by nomuraya", font=f_logo, fill=text_color)
    draw.text((int(W * 0.15), info_y + 60), url_text, font=f_info, fill=(160, 160, 160, 255))

    # 3. QRコードプレースホルダー（右下）
    qr_size = 180
    qr_x = W - int(W * 0.15) - qr_size
    draw_dummy_qr(draw, qr_x, H - 325, qr_size)

    img.convert("RGB").save(out_file, "PNG")
    print(f"生成（表紙連動プロ版）: {out_file}")
