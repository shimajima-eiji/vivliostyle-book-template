#!/usr/bin/env bash
# 新しい本の初期化スクリプト
# 使い方: bash scripts/init.sh
# book-template を ../book-template に clone して使う想定
set -e

echo "=== book-template 初期化 ==="
read -p "書名: " BOOK_TITLE
read -p "著者名: " AUTHOR
YEAR=$(date +%Y)
MONTH=$(date +%-m)

# プレースホルダー置換
find . -type f \( -name "*.md" -o -name "*.js" -o -name "*.css" -o -name "*.yaml" \) | while read f; do
  sed -i '' \
    -e "s|{{BOOK_TITLE}}|${BOOK_TITLE}|g" \
    -e "s|{{AUTHOR}}|${AUTHOR}|g" \
    -e "s|{{YEAR}}|${YEAR}|g" \
    -e "s|{{MONTH}}|${MONTH}|g" \
    "$f"
done

# Makefile を book-template 参照版に書き換え
cat > Makefile << 'MAKEFILE_EOF'
# Makefile — ビルドロジックは book-template/Makefile.engine に集約。
# book-template: https://github.com/shimajima-eiji/vivliostyle-book-template

ENGINE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))../book-template
include $(ENGINE_DIR)/Makefile.engine
MAKEFILE_EOF
echo "✅ Makefile を book-template 参照版に更新しました"

# assets/ ディレクトリと chapter-data.py スケルトンを作成
mkdir -p assets/diagrams

if [ ! -f assets/chapter-data.py ]; then
  cat > assets/chapter-data.py <<'EOF'
"""
章扉画像データ定義 — {{BOOK_TITLE}}
レイアウトロジックは book-template/assets/gen_chapter_covers_base.py に集約。

使い方: make chapters  または  uv run --with pillow python assets/chapter-data.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "assets"))
from gen_chapter_covers_base import render_all

# パレット定義 — 書籍テーマに合わせて調整する
PALETTES = {
    "main":  {"bg": (245, 248, 255), "accent": (30, 60, 120),  "text": (18, 22, 38)},
    "sub":   {"bg": (245, 250, 255), "accent": (25, 100, 160), "text": (15, 30, 50)},
}

# (章番号, 章ラベル, タイトル, サブコピー, タグ漢字1文字, パレット名)
CHAPTERS = [
    # ("01", "第1章", "章タイトル",
    #  "サブコピーをここに書く",
    #  "起", "main"),
]

# 章番号 → タイトル表示行のリスト（折り返しを手動制御）
TITLE_LINES = {
    # "01": ["章タイトル"],
}

if __name__ == "__main__":
    render_all(PALETTES, CHAPTERS, TITLE_LINES, out_dir=Path(__file__).parent)
EOF
  echo "✅ assets/chapter-data.py を作成しました（CHAPTERS/TITLE_LINES を書き込んでください）"
fi

if [ ! -f cover/fix-ledger.md ]; then
  cat > cover/fix-ledger.md <<'EOF'
# Cover Fix Ledger

最終的に採用している fix 入力と生成経路の台帳。

## Front

- output:
- canonical_source:
- generated_by:
- notes:
- updated:

## Back

- output:
- canonical_source:
- generated_by:
- notes:
- updated:

## Spine

- output:
- canonical_source:
- generated_by:
- notes:
- updated:
EOF
fi

# 表紙アセット運用の標準ディレクトリを用意
mkdir -p \
  cover/_candidates \
  cover/_fixed \
  cover/_work/incoming \
  cover/_work/scratch \
  cover/_work/compare \
  cover/_work/preview

if [ ! -f cover/_fixed/README.md ]; then
  cat > cover/_fixed/README.md <<'EOF'
# cover/_fixed

人手で補正した採用元マスターを置く。
- git管理する
- 生成スクリプトから参照してよい
- `copy` `final2` のような曖昧名は禁止
- 現在採用しているものは `cover/fix-ledger.md` に記録する
EOF
fi

if [ ! -f cover/_work/README.md ]; then
  cat > cover/_work/README.md <<'EOF'
# cover/_work

この書籍専用の一時ワークスペース。

- `incoming/`: 受領直後の一時置き場
- `scratch/`: 中間変換・試作
- `compare/`: 比較画像
- `preview/`: repo専用の確認物

ルール:
- `_work` 直下にファイルを直置きしない
- ここは git管理しない
- 採用候補に昇格させる場合は `_candidates/` または `_fixed/` に移す
EOF
fi

for subdir in incoming scratch compare preview; do
  if [ ! -f "cover/_work/${subdir}/README.md" ]; then
    cat > "cover/_work/${subdir}/README.md" <<EOF
# cover/_work/${subdir}

一時ワークスペースの ${subdir} 用ディレクトリ。
必要ならこの下に \`YYYYMMDD-短い説明/\` を切って使う。
EOF
  fi
done

echo ""
echo "✅ 初期化完了"
echo "  書名: ${BOOK_TITLE}"
echo "  著者: ${AUTHOR}"
echo ""
echo "前提: ../book-template が存在すること"
echo "  git clone https://github.com/shimajima-eiji/vivliostyle-book-template ../book-template"
echo ""
echo "次のステップ:"
echo "  1. vivliostyle.config.js で章エントリを設定"
echo "  2. manuscript/ch01/main.md から執筆開始"
echo "  3. make build でPDF確認"
echo "  4. 表紙作業は cover/_candidates / _fixed / _work/{incoming,scratch,compare,preview} を使い分ける"
echo "  5. 採用fixは cover/fix-ledger.md に記録する"
