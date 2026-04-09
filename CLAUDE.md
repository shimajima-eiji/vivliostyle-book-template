# {{BOOK_TITLE}} — 運用ガイド（AI向け）

## このリポジトリについて

`book-template` をベースに初期化された書籍リポジトリ。
ビルドロジックは `../book-template/Makefile.engine` に集約されている。

## ディレクトリ構成

```
manuscript/
  ch01/main.md  第1章（ここから執筆開始）
  chXX/main.md  追加章
  index.md      索引（make index で自動生成）
  colophon.md   奥付
scripts/
  gen-index.py      索引自動生成
  index-terms.yaml  索引用語リスト（手動管理）
theme/
  book.css      Vivliostyle テーマ（A5縦型）
cover/
  cover-book.png  表紙画像（make cover で生成）
dist/
  book-digital.pdf            本文PDF
  book-digital-with-cover.pdf 表紙込みPDF（配布用）
```

## ビルドコマンド

```bash
make build       # フルビルド（索引 → PDF → 表紙結合）
make vivliostyle # PDF組版のみ（原稿確認用）
make index       # 索引のみ再生成
make validate    # 品質チェック（ページ数・索引・印刷費参考値）
make clean       # dist/ を削除
```

## 章を追加するとき

1. `manuscript/chXX/main.md` を作成
2. `vivliostyle.config.js` の `entry` に追記
3. `make vivliostyle` で確認

## 索引を管理するとき

- `scripts/index-terms.yaml` に用語を追加
- `make index` で `manuscript/index.md` を再生成
- `make validate` で登録済み用語のヒットなし・未登録頻出語を確認

## 執筆スタイルについて

このテンプレートは執筆スタイルを規定しない。
著者自身のルールを `CLAUDE.md` に追記して使うこと。

例:
```
## 執筆ルール（著者設定）
- 一人称: 「私」
- 禁止表現: 〜しましょう
```
