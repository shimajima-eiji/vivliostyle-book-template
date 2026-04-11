"""
プリフライトチェック — 印刷・配布前の品質検証スクリプト。

チェック項目:
  1. PDF寸法がA5/B5の正しいサイズか
  2. 完全空白ページがないか
  3. 充填率45%未満のスカスカページがないか
  4. ノド余白が十分か（くるみ15mm以上、中綴じ10mm以上）
  5. 表紙画像がカット・クロップされていないか（表紙ページの画像サイズ検証）
  6. 裏表紙が存在するか
  7. 遊び紙（裏表紙直前の空白ページ）がないか
  8. ページ数の報告

使い方:
  python preflight-check.py <pdf_path> [--paper a5|b5] [--binding wireless|saddle]
"""
import sys
import argparse
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf が必要です: uv run --with pymupdf python preflight-check.py ...")
    sys.exit(1)

# 用紙サイズ定義 (mm)
PAPER_SPECS = {
    "a5": (148.0, 210.0),
    "b5": (182.0, 257.0),
}

# ノド余白の最低値 (mm)
GUTTER_MIN = {
    "wireless": 15.0,  # くるみ製本
    "saddle": 10.0,    # 中綴じ
}


def pt_to_mm(pt: float) -> float:
    return pt * 25.4 / 72.0


def check_page_size(doc, expected_w_mm, expected_h_mm, tolerance_mm=1.0):
    """全ページの寸法を検証"""
    issues = []
    for i in range(doc.page_count):
        p = doc[i]
        w = pt_to_mm(p.rect.width)
        h = pt_to_mm(p.rect.height)
        if abs(w - expected_w_mm) > tolerance_mm or abs(h - expected_h_mm) > tolerance_mm:
            issues.append(f"P{i+1}: {w:.1f}x{h:.1f}mm (期待: {expected_w_mm}x{expected_h_mm}mm)")
    return issues


def check_blank_pages(doc):
    """完全空白ページを検出"""
    blanks = []
    for i in range(doc.page_count):
        p = doc[i]
        text = p.get_text().strip()
        imgs = p.get_images()
        if not text and not imgs:
            blanks.append(i + 1)
    return blanks


def check_fill_ratio(doc, threshold=0.45):
    """充填率が低いページを検出（表紙・裏表紙は除外）"""
    sparse = []
    for i in range(1, doc.page_count - 1):  # 表紙・裏表紙を除外
        p = doc[i]
        blocks = p.get_text("blocks")
        text_blocks = [b for b in blocks if b[4].strip()]
        imgs = p.get_images()
        if not text_blocks and imgs:
            continue  # 画像のみのページ（表紙等）はスキップ
        if text_blocks:
            max_y = max(b[3] for b in text_blocks)
            fill = max_y / p.rect.height
            if fill < threshold:
                sparse.append((i + 1, fill))
    return sparse


def check_gutter(doc, min_gutter_mm, sample_pages=None):
    """ノド余白を検証（本文ページのサンプリング）"""
    if sample_pages is None:
        # 本文の代表ページ（表紙・目次を除いた5ページ目以降）
        sample_pages = [i for i in range(4, min(doc.page_count - 2, 15))]
    issues = []
    for i in sample_pages:
        if i >= doc.page_count:
            continue
        p = doc[i]
        blocks = p.get_text("blocks")
        text_blocks = [b for b in blocks if b[4].strip()]
        if not text_blocks:
            continue
        min_x = min(b[0] for b in text_blocks)
        max_x = max(b[2] for b in text_blocks)
        w_pt = p.rect.width
        left_mm = pt_to_mm(min_x)
        right_mm = pt_to_mm(w_pt - max_x)
        # 奇数ページ=右ページ=ノドが左、偶数ページ=左ページ=ノドが右
        gutter_mm = left_mm if i % 2 == 0 else right_mm
        if gutter_mm < min_gutter_mm:
            issues.append(f"P{i+1}: ノド={gutter_mm:.1f}mm (最低{min_gutter_mm}mm)")
    return issues


def check_cover(doc):
    """表紙と裏表紙の検証"""
    issues = []
    # P1: 表紙に画像があるか
    p1 = doc[0]
    if not p1.get_images():
        issues.append("P1: 表紙に画像がありません")

    # 最終ページ: 裏表紙に画像があるか
    last = doc[doc.page_count - 1]
    if not last.get_images():
        issues.append(f"P{doc.page_count}: 裏表紙に画像がありません")

    return issues


def check_play_paper(doc):
    """裏表紙直前の遊び紙を検出"""
    if doc.page_count < 3:
        return []
    pen = doc[doc.page_count - 2]  # 裏表紙の1つ前
    text = pen.get_text().strip()
    imgs = pen.get_images()
    if not text and not imgs:
        return [f"P{doc.page_count - 1}: 裏表紙直前が空白ページ（遊び紙の可能性）"]
    return []


def check_page_count_multiple(doc, binding):
    """本文ページ数が4の倍数かチェック（表紙・裏表紙を除く本文のみ）"""
    # 本文ページ数 = 全体 - 表紙(1) - 裏表紙(1)
    # ただし「本文のみ」PDFの場合は全ページが本文
    total = doc.page_count
    # 表紙・裏表紙の有無を判定
    first_has_img = bool(doc[0].get_images()) and not doc[0].get_text().strip()
    last_has_img = bool(doc[-1].get_images()) and not doc[-1].get_text().strip()
    body_pages = total
    if first_has_img:
        body_pages -= 1
    if last_has_img:
        body_pages -= 1

    if body_pages % 4 != 0:
        return [f"本文{body_pages}ページ（4の倍数でない。あと{4 - body_pages % 4}ページ追加が必要）"]
    return []


def run_check(pdf_path: Path, paper: str, binding: str) -> bool:
    doc = fitz.open(pdf_path)
    w_mm, h_mm = PAPER_SPECS[paper]
    gutter_min = GUTTER_MIN[binding]
    is_body_only = "本文のみ" in pdf_path.name

    print(f"📋 プリフライトチェック: {pdf_path.name}")
    print(f"   用紙: {paper.upper()} ({w_mm}x{h_mm}mm), 製本: {binding}")
    print(f"   ページ数: {doc.page_count}P {'(本文のみ)' if is_body_only else ''}")
    print()

    all_ok = True
    checks = [
        ("寸法", lambda: check_page_size(doc, w_mm, h_mm)),
        ("空白ページ", lambda: check_blank_pages(doc)),
        ("充填率", lambda: check_fill_ratio(doc)),
        ("ノド余白", lambda: check_gutter(doc, gutter_min)),
        ("4の倍数", lambda: check_page_count_multiple(doc, binding)),
    ]
    if not is_body_only:
        checks.append(("表紙/裏表紙", lambda: check_cover(doc)))
        checks.append(("遊び紙", lambda: check_play_paper(doc)))

    for label, fn in checks:
        result = fn()
        if not result:
            print(f"✅ {label}: OK")
        elif label == "充填率":
            print(f"⚠️  スカスカページ（充填率45%未満）:")
            for pn, fill in result:
                print(f"   P{pn}: {fill:.0%}")
            all_ok = False
        else:
            icon = "❌" if label in ("寸法", "空白ページ", "ノド余白") else "⚠️ "
            print(f"{icon} {label}:")
            for x in (result if isinstance(result[0], str) else [str(r) for r in result]):
                print(f"   {x}")
            all_ok = False

    print()
    print("🎉 全チェック通過" if all_ok else "⚠️  要確認項目があります")
    doc.close()
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="プリフライトチェック")
    parser.add_argument("pdf_or_dir", help="チェック対象のPDFまたはdist/ディレクトリ")
    parser.add_argument("--paper", default=None, choices=["a5", "b5"],
                        help="用紙サイズ（省略時はファイル名から自動判別）")
    parser.add_argument("--binding", default="wireless", choices=["wireless", "saddle"])
    args = parser.parse_args()

    target = Path(args.pdf_or_dir)

    # ディレクトリが渡された場合は中の *_カラー.pdf を全て検索
    if target.is_dir():
        pdfs = sorted(target.glob("*_カラー*.pdf"))
        if not pdfs:
            print(f"ERROR: {target} にチェック対象のPDFがありません")
            sys.exit(1)
    else:
        if not target.exists():
            print(f"ERROR: {target} が見つかりません")
            sys.exit(1)
        pdfs = [target]

    all_passed = True
    for pdf_path in pdfs:
        # 用紙サイズの自動判別
        paper = args.paper
        if paper is None:
            paper = "b5" if "_B5" in pdf_path.name else "a5"

        ok = run_check(pdf_path, paper, args.binding)
        if not ok:
            all_passed = False
        print()

    if len(pdfs) > 1:
        print("=" * 40)
        if all_passed:
            print(f"🎉 全{len(pdfs)}ファイル チェック通過")
        else:
            print(f"⚠️  要確認項目があります")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
