#!/usr/bin/env python3
"""
索引自動生成スクリプト（book-engine 共通版）
scripts/index-terms.yaml に宣言した用語を全章の本文から検索し、
索引ファイルを再生成する。

使い方（Makefile 経由で呼ぶ。BOOK_ROOT を必ず渡すこと）:
  BOOK_ROOT=/path/to/book uv run --with "pykakasi,pyyaml" python book-engine/scripts/gen-index.py

章ファイルの自動検出（優先順）:
  1. book/ch*.re            （Re:VIEW 形式） → book/index_ref.md に出力
  2. manuscript/ch*/main.md （Vivliostyle / サブディレクトリ構造）
  3. manuscripts/*.md       （フラット構造）
  4. curriculum/chapters/   （カリキュラム構造）
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


def strip_review_markup(text: str) -> str:
    """Re:VIEW マークアップを除去してプレーンテキストを返す（索引検索用）。"""
    # コードブロック除去（//list, //cmd, //terminal, //emlist 等）
    text = re.sub(r"^//(?:list|cmd|terminal|source|emlist|listnum|caution|note|warning|info)\b[^\n]*\n.*?^//\}", "",
                  text, flags=re.DOTALL | re.MULTILINE)
    # インライン索引マーカー @<hidx>{用語} はテキストとして保持
    text = re.sub(r"@<hidx>\{([^}]*)\}", r"\1", text)
    # インラインコード除去
    text = re.sub(r"@<code>\{[^}]*\}", "", text)
    # その他のインラインコマンド（@<b>{...} 等）: テキスト部分を保持
    text = re.sub(r"@<\w+>\{([^}]*)\}", r"\1", text)
    # ブロックコマンド行を除去（//image, //footnote 等）
    text = re.sub(r"^//\w+[^\n]*$", "", text, flags=re.MULTILINE)
    # 見出し行の記号を除去（=, ==, === 等）
    text = re.sub(r"^={1,6}(?:\[.*?\])?\s*", "", text, flags=re.MULTILINE)
    return text


def collect_chapter_files(root: Path) -> tuple[list[Path], Path, str]:
    """章ファイルのリストと index 出力先、フォーマット名を返す。"""
    # 1. Re:VIEW 形式: book/ch*.re
    review_dir = root / "book"
    if review_dir.exists():
        files = sorted(
            f for f in review_dir.iterdir()
            if f.suffix == ".re" and re.match(r"ch\d+", f.stem)
        )
        if files:
            return files, review_dir / "index_ref.md", "review"

    # 2. Vivliostyle / サブディレクトリ構造: manuscript/ch*/main.md
    manuscript = root / "manuscript"
    if manuscript.exists():
        files = sorted(manuscript.rglob("main.md"), key=lambda p: p.parent.name)
        if files:
            return files, manuscript / "index.md", "vivliostyle"

    # 3. フラット構造: manuscripts/*.md
    manuscripts = root / "manuscripts"
    if manuscripts.exists():
        files = sorted(
            f for f in manuscripts.iterdir()
            if f.suffix == ".md" and f.name not in SKIP_FILES
        )
        if files:
            return files, manuscripts / "index.md", "vivliostyle"

    # 4. カリキュラム構造: curriculum/chapters/
    curriculum = root / "curriculum" / "chapters"
    if curriculum.exists():
        files = sorted(
            f for f in curriculum.iterdir()
            if f.suffix == ".md" and f.name not in SKIP_FILES
        )
        if files:
            return files, curriculum.parent / "index.md", "vivliostyle"

    print("ERROR: 章ファイルが見つかりません（book/ch*.re, manuscript/, manuscripts/, curriculum/chapters/）")
    sys.exit(1)


chapter_files, OUTPUT, FORMAT = collect_chapter_files(ROOT)

chapter_texts: dict[str, str] = {}
chapter_labels: dict[str, str] = {}
for i, path in enumerate(chapter_files, start=1):
    fname = str(path.relative_to(ROOT))
    raw = path.read_text(encoding="utf-8")
    # Re:VIEW はマークアップを除去してから検索する
    chapter_texts[fname] = strip_review_markup(raw) if FORMAT == "review" else raw
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

if FORMAT == "review":
    lines = [
        "# 索引用語 参照一覧（参考）\n",
        "<!-- このファイルは gen-index.py が自動生成する参照用ファイルです。\n",
        "     Re:VIEW の実際の索引は各 .re ファイル内の @<hidx>{用語} マーカーで管理します。 -->\n",
    ]
else:
    lines = ["---\nclass: index\n---\n\n# 索引\n"]
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
if FORMAT == "review":
    print(f"生成完了: {OUTPUT}  ({total}エントリ、{len(chapter_texts)}章) ※参照用")
    print("  Re:VIEW の索引は各 .re ファイルの @<hidx>{用語} で管理してください")
else:
    print(f"生成完了: {OUTPUT}  ({total}エントリ、{len(chapter_texts)}章)")
if zero_hit:
    print(f"ヒットなし: {', '.join(zero_hit)}")

# ── 未登録候補の提案 ──────────────────────────────────────────
# 本文頻出語のうち index-terms.yaml に未登録のものを出力する。
# 索引の漏れ検出と品質向上のために使う。

from collections import Counter

# 登録済み用語セット（term と patterns の両方）
registered: set[str] = set()
for entry in terms_data:
    registered.add(entry.get("term", ""))
    for p in entry.get("patterns", []):
        registered.add(p)

# 全章テキストを結合（chapter_texts は既にマークアップ除去済み）
combined = "\n".join(chapter_texts.values())
if FORMAT == "review":
    # Re:VIEW 残余ノイズを追加除去
    combined = re.sub(r"^//.+$", "", combined, flags=re.MULTILINE)
else:
    # Markdown 記法行を除去
    combined = re.sub(r"```[\s\S]*?```", "", combined)
    combined = re.sub(r"`[^`\n]+`", "", combined)
    combined = re.sub(r"^#{1,6}[^\n]*$", "", combined, flags=re.MULTILINE)
    combined = re.sub(r"^\|[^\n]*$", "", combined, flags=re.MULTILINE)
    combined = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", combined)

# 英数字語（2文字以上）とカタカナ語（3文字以上）を抽出
candidates = re.findall(r"[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z]+)*|[ァ-ヶー]{3,}", combined)
counter = Counter(candidates)

# 未登録・3回以上・ノイズ除外
NOISE = {
    # Markdownの残滓・一般的すぎる語
    "md", "png", "pdf", "css", "js", "sh", "py", "yaml", "txt",
    "true", "false", "null", "None", "EOF",
    "the", "and", "or", "for", "with", "from", "import", "return",
    "path", "file", "str", "int", "list", "dict", "set",
    "assets", "scripts", "chapter", "image", "main",
}
suggestions = [
    (term, count)
    for term, count in counter.most_common(50)
    if term not in registered
    and term.lower() not in NOISE
    and count >= 3
    and len(term) >= 2
]

if suggestions:
    print(f"\n📋 索引未登録の頻出語（index-terms.yaml への追加を検討）:")
    for term, count in suggestions:
        print(f"   {count}回: {term}")
