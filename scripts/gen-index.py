#!/usr/bin/env python3
"""
索引自動生成スクリプト（book-engine 共通版）
scripts/index-terms.yaml に宣言した用語を全章の本文から検索し、
manuscript/index.md を再生成する。

使い方（Makefile 経由で呼ぶ。BOOK_ROOT を必ず渡すこと）:
  BOOK_ROOT=/path/to/book uv run --with "pykakasi,pyyaml" python book-engine/scripts/gen-index.py

章ディレクトリの自動検出（優先順）:
  1. manuscript/ch*/main.md （サブディレクトリ構造）
  2. manuscripts/*.md       （フラット構造）
  3. curriculum/chapters/   （カリキュラム構造）
"""

import os
import re
import sys
from pathlib import Path

try:
    import yaml
    from pykakasi import kakasi
except ImportError:
    print("依存ライブラリが不足しています:")
    print("  uv run --with 'pykakasi,pyyaml' python ...")
    sys.exit(1)

# BOOK_ROOT: 書籍リポジトリのルート（Makefile から環境変数で渡す）
ROOT = Path(os.environ.get("BOOK_ROOT", "."))
TERMS_FILE = ROOT / "scripts" / "index-terms.yaml"
SKIP_FILES = {"index.md", "colophon.md", "preface.md", "author.md", "afterword.md"}


def collect_chapter_files(root: Path) -> tuple[list[Path], Path]:
    """章ファイルのリストと index.md 出力先を返す。"""
    manuscript = root / "manuscript"
    if manuscript.exists():
        files = sorted(manuscript.rglob("main.md"), key=lambda p: p.parent.name)
        if files:
            return files, manuscript / "index.md"

    manuscripts = root / "manuscripts"
    if manuscripts.exists():
        files = sorted(
            f for f in manuscripts.iterdir()
            if f.suffix == ".md" and f.name not in SKIP_FILES
        )
        if files:
            return files, manuscripts / "index.md"

    curriculum = root / "curriculum" / "chapters"
    if curriculum.exists():
        files = sorted(
            f for f in curriculum.iterdir()
            if f.suffix == ".md" and f.name not in SKIP_FILES
        )
        if files:
            return files, curriculum.parent / "index.md"

    print("ERROR: 章ディレクトリが見つかりません（manuscript/, manuscripts/, curriculum/chapters/）")
    sys.exit(1)


chapter_files, OUTPUT = collect_chapter_files(ROOT)

chapter_texts: dict[str, str] = {}
chapter_labels: dict[str, str] = {}
for i, path in enumerate(chapter_files, start=1):
    fname = str(path.relative_to(ROOT))
    chapter_texts[fname] = path.read_text(encoding="utf-8")
    chapter_labels[fname] = f"{i}章"

if not TERMS_FILE.exists():
    print(f"ERROR: {TERMS_FILE} が見つかりません")
    sys.exit(1)

with TERMS_FILE.open(encoding="utf-8") as f:
    terms_data: list[dict] = yaml.safe_load(f) or []

kks = kakasi()


def to_hira(text: str) -> str:
    result = kks.convert(text)
    return "".join(item["hira"] or item["orig"] for item in result).lower()


def first_row(reading: str) -> str:
    c = reading[0] if reading else ""
    for row, chars in [
        ("あ行", "あいうえおぁぃぅぇぉ"),
        ("か行", "かきくけこがぎぐげご"),
        ("さ行", "さしすせそざじずぜぞ"),
        ("た行", "たちつてとだぢづでど"),
        ("な行", "なにぬねの"),
        ("は行", "はひふへほばびぶべぼぱぴぷぺぽ"),
        ("ま行", "まみむめも"),
        ("や行", "やゆよ"),
        ("ら行", "らりるれろ"),
        ("わ行", "わをん"),
    ]:
        if c in chars:
            return row
    return "英数字"


index_entries: list[dict] = []
for entry in terms_data:
    term = entry.get("term", "").strip()
    if not term:
        continue
    patterns: list[str] = entry.get("patterns", [term])
    reading: str = entry.get("reading") or to_hira(term)
    xref: str = entry.get("xref", "")

    matched_chapters: list[str] = []
    for fname, text in chapter_texts.items():
        for pat in patterns:
            try:
                if re.search(pat, text):
                    matched_chapters.append(chapter_labels[fname])
                    break
            except re.error:
                if pat in text:
                    matched_chapters.append(chapter_labels[fname])
                    break

    def sort_key(lbl: str) -> int:
        m = re.match(r"(\d+)章", lbl)
        return int(m.group(1)) if m else -1

    matched_chapters = sorted(set(matched_chapters), key=sort_key)
    index_entries.append({"term": term, "reading": reading, "xref": xref, "chapters": matched_chapters})

sections: dict[str, list] = {}
for e in index_entries:
    row = first_row(e["reading"])
    sections.setdefault(row, []).append(e)

ROW_ORDER = ["あ行", "か行", "さ行", "た行", "な行", "は行", "ま行", "や行", "ら行", "わ行", "英数字"]
for row in sections:
    sections[row].sort(key=lambda e: e["reading"])

lines = ["# 索引\n"]
total = 0
zero_hit = []

for row in ROW_ORDER:
    if row not in sections:
        continue
    lines.append(f"\n## {row}\n")
    lines.append("| 用語 | 参照章 |")
    lines.append("|------|--------|")
    for e in sections[row]:
        if e["xref"]:
            lines.append(f"| {e['term']} {e['xref']} | — |")
            total += 1
        elif e["chapters"]:
            lines.append(f"| {e['term']} | {'、'.join(e['chapters'])} |")
            total += 1
        else:
            zero_hit.append(e["term"])

OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"生成完了: {OUTPUT}  ({total}エントリ、{len(chapter_texts)}章)")
if zero_hit:
    print(f"ヒットなし: {', '.join(zero_hit)}")
