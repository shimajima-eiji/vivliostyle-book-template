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
from datetime import date
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
BOOK_YAML = ROOT / "book.yaml"

# book.yaml から印刷仕様を読み込む
# 表紙（表1〜表4）・遊び紙は本文ページ数とは別カウントのため加算しない
binding = "wireless"  # デフォルト: 無線綴じ
quote_date_str = None
printer = None
if BOOK_YAML.exists():
    with BOOK_YAML.open(encoding="utf-8") as f:
        book_config = yaml.safe_load(f) or {}
    print_config = book_config.get("print") or {}
    binding = print_config.get("binding", "wireless")
    quote_date_str = print_config.get("quote_date")
    printer = print_config.get("printer")

# 製本方式ごとのページ数の倍数要件
# - 中綴じ(saddle): 4の倍数必須（1枚=4p の折り丁構造）
# - 無線綴じ(wireless): 2の倍数で可（料金設定は印刷所により4単位が多い）
PAGE_MULTIPLE = 4 if binding == "saddle" else 2

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
                # 表紙（表1〜表4）・遊び紙は印刷所が別管理するため本文PDFのみでチェック
                binding_label = "中綴じ・4の倍数必須" if binding == "saddle" else "無線綴じ・2の倍数"
                if pages % PAGE_MULTIPLE != 0:
                    shortage = PAGE_MULTIPLE - (pages % PAGE_MULTIPLE)
                    errors.append(
                        f"本文ページ数が{PAGE_MULTIPLE}の倍数ではありません: {pages}p（{binding_label}）\n"
                        f"    → 本文を {shortage}p 増やしてください"
                    )
                else:
                    print(f"  ✅ ページ数: {pages}p（{binding_label}・OK）")
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

# ── 4. 印刷費参考値 ────────────────────────────────────────────
# 【重要】以下の料金テーブルは参考値です。
# - データ取得日: 2025-01-01（日光企画・オンデマンド印刷・A5・モノクロ本文）
# - 価格は予告なく改定されます。入稿前に必ず公式サイトで確認してください
# - 公式: https://www.nikko-pc.com/
# - 早割は「〆切日程」ページで確認: 締め切り3週間以上前で20〜30%引きが多い
#
# テーブル構造: {ページ数: {部数: 単価（円）}}
# ※ オンデマンド・A5・モノクロ本文の場合（2025年1月時点）
NIKKO_ONDEMAND_A5_MONO: dict[int, dict[int, int]] = {
    # ページ数: {部数: 合計金額（税込）} — 日光企画公式の「冊子印刷・オンデマンド」より
    # 実際の料金は https://www.nikko-pc.com/ の見積もりフォームで確認すること
    32:  {10: 3850,  20: 5060,  30: 6270,  50: 8690,  100: 15400},
    48:  {10: 4730,  20: 6490,  30: 8250,  50: 11770, 100: 21010},
    60:  {10: 5500,  20: 7700,  30: 9900,  50: 14300, 100: 25850},
    80:  {10: 6820,  20: 9790,  30: 12760, 50: 18700, 100: 34100},
    100: {10: 8140,  20: 11880, 30: 15620, 50: 23100, 100: 42350},
    120: {10: 9460,  20: 13970, 30: 18480, 50: 27500, 100: 50600},
}
EARLY_DISCOUNT_RATE = 0.80  # 早割（3週間以上前）: 約20%引き

def estimate_print_cost(total_pages: int) -> None:
    """ページ数に近い料金テーブルを参照して参考値を表示する。"""
    # 最も近いページ数エントリを選ぶ（以上で最小）
    candidates = [p for p in NIKKO_ONDEMAND_A5_MONO if p >= total_pages]
    if not candidates:
        print("  ℹ️  印刷費参考値: テーブル範囲外（公式サイトで見積もりしてください）")
        return

    table_pages = min(candidates)
    price_table = NIKKO_ONDEMAND_A5_MONO[table_pages]

    print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ⚠️  印刷費【参考値】— 日光企画・オンデマンド・A5モノクロ（{table_pages}p 相当）")
    print(f"  ⚠️  データ取得日: 2025-01-01 ｜ 必ず公式サイトで最新料金を確認してください")
    print(f"  ⚠️  公式見積もり: https://www.nikko-pc.com/")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {'部数':>6}  {'通常':>8}  {'早割(目安)':>10}  {'単価':>7}  {'物理本価格目安':>14}")
    print(f"  {'':->6}  {'':->8}  {'':->10}  {'':->7}  {'':->14}")
    for qty, total in sorted(price_table.items()):
        unit = total // qty
        early = int(total * EARLY_DISCOUNT_RATE)
        # 物理本頒布価格目安: 印刷費の2倍÷部数（100円単位切り上げ）
        sell_min = ((total * 2) // qty + 99) // 100 * 100
        print(f"  {qty:>6}冊  {total:>7,}円  {early:>9,}円  {unit:>6,}円  {sell_min:>10,}円〜")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ※ 早割は締め切り3週間前目安・実際の割引率は時期により異なる")
    print(f"  ※ 物理本価格目安は印刷費回収ライン（送料・委託手数料・自費分は別途考慮）\n")

    estimate_pdf_price(total_pages)


# BOOTH・技術書典のPDF頒布相場（2025年時点）
# ページ数帯ごとの一般的な価格レンジ。無料〜有料の判断基準も含む
PDF_PRICE_GUIDE: list[tuple[int, int, str, str]] = [
    # (ページ下限, ページ上限, 推奨価格帯, 補足)
    (1,   29, "無料〜300円",  "入門・ショートコンテンツ。BOOTH無料配布も多い"),
    (30,  59, "300〜500円",  "薄い本の主流。技術書典では500円が多い"),
    (60,  99, "500〜800円",  "標準的なページ数。600〜700円が相場"),
    (100, 149, "700〜1000円", "読み応えあり。1000円でも抵抗感は少ない"),
    (150, 999, "1000〜1500円", "厚い本。物理本と競合するため上限に注意"),
]

def estimate_pdf_price(total_pages: int) -> None:
    """ページ数からPDF頒布価格の相場を表示する。"""
    guide = next(
        (g for g in PDF_PRICE_GUIDE if g[0] <= total_pages <= g[1]),
        None
    )
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📄  PDF頒布価格【市場相場】— BOOTH・技術書典（2025年時点）")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if guide:
        _, _, price_range, note = guide
        print(f"  {total_pages}p の相場: {price_range}")
        print(f"  補足: {note}")
    else:
        print(f"  {total_pages}p: テーブル範囲外")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  【物理本と同時頒布する場合の価格設定指針】")
    print(f"  - PDF = 物理本の 50〜70% が一般的（例: 物理600円 → PDF 300〜400円）")
    print(f"  - 物理本購入者にPDFを付ける場合はBOOTHのまとめ買い割引を活用")
    print(f"  - 無料配布はフォロワー獲得・次回作への誘導として有効")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

# ページ数が確定している場合のみ参考値を表示
if BOOK_PDF.exists():
    try:
        result_pdf = subprocess.run(
            ["pdfinfo", str(BOOK_PDF)], capture_output=True, text=True, check=True
        )
        for line in result_pdf.stdout.splitlines():
            if line.startswith("Pages:"):
                pdf_pages = int(line.split(":")[1].strip())
                estimate_print_cost(pdf_pages)
                break
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # pdfinfo なければスキップ（ページ数チェックで既に警告済み）

# 見積もり取得日の鮮度チェック
QUOTE_EXPIRY_DAYS = 90
if quote_date_str:
    try:
        quote_date = date.fromisoformat(str(quote_date_str))
        days_elapsed = (date.today() - quote_date).days
        printer_label = f"（{printer}）" if printer else ""
        if days_elapsed > QUOTE_EXPIRY_DAYS:
            warnings.append(
                f"印刷費見積もりが {days_elapsed} 日前{printer_label}です。\n"
                f"    → 入稿前に最新の見積もりを取り直してください（book.yaml の quote_date を更新）"
            )
        else:
            print(f"  ✅ 印刷費見積もり取得日: {quote_date_str}{printer_label}（{days_elapsed} 日前・有効）")
    except ValueError:
        warnings.append(f"quote_date の形式が不正です: {quote_date_str}（YYYY-MM-DD で記述してください）")
else:
    print("  ℹ️  印刷費見積もり取得日: 未記録（入稿時は book.yaml に quote_date/printer を記録）")

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
