PYTHON     := uv run --with "pykakasi,pyyaml" python
COVER_PNG  := cover/cover-book.png
COVER_PDF  := /tmp/cover-page.pdf
BOOK_PDF   := dist/book-digital.pdf
FINAL_PDF  := dist/book-digital-with-cover.pdf

.PHONY: all build index vivliostyle cover clean help

all: build

## フルビルド（索引再生成 → PDF組版 → 表紙結合）
build: index vivliostyle cover

## 索引のみ再生成（scripts/index-terms.yaml が変更されたとき）
index:
	$(PYTHON) scripts/gen-index.py

## Vivliostyle でPDFを組版（索引再生成なし）
vivliostyle:
	npx @vivliostyle/cli build

## 表紙を先頭に結合して最終PDFを生成（カバー画像がない場合はそのままコピー）
cover: $(BOOK_PDF)
	@if [ -f "$(COVER_PNG)" ]; then \
		magick convert -density 300 $(COVER_PNG) $(COVER_PDF) 2>/dev/null; true; \
		pdfunite $(COVER_PDF) $(BOOK_PDF) $(FINAL_PDF); \
		echo "✅ $(FINAL_PDF) （表紙あり）"; \
	else \
		cp $(BOOK_PDF) $(FINAL_PDF); \
		echo "⚠️  カバー画像なし（$(COVER_PNG)）。$(FINAL_PDF) = 本文のみ"; \
	fi

## 中間ファイルを削除
clean:
	rm -f $(COVER_PDF)

help:
	@grep -E '^##' Makefile | sed 's/^## /  /'
	@echo ""
	@echo "使い方:"
	@echo "  make          # = make build"
	@echo "  make build    # フルビルド"
	@echo "  make index    # 索引のみ再生成"
	@echo "  make vivliostyle  # 組版のみ（索引再生成なし）"
