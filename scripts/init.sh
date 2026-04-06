#!/usr/bin/env bash
# 新しい本の初期化スクリプト
# 使い方: bash scripts/init.sh
set -e

echo "=== book-template 初期化 ==="
read -p "書名: " BOOK_TITLE
read -p "著者名: " AUTHOR
YEAR=$(date +%Y)
MONTH=$(date +%-m)

find . -type f \( -name "*.md" -o -name "*.js" -o -name "*.css" \) | while read f; do
  sed -i '' \
    -e "s|{{BOOK_TITLE}}|${BOOK_TITLE}|g" \
    -e "s|{{AUTHOR}}|${AUTHOR}|g" \
    -e "s|{{YEAR}}|${YEAR}|g" \
    -e "s|{{MONTH}}|${MONTH}|g" \
    "$f"
done

echo ""
echo "✅ 初期化完了"
echo "  書名: ${BOOK_TITLE}"
echo "  著者: ${AUTHOR}"
echo ""
echo "次のステップ:"
echo "  1. vivliostyle.config.js で章エントリを設定"
echo "  2. manuscript/ch01/main.md から執筆開始"
echo "  3. make build でPDF確認"
