"""
裏表紙・背表紙・表紙を1枚に連結した確認用プレビューを生成する。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def add_shadow(block: Image.Image, blur: int = 28, offset: tuple[int, int] = (0, 20)) -> Image.Image:
    shadow = Image.new("RGBA", (block.width + blur * 4, block.height + blur * 4), (0, 0, 0, 0))
    mask = Image.new("L", block.size, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, block.width, block.height), fill=180)
    shadow.paste((0, 0, 0, 255), (blur * 2 + offset[0], blur * 2 + offset[1]), mask)
    return shadow.filter(ImageFilter.GaussianBlur(blur))


def generate_preview(front_path: Path, spine_path: Path, back_path: Path, out_path: Path, title: str | None = None) -> None:
    front = Image.open(front_path).convert("RGBA")
    spine = Image.open(spine_path).convert("RGBA")
    back = Image.open(back_path).convert("RGBA")

    block_w = back.width + spine.width + front.width
    block_h = max(front.height, spine.height, back.height)

    block = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    x = 0
    block.paste(back, (x, 0), back)
    x += back.width
    block.paste(spine, (x, 0), spine)
    x += spine.width
    block.paste(front, (x, 0), front)

    pad_x = 140
    pad_top = 140 if title else 100
    pad_bottom = 120
    canvas = Image.new("RGBA", (block_w + pad_x * 2, block_h + pad_top + pad_bottom), (236, 234, 229, 255))

    shadow = add_shadow(block)
    shadow_x = (canvas.width - shadow.width) // 2
    shadow_y = pad_top + (block_h - shadow.height) // 2
    canvas.alpha_composite(shadow, (shadow_x, shadow_y))

    block_x = (canvas.width - block.width) // 2
    block_y = pad_top
    canvas.alpha_composite(block, (block_x, block_y))

    if title:
        draw = ImageDraw.Draw(canvas)
        font = load_font(34)
        fill = (78, 77, 74, 255)
        bbox = draw.textbbox((0, 0), title, font=font)
        draw.text(((canvas.width - (bbox[2] - bbox[0])) / 2, 48), title, font=font, fill=fill)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "PNG")
    print(f"Wrap preview generated: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--front", required=True)
    parser.add_argument("--spine", required=True)
    parser.add_argument("--back", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    generate_preview(
        front_path=Path(args.front),
        spine_path=Path(args.spine),
        back_path=Path(args.back),
        out_path=Path(args.out),
        title=args.title or None,
    )


if __name__ == "__main__":
    main()
