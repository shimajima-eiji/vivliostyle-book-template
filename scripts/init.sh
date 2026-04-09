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
