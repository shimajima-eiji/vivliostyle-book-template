"""
ビルド成果物の品質検証スクリプト（book-engine 共通版）
make validate で呼ぶ。問題があれば非ゼロで終了する。

チェック内容:
  1. ページ数が4の倍数か
  2. 索引ヒットなし用語がないか（登録済みだが本文に存在しない）
  3. 未登録頻出語が閾値（SUGGEST_THRESHOLD）以上ないか
  4. 印刷費参考値・市場相場との比較（完全受注生産対応）

対応フォーマット（BOOK_FORMAT 環境変数で切り替え、未設定時は自動検出）:
  review      … book/book.pdf + book/ch*.re をスキャン
  vivliostyle … dist/book-digital.pdf + manuscript/ch*/main.md をスキャン

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
BOOK_YAML = ROOT / "book.yaml"

# フォーマット判定: 環境変数 > 自動検出（book/config.yml の有無）
_fmt_env = os.environ.get("BOOK_FORMAT", "")
if _fmt_env in ("review", "vivliostyle"):
    FORMAT = _fmt_env
else:
    FORMAT = "review" if (ROOT / "book" / "config.yml").exists() else "vivliostyle"

# フォーマット別の PDF パスと章ファイルパターン
if FORMAT == "review":
    BOOK_PDF = ROOT / "book" / "book.pdf"
else:
    BOOK_PDF = ROOT / "dist" / "book-digital.pdf"

print(f"  フォーマット: {FORMAT}  PDF: {BOOK_PDF}")

# 印刷仕様の読み込み元: Re:VIEW は book/config.yml、Vivliostyle は book.yaml
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

def _strip_review_markup(text: str) -> str:
    """Re:VIEW マークアップを除去（索引検索用）。"""
    text = re.sub(r"^//(?:list|cmd|terminal|source|emlist|listnum|caution|note|warning|info)\b[^\n]*\n.*?^//\}",
                  "", text, flags=re.DOTALL | re.MULTILINE)
    text = re.sub(r"@<hidx>\{([^}]*)\}", r"\1", text)
    text = re.sub(r"@<code>\{[^}]*\}", "", text)
    text = re.sub(r"@<\w+>\{([^}]*)\}", r"\1", text)
    text = re.sub(r"^//\w+[^\n]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^={1,6}(?:\[.*?\])?\s*", "", text, flags=re.MULTILINE)
    return text


# ── 2. 索引ヒットなし用語チェック ────────────────────────────
if not TERMS_FILE.exists():
    warnings.append(f"索引用語ファイルが見つかりません: {TERMS_FILE}")
else:
    chapter_files: list[Path] = []
    if FORMAT == "review":
        review_dir = ROOT / "book"
        if review_dir.exists():
            chapter_files = sorted(
                f for f in review_dir.iterdir()
                if f.suffix == ".re" and re.match(r"ch\d+", f.stem)
            )
    else:
        manuscript = ROOT / "manuscript"
        manuscripts = ROOT / "manuscripts"
        if manuscript.exists():
            # chXX/main.md 構造（ai-writing-guide / teaching 等）
            chapter_files = sorted(manuscript.rglob("main.md"), key=lambda p: p.parent.name)
        elif manuscripts.exists():
            # XX-title.md フラット構造（freelance-contract-os 等）
            SKIP_FLAT = {"index.md", "colophon.md", "preface.md", "author.md", "afterword.md", "config.yaml"}
            chapter_files = sorted(
                f for f in manuscripts.glob("*.md")
                if f.name not in SKIP_FLAT
            )

    chapter_texts: dict[str, str] = {}
    for path in chapter_files:
        fname = str(path.relative_to(ROOT))
        raw = path.read_text(encoding="utf-8")
        chapter_texts[fname] = _strip_review_markup(raw) if FORMAT == "review" else raw

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

    # chapter_texts は既にマークアップ除去済み
    combined = "\n".join(chapter_texts.values())
    if FORMAT == "review":
        combined = re.sub(r"^//.+$", "", combined, flags=re.MULTILINE)
    else:
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

# ── 4. 印刷費参考値・市場相場 ─────────────────────────────────
# 【重要】以下の料金テーブルは参考値です。
# - データ取得日: 2025-01-01（日光企画・オンデマンド印刷・A5・モノクロ本文）
# - 価格は予告なく改定されます。入稿前に必ず公式サイトで確認してください
# - 公式: https://www.nikko-pc.com/
# - 早割は「〆切日程」ページで確認: 締め切り3週間以上前で20〜30%引きが多い
NIKKO_ONDEMAND_A5_MONO: dict[int, dict[int, int]] = {
    # ページ数: {部数: 合計金額（税込）} — 日光企画公式の「冊子印刷・オンデマンド」より
    32:  {10: 3850,  20: 5060,  30: 6270,  50: 8690,  100: 15400},
    48:  {10: 4730,  20: 6490,  30: 8250,  50: 11770, 100: 21010},
    60:  {10: 5500,  20: 7700,  30: 9900,  50: 14300, 100: 25850},
    80:  {10: 6820,  20: 9790,  30: 12760, 50: 18700, 100: 34100},
    100: {10: 8140,  20: 11880, 30: 15620, 50: 23100, 100: 42350},
    120: {10: 9460,  20: 13970, 30: 18480, 50: 27500, 100: 50600},
}
EARLY_DISCOUNT_RATE = 0.80  # 早割（3週間以上前）: 約20%引き

# 技術書典・BOOTH市場相場（2025年調査）
# 60p前後の技術同人誌: 1,000円が最多。エッセイ系は800〜1,000円が上限感
# 完全受注生産でも価格上乗せは慣例的に行わない
MARKET_PHYSICAL_STANDARD = 1000  # 技術書典で最も多い物理本価格


def _unit_cost(price_table: dict[int, int], qty: int) -> int:
    return price_table[qty] // qty


def _physical_min(unit_cost: int) -> int:
    """印刷費回収ライン（印刷費×2倍、100円切り上げ）。"""
    return (unit_cost * 2 + 99) // 100 * 100


def _pdf_range(physical_price: int) -> tuple[int, int]:
    """物理本価格からPDF価格を逆算（物理本の50〜70%、100円切り捨て）。"""
    return (
        physical_price * 50 // 100 // 100 * 100,
        physical_price * 70 // 100 // 100 * 100,
    )


def estimate_print_cost(total_pages: int) -> None:
    """ページ数に近い料金テーブルを参照して参考値と市場相場を表示する。"""
    candidates = [p for p in NIKKO_ONDEMAND_A5_MONO if p >= total_pages]
    if not candidates:
        print("  ℹ️  印刷費参考値: テーブル範囲外（公式サイトで見積もりしてください）")
        return

    table_pages = min(candidates)
    price_table = NIKKO_ONDEMAND_A5_MONO[table_pages]

    # 完全受注生産の基準: 10部ロット単価（最もコスト高）
    unit_od = _unit_cost(price_table, 10)
    phys_od = _physical_min(unit_od)
    pdf_od_min, pdf_od_max = _pdf_range(phys_od)
    margin_od = MARKET_PHYSICAL_STANDARD - unit_od  # 市場標準1,000円での1冊利益

    SEP = "  " + "-" * 51

    print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ⚠️  印刷費【参考値】日光企画・A5モノクロ（{table_pages}p 相当）")
    print(f"  ⚠️  データ: 2025-01-01取得 ｜ 公式: https://www.nikko-pc.com/")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── 完全受注生産セクション ──
    print(f"  🎯  完全受注生産（1冊ずつ・10部ロット単価基準）")
    print(f"      印刷費/冊: {unit_od:,}円")
    print(f"      印刷費回収ライン: {phys_od:,}円〜（印刷費×2倍）")
    if margin_od >= 0:
        print(f"      市場標準1,000円で売った場合: +{margin_od:,}円/冊の利益")
        print(f"      → 物理本: 1,000円  PDF: {pdf_od_min:,}〜{pdf_od_max:,}円 が現実的な設定")
    else:
        print(f"      ⚠️  市場標準1,000円では {abs(margin_od):,}円/冊の赤字")
        print(f"      → 物理本: {phys_od:,}円以上  PDF: {pdf_od_min:,}〜{pdf_od_max:,}円 を推奨")
    print(SEP)

    # ── 市場相場セクション ──
    print(f"  📊  市場相場（技術書典・BOOTH 2025年調査）")
    print(f"      物理本:          1,000円が最多（60p前後・技術エッセイ含む）")
    print(f"      PDF単体:         600〜700円（60〜99p帯）")
    print(f"      PDF+物理同時:    物理本の50〜70%が相場")
    print(f"      完全受注生産:    通常頒布と同価格帯が慣例（上乗せしない）")
    print(SEP)

    # ── 部数別比較テーブル ──
    print(f"  📊  まとめて刷る場合（部数別・市場標準1,000円販売時）")
    print(f"  {'部数':>5}  {'印刷費':>8}  {'早割':>7}  {'単価':>5}  {'回収ライン':>9}  {'PDF目安':>11}  {'利益合計':>9}")
    print(f"  {'-'*5}  {'-'*8}  {'-'*7}  {'-'*5}  {'-'*9}  {'-'*11}  {'-'*9}")
    for qty, total in sorted(price_table.items()):
        unit = _unit_cost(price_table, qty)
        early = int(total * EARLY_DISCOUNT_RATE)
        phys = _physical_min(unit)
        p_min, p_max = _pdf_range(phys)
        profit = (MARKET_PHYSICAL_STANDARD - unit) * qty
        profit_str = f"+{profit:,}円" if profit >= 0 else f"▲{abs(profit):,}円"
        marker = " ←受注基準" if qty == 10 else ""
        print(f"  {qty:>5}冊  {total:>7,}円  {early:>6,}円  {unit:>4,}円  {phys:>7,}円〜  {p_min:,}〜{p_max:,}円  {profit_str:>8}{marker}")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ※ 早割: 締め切り3週間前目安・実際の割引率は時期により異なる")
    print(f"  ※ 利益合計 = (1,000円 - 1冊単価) × 部数（搬入・委託手数料等は含まない）")
    print(f"\n  ⚠️  【このツールが対応していないケース】")
    print(f"  ・PDF単体のみ頒布: 物理本なしの場合はPDF相場600〜700円を直接参照")
    print(f"  ・カラー表紙オプション: 表紙印刷費は未反映。実際の単価はテーブル値より高くなる")
    print(f"  ・120p超: テーブル範囲外。公式サイトの見積もりフォームで算出")
    print(f"  ・委託販売: BOOTH手数料22%・書店委託30〜40%は別途計算が必要")
    print(f"  ・直前入稿: 早割が使えない場合、早割欄の数字は無効")


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
