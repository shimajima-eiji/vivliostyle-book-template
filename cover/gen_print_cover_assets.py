"""
印刷向け表紙アセットを生成する。

- A5トリム: 148mm x 210mm
- 既定塗り足し: 3mm
- 既定解像度: 300dpi

出力:
- front-trim-300dpi.png / pdf
- back-trim-300dpi.png / pdf
- front-bleed-300dpi.png / pdf
- back-bleed-300dpi.png / pdf
- spine-trim-300dpi.png / pdf
- spread-trim-300dpi.png / pdf
- spread-bleed-300dpi.png / pdf
- spread-guide.png
- manifest.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageOps
from print_specs import (
    BLEED_MM,
    BLEED_PX,
    PRINT_DPI,
    TRIM_H_MM,
    TRIM_H_PX,
    TRIM_W_MM,
    TRIM_W_PX,
    mm_to_px,
)
SPINE_WIDTH_RE = re.compile(r"spine_width_mm\s*=\s*([0-9]+(?:\.[0-9]+)?)")


def load_panel(path: str | Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, size, Image.Resampling.LANCZOS)


def extend_bleed(img: Image.Image, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0) -> Image.Image:
    w, h = img.size
    out = Image.new("RGB", (w + left + right, h + top + bottom))
    out.paste(img, (left, top))

    if left:
        strip = img.crop((0, 0, 1, h)).resize((left, h), Image.Resampling.NEAREST)
        out.paste(strip, (0, top))
    if right:
        strip = img.crop((w - 1, 0, w, h)).resize((right, h), Image.Resampling.NEAREST)
        out.paste(strip, (left + w, top))
    if top:
        strip = out.crop((0, top, out.width, top + 1)).resize((out.width, top), Image.Resampling.NEAREST)
        out.paste(strip, (0, 0))
    if bottom:
        strip = out.crop((0, top + h - 1, out.width, top + h)).resize((out.width, bottom), Image.Resampling.NEAREST)
        out.paste(strip, (0, top + h))
    return out


def save_png_and_pdf(img: Image.Image, png_path: Path, pdf_path: Path) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path, "PNG", dpi=(PRINT_DPI, PRINT_DPI))
    img.save(pdf_path, "PDF", resolution=float(PRINT_DPI))


def make_spread_guide(spread: Image.Image, out_path: Path, spine_trim_px: int) -> None:
    guide = spread.copy()
    draw = ImageDraw.Draw(guide)
    trim_x0 = BLEED_PX
    trim_y0 = BLEED_PX
    trim_x1 = guide.width - BLEED_PX
    trim_y1 = guide.height - BLEED_PX

    back_end = trim_x0 + TRIM_W_PX
    spine_end = back_end + spine_trim_px

    guide_color = (220, 40, 40)
    fold_color = (30, 90, 180)

    draw.rectangle((trim_x0, trim_y0, trim_x1 - 1, trim_y1 - 1), outline=guide_color, width=2)
    draw.line((back_end, trim_y0, back_end, trim_y1), fill=fold_color, width=2)
    draw.line((spine_end, trim_y0, spine_end, trim_y1), fill=fold_color, width=2)
    guide.save(out_path, "PNG", dpi=(PRINT_DPI, PRINT_DPI))


def write_manifest(out_dir: Path, spine_width_mm: float, spine_trim_px: int, spread_size: tuple[int, int]) -> None:
    manifest = f"""print spec
dpi: {PRINT_DPI}
trim_mm: {TRIM_W_MM} x {TRIM_H_MM}
trim_px: {TRIM_W_PX} x {TRIM_H_PX}
bleed_mm: {BLEED_MM}
bleed_px: {BLEED_PX}
spine_mm: {spine_width_mm}
spine_px: {spine_trim_px}
spread_px: {spread_size[0]} x {spread_size[1]}
"""
    (out_dir / "manifest.txt").write_text(manifest, encoding="utf-8")


def detect_spine_width_mm(spine_data_path: Path) -> float:
    text = spine_data_path.read_text(encoding="utf-8")
    match = SPINE_WIDTH_RE.search(text)
    if not match:
        raise SystemExit(f"spine_width_mm を取得できませんでした: {spine_data_path}")
    return float(match.group(1))


def resolve_path(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def generate_print_assets(
    front_path: str | Path,
    back_path: str | Path,
    spine_path: str | Path,
    spine_width_mm: float,
    out_dir: str | Path,
) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    spine_trim_px = mm_to_px(spine_width_mm)

    front_trim = load_panel(front_path, (TRIM_W_PX, TRIM_H_PX))
    back_trim = load_panel(back_path, (TRIM_W_PX, TRIM_H_PX))
    spine_trim = load_panel(spine_path, (spine_trim_px, TRIM_H_PX))

    front_bleed = extend_bleed(front_trim, left=0, right=BLEED_PX, top=BLEED_PX, bottom=BLEED_PX)
    back_bleed = extend_bleed(back_trim, left=BLEED_PX, right=0, top=BLEED_PX, bottom=BLEED_PX)
    spine_pdf = out_dir / "spine-trim-300dpi.pdf"
    save_png_and_pdf(spine_trim, out_dir / "spine-trim-300dpi.png", spine_pdf)

    save_png_and_pdf(front_trim, out_dir / "front-trim-300dpi.png", out_dir / "front-trim-300dpi.pdf")
    save_png_and_pdf(back_trim, out_dir / "back-trim-300dpi.png", out_dir / "back-trim-300dpi.pdf")
    save_png_and_pdf(front_bleed, out_dir / "front-bleed-300dpi.png", out_dir / "front-bleed-300dpi.pdf")
    save_png_and_pdf(back_bleed, out_dir / "back-bleed-300dpi.png", out_dir / "back-bleed-300dpi.pdf")

    spread_trim = Image.new("RGB", (TRIM_W_PX * 2 + spine_trim_px, TRIM_H_PX))
    x = 0
    spread_trim.paste(back_trim, (x, 0))
    x += TRIM_W_PX
    spread_trim.paste(spine_trim, (x, 0))
    x += spine_trim_px
    spread_trim.paste(front_trim, (x, 0))

    save_png_and_pdf(spread_trim, out_dir / "spread-trim-300dpi.png", out_dir / "spread-trim-300dpi.pdf")
    spread_bleed = extend_bleed(spread_trim, left=BLEED_PX, right=BLEED_PX, top=BLEED_PX, bottom=BLEED_PX)
    save_png_and_pdf(spread_bleed, out_dir / "spread-bleed-300dpi.png", out_dir / "spread-bleed-300dpi.pdf")
    make_spread_guide(spread_bleed, out_dir / "spread-guide.png", spine_trim_px)
    write_manifest(out_dir, spine_width_mm, spine_trim_px, spread_bleed.size)

    print(f"Print assets generated: {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="A5 同人誌向けの印刷用カバーアセットを生成する")
    parser.add_argument("book_root", nargs="?", default=".", help="書籍ルート。省略時はカレントディレクトリ")
    parser.add_argument("--front", help="表紙PNGへのパス。省略時は cover/cover-book.png")
    parser.add_argument("--back", help="裏表紙PNGへのパス。省略時は cover/back-book.png")
    parser.add_argument("--spine", help="背表紙PNGへのパス。省略時は cover/spine-book.png")
    parser.add_argument("--spine-data", help="spine-data.py へのパス。省略時は cover/spine-data.py")
    parser.add_argument("--spine-width-mm", type=float, help="背幅(mm)。指定時は spine-data.py の解析を省略")
    parser.add_argument("--out-dir", help="出力先。省略時は cover/print")
    args = parser.parse_args()

    book_root = Path(args.book_root).resolve()
    cover_dir = book_root / "cover"

    front_path = resolve_path(book_root, args.front) if args.front else (cover_dir / "cover-book.png")
    back_path = resolve_path(book_root, args.back) if args.back else (cover_dir / "back-book.png")
    spine_path = resolve_path(book_root, args.spine) if args.spine else (cover_dir / "spine-book.png")
    spine_data_path = resolve_path(book_root, args.spine_data) if args.spine_data else (cover_dir / "spine-data.py")
    out_dir = resolve_path(book_root, args.out_dir) if args.out_dir else (cover_dir / "print")

    missing = [str(path) for path in (front_path, back_path, spine_path) if not path.exists()]
    if missing:
        raise SystemExit(f"必要なPNGが見つかりません:\n- " + "\n- ".join(missing))

    spine_width_mm = args.spine_width_mm
    if spine_width_mm is None:
        if not spine_data_path.exists():
            raise SystemExit(f"spine-data.py が見つかりません: {spine_data_path}")
        spine_width_mm = detect_spine_width_mm(spine_data_path)

    generate_print_assets(
        front_path=front_path,
        back_path=back_path,
        spine_path=spine_path,
        spine_width_mm=spine_width_mm,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
