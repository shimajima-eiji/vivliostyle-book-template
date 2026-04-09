"""
書籍裏表紙生成ベースモジュール（book-template 共通）
説明テキストを置かず、色面と余白だけで本の人格を閉じるためのミニマルな描画ロジック。
"""

import os
import platform

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1240, 1754


def load_font(size: int) -> ImageFont.FreeTypeFont:
    if platform.system() == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\consola.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Optima.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _to_rgba(color, alpha=None):
    if len(color) == 4:
        rgba = color
    else:
        rgba = (*color, 255)
    if alpha is None:
        return rgba
    return (rgba[0], rgba[1], rgba[2], alpha)


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def _make_gradient(start_color, end_color):
    start = _to_rgba(start_color)
    end = _to_rgba(end_color)
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        color = tuple(_lerp(start[i], end[i], t) for i in range(4))
        draw.line([(0, y), (W, y)], fill=color)
    return img


def _apply_rectangle(img, spec):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle(spec["box"], fill=_to_rgba(spec["fill"]))
    blur = spec.get("blur", 0)
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img, layer)


def _apply_glow(img, spec):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = spec["center"]
    radius = spec["radius"]
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(box, fill=_to_rgba(spec["fill"]))
    blur = spec.get("blur", max(radius // 2, 1))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img, layer)


def _apply_line(draw, spec):
    draw.line(spec["xy"], fill=_to_rgba(spec["fill"]), width=spec.get("width", 1))


def _apply_signature(draw, spec):
    text = spec["text"]
    font = load_font(spec.get("size", 24))
    margin_x = spec.get("margin_x", 64)
    margin_y = spec.get("margin_y", 64)
    fill = _to_rgba(spec.get("fill", (255, 255, 255, 80)))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    align = spec.get("align", "left")
    x = margin_x if align == "left" else W - tw - margin_x
    y = H - th - margin_y
    draw.text((x, y), text, font=font, fill=fill)


def _legacy_back_cover(bg_path: str, english_title: str):
    if os.path.exists(bg_path):
        src = Image.open(bg_path).convert("RGBA")
        img = ImageOps.fit(src, (W, H), Image.Resampling.LANCZOS)
        img = ImageOps.mirror(img)
        img = img.filter(ImageFilter.GaussianBlur(30))
        overlay = Image.new("RGBA", (W, H), (15, 15, 18, 200))
        img = Image.alpha_composite(img, overlay)
    else:
        img = Image.new("RGBA", (W, H), (30, 30, 32, 255))

    draw = ImageDraw.Draw(img)
    f_center = load_font(45)
    f_bottom = load_font(30)

    bbox = draw.textbbox((0, 0), english_title, font=f_center)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, H // 2 - 40), english_title, font=f_center, fill=(230, 230, 230, 255))

    pub_text = "Published by nomuraya   |   nomuraya.com"
    pbox = draw.textbbox((0, 0), pub_text, font=f_bottom)
    pw = pbox[2] - pbox[0]
    draw.text(((W - pw) / 2, H - 150), pub_text, font=f_bottom, fill=(120, 120, 120, 255))
    return img


def generate(
    bg_path: str = "",
    english_title: str = "",
    out_file: str = "cover/back-book.png",
    style: dict | None = None,
) -> None:
    if style is None:
        img = _legacy_back_cover(bg_path, english_title)
    else:
        background = style.get("background", {})
        start_color = background.get("top", background.get("color", (24, 24, 26, 255)))
        end_color = background.get("bottom", start_color)
        img = _make_gradient(start_color, end_color)

        for rect in style.get("rectangles", []):
            img = _apply_rectangle(img, rect)
        for glow in style.get("glows", []):
            img = _apply_glow(img, glow)

        draw = ImageDraw.Draw(img)
        for line in style.get("lines", []):
            _apply_line(draw, line)
        if style.get("signature"):
            _apply_signature(draw, style["signature"])

    img.convert("RGB").save(out_file, "PNG")
    print(f"Back cover generated: {out_file}")
