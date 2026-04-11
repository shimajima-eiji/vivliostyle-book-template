"""
book.css 生成スクリプト
book.yaml の title と css.chapter_image フラグを読み取り、
book.css.template から theme/book.css を生成する。

使い方（book-template から直接呼ばない。Makefile 経由で使う）:
  BOOK_ROOT=/path/to/book python book-template/scripts/gen-css.py
"""

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("依存ライブラリが不足しています: uv run --with pyyaml python ...")
    sys.exit(1)

CHAPTER_IMAGE_CSS = """\
/* 章扉画像: 左ページに全面配置（見開きで右ページの章タイトルと対になる） */
@page chapter-image {
  margin: 0;
  @top-left   { content: none; }
  @top-right  { content: none; }
  @bottom-left  { content: none; }
  @bottom-right { content: none; }
}

.chapter-image {
  page: chapter-image;
  break-before: {{CHAPTER_IMAGE_BREAK_BEFORE}};
  display: block;
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  object-fit: contain;
}
"""

INDEX_COMPACT_CSS = """\
/* キンコーズ中綴じ: 索引を少し詰めて空きページを減らす */
.index {
  font-size: 8.8pt;
}

.index h2 {
  margin-top: 1rem;
  margin-bottom: 0.45rem;
}

.index table {
  font-size: 8pt;
  line-height: 1.45;
}

.index th,
.index td {
  padding-top: 0.12em;
  padding-bottom: 0.12em;
}
"""

def main():
    book_root = Path(os.environ.get("BOOK_ROOT", "."))
    book_yaml = book_root / "book.yaml"

    if not book_yaml.exists():
        print(f"ERROR: {book_yaml} が見つかりません")
        sys.exit(1)

    with book_yaml.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    title = config.get("title", "")
    chapter_image = config.get("css", {}).get("chapter_image", True)
    print_cfg = config.get("print", {}) or {}
    is_kinkos_saddle = print_cfg.get("printer") == "kinkos" and print_cfg.get("binding") == "saddle"
    h1_break_before = "page" if is_kinkos_saddle else "right"
    chapter_image_break_before = "page" if is_kinkos_saddle else "left"

    engine_dir = Path(__file__).parent.parent
    template = (engine_dir / "theme" / "book.css.template").read_text(encoding="utf-8")

    css = template.replace("{{BOOK_TITLE}}", title)
    css = css.replace("{{H1_BREAK_BEFORE}}", h1_break_before)
    if chapter_image:
        chapter_image_css = CHAPTER_IMAGE_CSS.replace("{{CHAPTER_IMAGE_BREAK_BEFORE}}", chapter_image_break_before)
    else:
        chapter_image_css = ""
    css = css.replace("{{CHAPTER_IMAGE_CSS}}", chapter_image_css)
    css = css.replace("{{INDEX_COMPACT_CSS}}", INDEX_COMPACT_CSS if is_kinkos_saddle else "")

    out = book_root / "theme" / "book.css"
    out.parent.mkdir(exist_ok=True)
    out.write_text(css, encoding="utf-8")
    print(f"生成: {out}  (chapter_image={chapter_image})")

if __name__ == "__main__":
    main()
