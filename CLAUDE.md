# {{BOOK_TITLE}} — 運用ルール

## ディレクトリ構成

```
manuscript/
  ch01/main.md  第1章
  ch02/main.md  第2章（追加していく）
  index.md      索引（自動生成）
  colophon.md   奥付
scripts/
  gen-index.py      索引自動生成
  index-terms.yaml  索引用語リスト
  init.sh           初期化スクリプト
theme/
  book.css      Vivliostyle テーマ（A5縦型）
cover/
  cover-book.png  表紙画像（make cover で使用）
dist/
  book-digital.pdf            本文PDF
  book-digital-with-cover.pdf 表紙込みPDF（配布用）
```

## ビルド

```bash
make build      # フルビルド（索引 → PDF → 表紙結合）
make vivliostyle # PDF組版のみ
make index      # 索引のみ再生成
```

## 執筆ルール

- 一人称は「私」
- 体験ベースで書く（具体例・失敗談・Before/After必須）
- 禁止表現: `〜しましょう` `〜ありませんか` `この記事では` `**太字**`
- 禁止見出し: `## はじめに` `## まとめ` `## おわりに`
- センシティブ情報（企業名・個人名）は匿名化

## 章を追加するとき

1. `manuscript/chXX/main.md` を作成
2. `vivliostyle.config.js` の `entry` に追記
3. `make vivliostyle` で確認
