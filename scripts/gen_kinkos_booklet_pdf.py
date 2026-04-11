"""
キンコーズの A5 中綴じ向けに、front / body / back / 必要な空白をまとめた PDF を生成する。

- Vivliostyle 本: front + body + blanks + back
- Re:VIEW 本: coverimage が本文 PDF に含まれている前提なら body + blanks + back
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("依存ライブラリが不足しています: uv run --with 'pyyaml,pillow' python ...")
    raise SystemExit(1)

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cover"))
from print_specs import PRINT_DPI, TRIM_H_PX, TRIM_W_PX


def detect_format(book_root: Path) -> str:
    return "review" if (book_root / "book" / "config.yml").exists() else "vivliostyle"


def pdf_pages(pdf_path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise SystemExit(f"ページ数を取得できませんでした: {pdf_path}")


def load_book_yaml(book_root: Path) -> dict:
    path = book_root / "book.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def review_pdf_has_coverimage(book_root: Path) -> bool:
    config_path = book_root / "book" / "config.yml"
    if not config_path.exists():
        return False
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if data.get("coverimage"):
        return True
    pdfmaker = data.get("pdfmaker") or {}
    return bool(pdfmaker.get("coverimage"))


def png_to_pdf(png_path: Path, pdf_path: Path) -> None:
    img = Image.open(png_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=float(PRINT_DPI))


def blank_pdf(pdf_path: Path) -> None:
    img = Image.new("RGB", (TRIM_W_PX, TRIM_H_PX), (255, 255, 255))
    img.save(pdf_path, "PDF", resolution=float(PRINT_DPI))


def resolve_cover_pdf(pdf_path: Path, png_path: Path, fallback_path: Path) -> Path:
    if pdf_path.exists():
        return pdf_path
    if png_path.exists():
        png_to_pdf(png_path, fallback_path)
        return fallback_path
    raise SystemExit(f"必要な cover アセットが見つかりません: {pdf_path} / {png_path}")


def pick_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def write_manifest(
    manifest_path: Path,
    *,
    format_name: str,
    body_pages: int,
    include_front: bool,
    include_back: bool,
    blank_pages: int,
    total_pages: int,
) -> None:
    text = f"""kinkos booklet packet
format: {format_name}
body_pages: {body_pages}
include_front: {include_front}
include_back: {include_back}
blank_pages_before_back: {blank_pages}
total_pages: {total_pages}
paper_size: A5
dpi: {PRINT_DPI}
"""
    manifest_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="キンコーズ A5 中綴じ向け PDF を生成する")
    parser.add_argument("book_root", nargs="?", default=".", help="書籍ルート")
    parser.add_argument("--out", help="出力 PDF。省略時は dist/book-kinkos-booklet.pdf")
    args = parser.parse_args()

    book_root = Path(args.book_root).resolve()
    format_name = detect_format(book_root)
    book_yaml = load_book_yaml(book_root)
    print_config = book_yaml.get("print") or {}
    binding = print_config.get("binding", "wireless")
    if binding != "saddle":
        raise SystemExit(
            "キンコーズ手刷り向け packet は中綴じ前提です。book.yaml の print.binding を 'saddle' にしてください。"
        )

    if format_name == "review":
        body_pdf = book_root / "book" / "book.pdf"
        include_front = not review_pdf_has_coverimage(book_root)
    else:
        body_pdf = book_root / "dist" / "book-digital.pdf"
        include_front = True

    if not body_pdf.exists():
        raise SystemExit(f"本文 PDF が見つかりません: {body_pdf}")

    out_pdf = Path(args.out).resolve() if args.out else (book_root / "dist" / "book-kinkos-booklet.pdf")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = out_pdf.with_suffix(".manifest.txt")

    cover_dir = book_root / "cover"
    front_pdf = cover_dir / "print" / "front-trim-300dpi.pdf"
    back_pdf = cover_dir / "print" / "back-trim-300dpi.pdf"
    front_png = pick_existing([cover_dir / "cover-book.png"])
    back_png = pick_existing([cover_dir / "back-book.png", cover_dir / "back-cover.png"])
    if front_png is None or back_png is None:
        raise SystemExit("front または back の PNG が見つかりません")

    with tempfile.TemporaryDirectory(prefix="kinkos-", dir=str(out_pdf.parent)) as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        front_fallback_pdf = tmp_dir / "front-from-png.pdf"
        back_fallback_pdf = tmp_dir / "back-from-png.pdf"
        front_part = resolve_cover_pdf(front_pdf, front_png, front_fallback_pdf)
        back_part = resolve_cover_pdf(back_pdf, back_png, back_fallback_pdf)

        parts: list[Path] = []
        if include_front:
            parts.append(front_part)
        parts.append(body_pdf)

        body_pages = pdf_pages(body_pdf)
        total_without_blanks = body_pages + (1 if include_front else 0) + 1
        blank_pages = (-total_without_blanks) % 4

        for idx in range(blank_pages):
            blank_part = tmp_dir / f"blank-{idx + 1}.pdf"
            blank_pdf(blank_part)
            parts.append(blank_part)

        parts.append(back_part)
        total_pages = total_without_blanks + blank_pages

        subprocess.run(["pdfunite", *(str(p) for p in parts), str(out_pdf)], check=True)

    write_manifest(
        manifest_path,
        format_name=format_name,
        body_pages=body_pages,
        include_front=include_front,
        include_back=True,
        blank_pages=blank_pages,
        total_pages=total_pages,
    )
    print(f"Kinko's booklet PDF generated: {out_pdf}")
    print(f"Kinko's booklet manifest: {manifest_path}")


if __name__ == "__main__":
    main()
