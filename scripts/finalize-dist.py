import os
import yaml
import subprocess
import shutil
import re
from pathlib import Path

def convert_to_grayscale(input_pdf: Path, output_pdf: Path):
    """Ghostscript を使用して PDF をグレースケールに変換する (超高速)"""
    gs_path = "/opt/homebrew/bin/gs"
    if not os.path.exists(gs_path):
        gs_path = "gs" # fallback to PATH

    cmd = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-sColorConversionStrategy=Gray",
        "-dProcessColorModel=/DeviceGray",
        "-dCompatibilityLevel=1.4",
        "-dNOPAUSE", "-dBATCH",
        f"-sOutputFile={output_pdf}",
        str(input_pdf)
    ]
    print(f"  🌚 Converting to grayscale: {output_pdf.name}...")
    subprocess.run(cmd, check=True, capture_output=True)

def add_blank_pages_if_needed(input_pdf: Path, output_pdf: Path, binding):
    """中綴じの場合、ページ数を4の倍数に調整"""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("  ⚠️ pypdf not installed, skipping page adjustment")
        shutil.copy2(input_pdf, output_pdf)
        return

    reader = PdfReader(input_pdf)
    num_pages = len(reader.pages)
    print(f"  📄 Body PDF has {num_pages} pages")

    if binding == "saddle" and num_pages % 4 != 0:
        pages_to_add = 4 - (num_pages % 4)
        print(f"  ➕ Adding {pages_to_add} blank pages for saddle binding")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # 空白ページ追加 (A5サイズ)
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A5
            temp_blank = output_pdf.parent / "temp_blank.pdf"
            for _ in range(pages_to_add):
                c = canvas.Canvas(str(temp_blank), pagesize=A5)
                c.showPage()
                c.save()
                blank_reader = PdfReader(str(temp_blank))
                writer.add_page(blank_reader.pages[0])
            temp_blank.unlink(missing_ok=True)
        except ImportError:
            print("  ⚠️ reportlab not installed, cannot add blank pages")
            writer = PdfReader(input_pdf)  # コピー

        writer.write(output_pdf)
    else:
        shutil.copy2(input_pdf, output_pdf)

def detect_format(book_path: Path) -> str:
    """Re:VIEW か Vivliostyle かを判定する"""
    if (book_path / "book" / "config.yml").exists():
        return "review"
    return "vivliostyle"


def detect_blank_pages(pdf_path: Path) -> list[int]:
    """空白ページ（テキストも画像もないページ）を検出する"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    reader = PdfReader(pdf_path)
    blanks = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        has_images = len(page.get("/Resources", {}).get("/XObject", {}) or {}) > 0
        if not text.strip() and not has_images:
            blanks.append(i + 1)
    return blanks


def finalize_book_dist(book_path: Path, no_gray: bool = False):
    book_id = book_path.name
    print(f"\n📦 Finalizing Distribution: {book_id}")

    # Re:VIEW形式の場合は案内を出して終了
    fmt = detect_format(book_path)
    if fmt == "review":
        print(f"  ℹ️  Re:VIEW形式です。表紙・裏表紙はconfig.ymlで管理されます。")
        print(f"  ℹ️  ビルド: cd book && bundle exec review-pdfmaker config.yml")
        print(f"  ℹ️  配布:  make ship （book.pdf をそのまま dist/ に配置します）")
        # 遊び紙（空白ページ）検出
        book_pdf = book_path / "book" / "book.pdf"
        if book_pdf.exists():
            blanks = detect_blank_pages(book_pdf)
            if blanks:
                print(f"  ⚠️  空白ページを検出: {blanks}")
                print(f"      遊び紙が不要なら config.yml の titlepage/backcover 設定を確認してください。")
        return

    dist_dir = book_path / "dist"
    cover_dir = book_path / "cover"

    # 1. Get proper title and binding from book.yaml first
    yaml_path = book_path / "book.yaml"
    title = "book"
    binding = "wireless"  # default
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            y = f.read()
            m = re.search(r'title:\s*["\']?(.*?)["\']?\s*$', y, re.M)
            if m:
                title = m.group(1).replace("/", "_").replace(" ", "_").replace(":", "_")
            m2 = re.search(r'binding:\s*["\']?(.*?)["\']?\s*$', y, re.M)
            if m2:
                binding = m2.group(1)

    # 2. Clean existing finalized distribution PDFs (starting with title_ or book_)
    for p in dist_dir.glob("*.pdf"):
        if p.name.startswith(title) or p.name.startswith("book-print"):
            p.unlink()
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Source paths
    front_pdf = cover_dir / "print" / "front-trim-300dpi.pdf"
    back_pdf = cover_dir / "print" / "back-trim-300dpi.pdf"
    
    # Base Color Body PDF
    color_body = dist_dir / "book-digital.pdf"
    if not color_body.exists():
        color_body = book_path / "book" / "book.pdf" # Re:VIEW fallback

    if not color_body.exists():
        print(f"  ❌ Body PDF not found for {book_id}")
        return

    # 2. Adjust page count for binding
    adjusted_color_body = dist_dir / "book-digital-adjusted.pdf"
    add_blank_pages_if_needed(color_body, adjusted_color_body, binding)

    # 3. Create Grayscale Body via Ghostscript (if not no_gray)
    if not no_gray:
        gray_body = dist_dir / "book-print-gray.pdf"
        try:
            convert_to_grayscale(adjusted_color_body, gray_body)
        except Exception as e:
            print(f"  ⚠️ Grayscale conversion failed, using color: {e}")
            shutil.copy2(adjusted_color_body, gray_body)
    else:
        gray_body = None

    # Destinations
    out_front = dist_dir / f"{title}_表紙.pdf"
    out_back = dist_dir / f"{title}_裏表紙.pdf"
    out_body_color = dist_dir / f"{title}_本文のみ_カラー.pdf"
    out_body_gray = dist_dir / f"{title}_本文のみ_白黒.pdf"
    out_full_digital = dist_dir / f"{title}_電子版_カラー.pdf"
    out_full_print = dist_dir / f"{title}_印刷用_本文白黒.pdf"

    # Check components
    if not all([front_pdf.exists(), back_pdf.exists()]):
        print(f"  ❌ Cover components missing.")
        return

    # Copy individual parts
    shutil.copy2(front_pdf, out_front)
    shutil.copy2(back_pdf, out_back)
    shutil.copy2(adjusted_color_body, out_body_color)
    if not no_gray:
        shutil.copy2(gray_body, out_body_gray)

    # 4. Merge PDFs
    def merge_pdf(f, b, bk, out, label):
        cmd = ["qpdf", "--empty", "--pages", str(f), str(b), str(bk), "--", str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  ✅ {label}: {out.name}")

    try:
        # Merge Digital (All Color)
        merge_pdf(front_pdf, adjusted_color_body, back_pdf, out_full_digital, "Merged Digital")
        # Merge Print (Cover Color, Body Gray) - only if not no_gray
        if not no_gray:
            merge_pdf(front_pdf, gray_body, back_pdf, out_full_print, "Merged Print")
    except Exception as e:
        print(f"  ❌ Failed to merge PDF: {e}")

if __name__ == "__main__":
    import sys
    root = Path("/Users/nomuraya/workspace-ai/nomuraya-books")
    
    # --no-gray オプションを処理
    no_gray = '--no-gray' in sys.argv
    if no_gray:
        sys.argv.remove('--no-gray')
    
    # 引数があればそれだけを処理、なければ全件
    if len(sys.argv) > 1:
        target_name = sys.argv[1]
        target_path = Path(target_name)
        if not target_path.is_absolute():
            target_path = (root / target_name).resolve()
        
        if target_path.exists():
            finalize_book_dist(target_path, no_gray)
        else:
            print(f"❌ Target not found: {target_path}")
    else:
        books = [
            "teaching-ai-to-non-engineers",
            "ai-writing-guide",
            "freelance-contract-os",
            "gijutusyotenn-gennkou"
        ]
        for b in books:
            if (root / b).exists():
                finalize_book_dist(root / b, no_gray)
