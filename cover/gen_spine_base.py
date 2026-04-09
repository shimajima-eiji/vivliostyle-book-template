import os
import platform
from PIL import Image, ImageDraw, ImageFont

H = 1754

def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
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

def draw_vertical(draw, text, font, cx, start_y, fill):
    y = start_y
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = cx - w / 2
        draw.text((x, y), ch, font=font, fill=fill)
        y += h + 5

def generate_spine(
    bg_path: str,
    title: str,
    author: str,
    spine_width_mm: float,
    out_file: str,
    base_color: tuple = (26, 26, 27, 255),
    line_colors: list = None,
    prefer_base_color: bool = False,
):
    W = int(spine_width_mm * 8.352) # 1754 / 210 = 8.352 px/mm
    if os.path.exists(bg_path) and not prefer_base_color:
        src = Image.open(bg_path).convert("RGBA")
        c = src.width // 2
        crop_w = int(src.width * 0.05) if src.width > 200 else src.width
        img = src.crop((c - crop_w//2, 0, c + crop_w//2, src.height))
        img = img.resize((W, H), Image.Resampling.LANCZOS)
    else:
        img = Image.new("RGBA", (W, H), base_color)
        draw = ImageDraw.Draw(img)
        if line_colors:
            x = W // 2
            for i, c in enumerate(line_colors):
                draw.line([(x + (i*4 - 2), 0), (x + (i*4 - 2), H)], fill=c, width=2)
    
    draw = ImageDraw.Draw(img)
    font_size = min(int(W * 0.8), 60) # cap font size so it doesn't get too crazy
    f_title = load_font(font_size)
    f_auth = load_font(int(font_size * 0.8))
    
    draw_vertical(draw, title, f_title, W//2, int(H * 0.08), (245, 245, 245))
    
    # Author (horizontal rotated)
    auth_img = Image.new("RGBA", (H, W), (0,0,0,0))
    auth_draw = ImageDraw.Draw(auth_img)
    auth_bbox = auth_draw.textbbox((0,0), author, font=f_auth)
    auth_draw.text((0,0), author, font=f_auth, fill=(230,230,230))
    auth_w = auth_bbox[2] - auth_bbox[0]
    auth_h = auth_bbox[3] - auth_bbox[1]
    auth_img = auth_img.crop((0, 0, auth_w, auth_h))
    auth_img = auth_img.rotate(270, expand=True)
    img.paste(auth_img, (int(W//2 - auth_img.width//2), int(H * 0.85)), auth_img)
    
    img.convert("RGB").save(out_file, "PNG")
    print(f"Spine saved: {out_file} (Width: {W}px)")
