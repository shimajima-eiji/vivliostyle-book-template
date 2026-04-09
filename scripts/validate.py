"""
ビルド成果物の品質検証スクリプト（book-engine 共通版）
make validate で呼ぶ。問題があれば非ゼロで終了する。

チェック内容:
  1. ページ数が4の倍数か
  2. 索引ヒットなし用語がないか（登録済みだが本文に存在しない）
  3. 未登録頻出語が閾値（SUGGEST_THRESHOLD）以上ないか

使い方:
  BOOK_ROOT=/path/to/book uv run --with "pykakasi,pyyaml" python book-template/scripts/validate.py
"""

import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
    from pykakasi import kakasi
except ImportError:
    print("依存ライブラリが不足しています: uv run --with 'pykakasi,pyyaml' python ...")
    sys.exit(1)

ROOT = Path(os.environ.get("BOOK_ROOT", "."))
TERMS_FILE = ROOT / "scripts" / "index-terms.yaml"
BOOK_PDF = ROOT / "dist" / "book-digital.pdf"

# 未登録頻出語がこの件数以上あれば警告
SUGGEST_THRESHOLD = 5
# 頻出語の最小出現回数
MIN_FREQ = 3

SKIP_FILES = {"index.md", "colophon.md", "preface.md", "author.md", "afterword.md"}
NOISE = {
    "md", "png", "pdf", "css", "js", "sh", "py", "yaml", "txt",
    "true", "false", "null", "None", "EOF",
    "the", "and", "or", "for", "with", "from", "import", "return",
    "path", "file", "str", "int", "list", "dict", "set",
    "assets", "scripts", "chapter", "image", "main",
    # 一般語・複合語の構成要素（単体では索引不要）
    "claude", "code", "max", "pro",  # 「Claude Code」等として登録済み（小文字で比較）
    "ファイル", "テーマ", "ツール", "コスト", "ページ",
    "タイトル", "ルール", "テキスト", "サークル", "コマンド",
    "リポジトリ", "ディレクトリ", "セクションタイトル", "プラン",
}

errors: list[str] = []
warnings: list[str] = []

# ── 1. ページ数チェック ───────────────────────────────────────
if not BOOK_PDF.exists():
    errors.append(f"PDF が見つかりません: {BOOK_PDF}（make build を先に実行してください）")
else:
    try:
        result = subprocess.run(
            ["pdfinfo", str(BOOK_PDF)],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":")[1].strip())
                if pages % 4 != 0:
                    errors.append(f"ページ数が4の倍数ではありません: {pages}p（印刷入稿時に白紙が自動補完されます）")
                else:
                    print(f"  ✅ ページ数: {pages}p（4の倍数）")
                break
    except (subprocess.CalledProcessError, FileNotFoundError):
        warnings.append("pdfinfo が見つかりません。ページ数チェックをスキップします（brew install poppler）")

# ── 2. 索引ヒットなし用語チェック ────────────────────────────
if not TERMS_FILE.exists():
    warnings.append(f"索引用語ファイルが見つかりません: {TERMS_FILE}")
else:
    manuscript = ROOT / "manuscript"
    chapter_files: list[Path] = []
    if manuscript.exists():
        chapter_files = sorted(manuscript.rglob("main.md"), key=lambda p: p.parent.name)

    chapter_texts: dict[str, str] = {}
    for path in chapter_files:
        fname = str(path.relative_to(ROOT))
        chapter_texts[fname] = path.read_text(encoding="utf-8")

    with TERMS_FILE.open(encoding="utf-8") as f:
        terms_data: list[dict] = yaml.safe_load(f) or []

    zero_hit: list[str] = []
    for entry in terms_data:
        term = entry.get("term", "").strip()
        if not term:
            continue
        patterns: list[str] = entry.get("patterns", [term])
        found = False
        for text in chapter_texts.values():
            for pat in patterns:
                try:
                    if re.search(pat, text):
                        found = True
                        break
                except re.error:
                    if pat in text:
                        found = True
                        break
            if found:
                break
        if not found:
            zero_hit.append(term)

    if zero_hit:
        errors.append(f"索引登録済みだが本文にヒットしない用語: {', '.join(zero_hit)}")
    else:
        print(f"  ✅ 索引ヒットなし: 0件")

# ── 3. 未登録頻出語チェック ──────────────────────────────────
    registered: set[str] = set()
    for entry in terms_data:
        registered.add(entry.get("term", ""))
        for p in entry.get("patterns", []):
            registered.add(p)

    combined = "\n".join(chapter_texts.values())
    combined = re.sub(r"```[\s\S]*?```", "", combined)
    combined = re.sub(r"`[^`\n]+`", "", combined)
    combined = re.sub(r"^#{1,6}[^\n]*$", "", combined, flags=re.MULTILINE)
    combined = re.sub(r"^\|[^\n]*$", "", combined, flags=re.MULTILINE)
    combined = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", combined)

    candidates = re.findall(r"[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z]+)*|[ァ-ヶー]{3,}", combined)
    counter = Counter(candidates)

    suggestions = [
        (term, count)
        for term, count in counter.most_common(50)
        if term not in registered
        and term.lower() not in NOISE
        and count >= MIN_FREQ
        and len(term) >= 2
    ]

    if len(suggestions) >= SUGGEST_THRESHOLD:
        suggestion_lines = "\n".join(f"    {count}回: {term}" for term, count in suggestions[:10])
        warnings.append(
            f"未登録の頻出語が {len(suggestions)} 件あります（index-terms.yaml への追加を検討）:\n{suggestion_lines}"
        )
    else:
        print(f"  ✅ 未登録頻出語: {len(suggestions)} 件（閾値 {SUGGEST_THRESHOLD} 件未満）")

# ── 結果出力 ─────────────────────────────────────────────────
print()
if warnings:
    for w in warnings:
        print(f"⚠️  {w}")

if errors:
    print()
    for e in errors:
        print(f"❌ {e}")
    print(f"\n{len(errors)} 件のエラーがあります。修正してください。")
    sys.exit(1)
else:
    print("✅ すべてのチェックが通過しました。")
