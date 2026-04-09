#!/usr/bin/env bash
# 新しい本の初期化スクリプト
# 使い方: bash scripts/init.sh
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

# book-engine のセットアップ（失敗しても初期化は完了扱い）
BOOK_ENGINE_DIR="$(dirname "$(pwd)")/book-engine"
BOOK_ENGINE_URL="https://github.com/shimajima-eiji/book-engine.git"

echo ""
echo "--- book-engine セットアップ ---"
if [ -d "$BOOK_ENGINE_DIR/.git" ]; then
  echo "✅ book-engine は既にセットアップ済みです: ${BOOK_ENGINE_DIR}"
  USE_ENGINE=true
elif git clone "$BOOK_ENGINE_URL" "$BOOK_ENGINE_DIR" 2>/dev/null; then
  echo "✅ book-engine をセットアップしました: ${BOOK_ENGINE_DIR}"
  USE_ENGINE=true
else
  echo "⚠️  book-engine のセットアップをスキップしました（後から手動で設定できます）"
  USE_ENGINE=false
fi

# book-engine が使える場合は Makefile をラッパーに置き換え
if [ "$USE_ENGINE" = true ]; then
  cat > Makefile << 'MAKEFILE_EOF'
# Makefile — ビルドロジックは book-engine/Makefile.engine に集約。
# book-engine: https://github.com/nomuraya-books/book-engine

ENGINE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))../book-engine
include $(ENGINE_DIR)/Makefile.engine
MAKEFILE_EOF
  echo "✅ Makefile を book-engine 参照版に更新しました"
fi

echo ""
echo "✅ 初期化完了"
echo "  書名: ${BOOK_TITLE}"
echo "  著者: ${AUTHOR}"
echo ""
echo "次のステップ:"
echo "  1. vivliostyle.config.js で章エントリを設定"
echo "  2. manuscript/ch01/main.md から執筆開始"
echo "  3. make build でPDF確認"
