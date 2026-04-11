"""
PDFを2ページ見開きでスクリーンショットを生成する。
出力: dist/_preview/ に spread-01-02.png, spread-03-04.png ... の形式で保存。
"""
import sys
from pathlib import Path
import fitz  # pymupdf
from PIL import Image
import io

DPI = 150


def page_to_pil(doc, idx, dpi=DPI):
    if 0 <= idx < doc.page_count:
        pix = doc[idx].get_pixmap(dpi=dpi)
        return Image.open(io.BytesIO(pix.tobytes("png")))
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: pdf-spread-screenshots.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else pdf_path.parent / "_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"📖 {pdf_path.name}: {doc.page_count}P")

    gap = 4
    bg_color = (40, 40, 40)

    for i in range(0, doc.page_count, 2):
        left_img = page_to_pil(doc, i)
        right_img = page_to_pil(doc, i + 1)

        imgs = [img for img in [left_img, right_img] if img]
        if not imgs:
            continue

        h = max(img.height for img in imgs)
        w = sum(img.width for img in imgs) + gap

        spread = Image.new("RGB", (w, h), bg_color)
        x = 0
        if left_img:
            spread.paste(left_img, (x, 0))
            x += left_img.width + gap
        if right_img:
            spread.paste(right_img, (x, 0))

        fname = f"spread-{i+1:02d}-{i+2:02d}.png"
        spread.save(out_dir / fname)
        print(f"  {fname}")

    doc.close()
    print(f"✅ {out_dir}/")


if __name__ == "__main__":
    main()
