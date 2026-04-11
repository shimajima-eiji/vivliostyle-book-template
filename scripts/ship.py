"""
ship.py — 書籍のビルド・dist組立フレームワーク。

各本のMakefileから呼ばれる。Re:VIEW / Vivliostyle の差異を吸収し、
dist/{SIZE}/ にディレクトリ構成で成果物を配置する。

Usage:
    python ship.py <book_root> [--sizes a5,b5] [--skip-build]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# --- 用紙サイズ定義 ---
PAPER_SPECS = {
    "a5": {"mm": (148, 210), "review_paper": "a5"},
    "b5": {"mm": (182, 257), "review_paper": "b5"},
    "a4": {"mm": (210, 297), "review_paper": "a4"},
    "a6": {"mm": (105, 148), "review_paper": "a6"},
}


def detect_format(book_root: Path) -> str:
    if (book_root / "book" / "config.yml").exists():
        return "review"
    return "vivliostyle"


def read_title(book_root: Path) -> str:
    yaml_path = book_root / "book.yaml"
    if yaml_path.exists():
        m = re.search(r"title:\s*[\"'](.*?)[\"']", yaml_path.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "book"


def read_binding(book_root: Path) -> str:
    yaml_path = book_root / "book.yaml"
    if yaml_path.exists():
        m = re.search(r"binding:\s*[\"']?(\w+)", yaml_path.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "wireless"


def make_blank_pdf(output_path: Path, size_key: str):
    """指定サイズの白紙1ページPDFを生成する"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    dims = {
        "a5": (148 * mm, 210 * mm),
        "b5": (182 * mm, 257 * mm),
        "a4": (210 * mm, 297 * mm),
        "a6": (105 * mm, 148 * mm),
    }
    c = canvas.Canvas(str(output_path), pagesize=dims.get(size_key, dims["a5"]))
    c.showPage()
    c.save()


def get_body_page_count(pdf_path: Path) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    count = doc.page_count
    doc.close()
    return count


class BookProject:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.fmt = detect_format(self.root)
        self.title = read_title(self.root)
        self.binding = read_binding(self.root)
        self.engine_dir = Path(__file__).parent.parent.resolve()

    def ship(self, sizes: list[str], skip_build: bool = False):
        """指定サイズすべてをビルド→dist配置する"""
        print(f"📦 {self.title} ({self.fmt})")

        for size in sizes:
            if size not in PAPER_SPECS:
                print(f"  ⚠️ 未対応の用紙サイズ: {size}")
                continue
            self._ship_size(size, skip_build)

        # 複数サイズをビルドした場合、最初のサイズでbook.pdfを復元
        if len(sizes) > 1 and not skip_build:
            base = sizes[0]
            print(f"  {base.upper()}版のbook.pdfを復元中...")
            self._build(base)

    def _ship_size(self, size: str, skip_build: bool):
        print(f"\n  === {size.upper()} ===")
        out_dir = self.root / "dist" / size.upper()
        bind_dir = out_dir / "製本版"
        bind_dir.mkdir(parents=True, exist_ok=True)

        # ビルド
        if not skip_build:
            self._build(size)

        # ソースPDF
        body_pdf = self._get_body_pdf()
        if not body_pdf.exists():
            print(f"  ❌ 本文PDFが見つかりません: {body_pdf}")
            return

        cover_dir = self._get_cover_dir(size)
        # cover/print-{size} がなければ _fixed/ の素材から自動生成
        if cover_dir is None and size != "a5":
            cover_dir = self._generate_cover_print(size)
        front_pdf = cover_dir / "front-trim-300dpi.pdf" if cover_dir else None
        back_pdf = cover_dir / "back-trim-300dpi.pdf" if cover_dir else None

        has_covers = front_pdf and front_pdf.exists() and back_pdf and back_pdf.exists()

        # 製本版: 本文・表紙・裏表紙
        shutil.copy2(body_pdf, bind_dir / "本文.pdf")
        print(f"  製本版/本文.pdf OK")

        if has_covers:
            shutil.copy2(front_pdf, bind_dir / "表紙.pdf")
            shutil.copy2(back_pdf, bind_dir / "裏表紙.pdf")
            print(f"  製本版/表紙.pdf OK")
            print(f"  製本版/裏表紙.pdf OK")

            # 画像ファイル（PNG）も配置
            for name, src_name in [("表紙", "front-trim-300dpi.png"), ("裏表紙", "back-trim-300dpi.png"), ("背表紙", "spine-trim-300dpi.png")]:
                src = cover_dir / src_name
                if src.exists():
                    shutil.copy2(src, bind_dir / f"{name}.png")
                    print(f"  製本版/{name}.png OK")

            # 電子版・ネットプリント（format別）
            if self.fmt == "review":
                # Re:VIEW: book.pdfはcoverimageで表紙込み → 本文+裏表紙で電子版
                subprocess.run(
                    ["qpdf", "--empty", "--pages", str(body_pdf), str(back_pdf), "--",
                     str(out_dir / "電子版.pdf")],
                    check=True, capture_output=True,
                )
                print(f"  電子版.pdf OK")
                # ネットプリント: 表紙+白紙+本文(P2〜)+白紙+裏表紙（P1は表紙重複なのでスキップ）
                self._make_netprint(size, front_pdf, body_pdf, back_pdf, bind_dir / "ネットプリント.pdf", skip_first_page=True)
            else:
                # Vivliostyle: book-digital.pdfは表紙なし → 表紙+本文+裏表紙で電子版
                subprocess.run(
                    ["qpdf", "--empty", "--pages", str(front_pdf), str(body_pdf), str(back_pdf), "--",
                     str(out_dir / "電子版.pdf")],
                    check=True, capture_output=True,
                )
                print(f"  電子版.pdf OK")
                # ネットプリント: 表紙+白紙+本文(全ページ)+白紙+裏表紙
                self._make_netprint(size, front_pdf, body_pdf, back_pdf, bind_dir / "ネットプリント.pdf", skip_first_page=False)
        else:
            # 表紙なし
            shutil.copy2(body_pdf, out_dir / "電子版.pdf")
            print(f"  電子版.pdf OK（表紙なし）")

        print(f"  ---")
        for p in sorted(out_dir.rglob("*.pdf")):
            print(f"  {p.relative_to(out_dir)}")

    def _make_netprint(self, size: str, front_pdf: Path, body_pdf: Path, back_pdf: Path, out_path: Path, skip_first_page: bool = False):
        """表紙+白紙+本文+白紙+裏表紙のネットプリントPDFを生成する"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            blank_path = Path(tmp.name)
        try:
            make_blank_pdf(blank_path, size)
            body_pages = get_body_page_count(body_pdf)
            body_range = f"2-{body_pages}" if skip_first_page else f"1-{body_pages}"
            subprocess.run(
                ["qpdf", "--empty", "--pages",
                 str(front_pdf),
                 str(blank_path),
                 str(body_pdf), body_range,
                 str(blank_path),
                 str(back_pdf),
                 "--", str(out_path)],
                check=True, capture_output=True,
            )
            print(f"  製本版/ネットプリント.pdf OK（白紙挿入済み）")
        finally:
            blank_path.unlink(missing_ok=True)

    def _build(self, size: str):
        if self.fmt == "review":
            self._build_review(size)
        else:
            self._build_vivliostyle(size)

    def _build_review(self, size: str):
        config_path = self.root / "book" / "config.yml"
        config_text = config_path.read_text(encoding="utf-8")

        # 用紙サイズを一時変更
        new_text = config_text
        if size != "a5":
            new_text = new_text.replace("paper=a5", f"paper={size}")
            cover_b5 = f"cover-{size}.pdf"
            if (self.root / "book" / "images" / cover_b5).exists():
                new_text = new_text.replace("coverimage: cover-a5.pdf", f"coverimage: {cover_b5}")

        if new_text != config_text:
            config_path.write_text(new_text, encoding="utf-8")

        try:
            env = os.environ.copy()
            env["PATH"] = f"/Library/TeX/texbin:{env.get('PATH', '')}"
            result = subprocess.run(
                ["bundle", "exec", "review-pdfmaker", "config.yml"],
                cwd=self.root / "book",
                env=env,
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"  ❌ Re:VIEWビルドエラー:")
                print(result.stderr[-500:] if result.stderr else "")
                return
            print(f"  ✅ Re:VIEWビルド完了 ({size.upper()})")
        finally:
            # config.yml を復元
            if new_text != config_text:
                config_path.write_text(config_text, encoding="utf-8")

    def _build_vivliostyle(self, size: str):
        # CSSの用紙サイズを一時変更
        css_path = self.root / "theme" / "book.css"
        css_text = css_path.read_text(encoding="utf-8") if css_path.exists() else None

        if css_text and size != "a5":
            size_map = {"b5": "B5", "a4": "A4", "a6": "A6"}
            target_size = size_map.get(size)
            if not target_size:
                print(f"  ⚠️ Vivliostyle {size.upper()}版は未対応です")
                return
            new_css = css_text.replace("size: A5;", f"size: {target_size};")
            css_path.write_text(new_css, encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "@vivliostyle/cli", "build"],
                cwd=self.root, capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"  ❌ Vivliostyleビルドエラー:")
                print(result.stderr[-500:] if result.stderr else "")
                return
            print(f"  ✅ Vivliostyleビルド完了 ({size.upper()})")
        finally:
            # CSS を復元
            if css_text and size != "a5":
                css_path.write_text(css_text, encoding="utf-8")

    def _get_body_pdf(self) -> Path:
        if self.fmt == "review":
            return self.root / "book" / "book.pdf"
        return self.root / "dist" / "book-digital.pdf"

    def _get_cover_dir(self, size: str) -> Path | None:
        if size == "a5":
            d = self.root / "cover" / "print"
        else:
            d = self.root / "cover" / f"print-{size}"
        return d if d.exists() else None

    def _generate_cover_print(self, size: str) -> Path | None:
        """_fixed/ のサイズ別素材から cover/print-{size} を生成する"""
        fixed = self.root / "cover" / "_fixed"
        front = fixed / f"front-{size}.png"
        back = fixed / f"back-{size}.png"
        spine = self.root / "cover" / "spine-book.png"

        if not front.exists() or not back.exists():
            print(f"  ⚠️ {size.upper()}版表紙素材がありません: _fixed/front-{size}.png, back-{size}.png")
            print(f"      make cover-b5-prep で生成してください")
            return None

        out_dir = self.root / "cover" / f"print-{size}"
        env = os.environ.copy()
        env["PAPER_SIZE"] = size
        gen_script = self.engine_dir / "cover" / "gen_print_cover_assets.py"

        args = ["uv", "run", "--with", "pillow", "python3", str(gen_script),
                "--front", str(front), "--back", str(back),
                "--spine", str(spine), "--out", str(out_dir)]
        result = subprocess.run(args, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ❌ {size.upper()}版表紙生成エラー: {result.stderr[-200:]}")
            return None
        print(f"  ✅ {size.upper()}版表紙生成完了")
        return out_dir


def main():
    parser = argparse.ArgumentParser(description="書籍ビルド・dist組立フレームワーク")
    parser.add_argument("book_root", nargs="?", default=".", help="書籍ルートディレクトリ")
    parser.add_argument("--sizes", default="b5,a5", help="生成する用紙サイズ（カンマ区切り、先頭がベース）")
    parser.add_argument("--skip-build", action="store_true", help="ビルドをスキップしてdist組立のみ")
    args = parser.parse_args()

    book_root = Path(args.book_root).resolve()
    sizes = [s.strip().lower() for s in args.sizes.split(",")]

    project = BookProject(book_root)
    project.ship(sizes, skip_build=args.skip_build)


if __name__ == "__main__":
    main()
