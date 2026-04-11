"""
書籍裏表紙生成ベースモジュール（book-template 共通）
印刷基準（300dpi）でマスターを生成し、幾何学パターンをサポート。
"""

import os
import platform
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import print_specs
    import patterns
except ImportError:
    import print_specs
    import patterns

W, H = print_specs.TRIM_W_PX, print_specs.TRIM_H_PX

def load_font(size: int) -> ImageFont.FreeTypeFont:
    if platform.system() == "Windows":
        candidates = ["C:\\Windows\\Fonts\\meiryo.ttc", "C:\\Windows\\Fonts\\consola.ttf"]
    else:
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
    return ImageFont.load_default()

def _to_rgba(color, alpha=None):
    rgba = color if len(color) == 4 else (*color, 255)
    return (rgba[0], rgba[1], rgba[2], alpha) if alpha is not None else rgba

def _make_gradient(start_color, end_color):
    start, end = _to_rgba(start_color), _to_rgba(end_color)
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(round(start[i] + (end[i] - start[i]) * t) for i in range(4))
        draw.line([(0, y), (W, y)], fill=c)
    return img

def generate(style: dict, out_file: str = "cover/back-book.png") -> None:
    bg = style.get("background", {})
    img = _make_gradient(bg.get("top", (24, 24, 26)), bg.get("bottom", (24, 24, 26)))

    # --- 幾何学パターンの重畳 ---
    p_style = style.get("patterns", [])
    if "dots" in p_style:
        img = Image.alpha_composite(img, patterns.create_dot_grid(W, H, spacing=60, color=(255, 255, 255, 20)))
    if "waves" in p_style:
        img = Image.alpha_composite(img, patterns.create_math_waves(W, H, color=(255, 255, 255, 25)))
    if "network" in p_style:
        img = Image.alpha_composite(img, patterns.create_network(W, H, nodes=18, color=(255, 255, 255, 12)))
    if "frame" in p_style:
        img = Image.alpha_composite(img, patterns.create_frame_accent(W, H, color=(255, 255, 255, 30)))
    if "grain" in p_style:
        img = Image.alpha_composite(img, patterns.create_grain(W, H, intensity=8))

    # 既存の図形描画
    draw = ImageDraw.Draw(img)
    for rect in style.get("rectangles", []):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle(rect["box"], fill=_to_rgba(rect["fill"]))
        if rect.get("blur"): layer = layer.filter(ImageFilter.GaussianBlur(rect["blur"]))
        img = Image.alpha_composite(img, layer)
    
    for glow in style.get("glows", []):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((glow["center"][0]-glow["radius"], glow["center"][1]-glow["radius"], glow["center"][0]+glow["radius"], glow["center"][1]+glow["radius"]), fill=_to_rgba(glow["fill"]))
        img = Image.alpha_composite(img, layer.filter(ImageFilter.GaussianBlur(glow.get("blur", glow["radius"]//2))))

    draw = ImageDraw.Draw(img) # 再度線の描画用に取得
    for line in style.get("lines", []):
        draw.line(line["xy"], fill=_to_rgba(line["fill"]), width=line.get("width", 1))
    
    if style.get("signature"):
        sig = style["signature"]
        font = load_font(sig.get("size", 28))
        sig_text = sig["text"]
        bbox = draw.textbbox((0, 0), sig_text, font=font)
        text_w = bbox[2] - bbox[0]
        # 右端から 80px のマージンを確保
        draw.text((W - text_w - 80, H - 100), sig_text, font=font, fill=_to_rgba(sig.get("fill", (255,255,255,60))))

    img.convert("RGB").save(out_file, "PNG")
    print(f"Back cover MASTER generated with patterns: {out_file}")
