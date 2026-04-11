# {{BOOK_TITLE}} — 運用ガイド（AI向け）

## このリポジトリについて

`book-template` をベースに初期化された書籍リポジトリ。
ビルドロジックは `../book-template/Makefile.engine` に集約されている。
Re:VIEW と Vivliostyle の両方に対応。format は自動検出される。

## format 自動検出

`book/config.yml` が存在すれば Re:VIEW、なければ Vivliostyle。

## ディレクトリ構成

### Vivliostyle の場合

```
manuscript/
  preface.md          はじめに（本文ビルドに含まれる）
  preface-standalone.md  はじめに独立ビルド用（章扉なし）
  ch01/main.md        第1章
  index.md            索引（make index で自動生成）
  colophon.md         奥付
vivliostyle.config.js   本文ビルド設定
vivliostyle.preface.js  はじめに独立ビルド設定
theme/
  book.css            本文テーマ（A5縦型）
  preface.css         はじめにテーマ（ローマ数字ノンブル）
assets/
  chapter-XX.png      章扉画像（原稿の ![](../../assets/...) で参照）
  diagrams/           図解画像
```

### Re:VIEW の場合

```
book/
  config.yml          Re:VIEW 設定
  catalog.yml         章構成（PREDEF/CHAPS/POSTDEF）
  preface.re          はじめに
  ch01.re〜           各章
  colophon.re         奥付
  images/             本文画像（原稿の @<image>{...} で参照）
    cover.png         表紙（coverimage 用、ビルド生成物）
    cover-a5.pdf      表紙PDF（pdfmaker 用、ビルド生成物）
    cover-b5.pdf      B5版表紙PDF（ビルド生成物）
    backcover.png     裏表紙（ビルド生成物）
    *.png             本文挿絵（著者が手動配置）
```

### 共通

```
book.yaml               書籍メタデータ（タイトル・著者・製本方式）
cover/
  cover-book.png         表紙（採用版）
  back-book.png          裏表紙（採用版）
  spine-book.png         背表紙（採用版）
  fix-ledger.md          採用中の fix 入力台帳
  cover-data.py          表紙生成スクリプト
  print/                 A5 印刷用アセット（300dpi）
  print-b5/              B5 印刷用アセット（300dpi）
  _candidates/           原本・生データ保管（AI生成画像等、加工前）
  _fixed/                採用済み加工版（各サイズ版含む）
  _work/                 一時ワークスペース（git管理しない）
dist/
  A5/
    電子版.pdf
    製本版/
      pdf/  本文.pdf, 表紙.pdf, 裏表紙.pdf, ネットプリント.pdf
      raw/  表紙.png, 裏表紙.png, 背表紙.png
  B5/
    （同じ構成）
```

## 画像管理の違い

| 項目 | Vivliostyle | Re:VIEW |
|------|-------------|---------|
| 本文画像の置き場 | `assets/` | `book/images/` |
| 原稿からの参照 | `![](../../assets/xxx.png)` | `@<image>{xxx}` |
| 表紙ビルド入力 | `cover/cover-book.png` | `book/images/cover.png` + `cover-a5.pdf` |
| 裏表紙ビルド入力 | `cover/back-book.png` | `book/images/backcover.png` |
| ビルド生成物の混在 | なし | `book/images/` に混在（手動編集禁止） |

## 表紙アセット運用

- `cover/` 直下には正本と生成スクリプトだけ置く
- `cover/_candidates/` = 原本・生データ保管（AI生成画像等、加工前のオリジナル）
- `cover/_fixed/` = 採用済み加工版（ビルド入力、各サイズ版含む）
- 現在採用している fix 入力は `cover/fix-ledger.md` に記録する
- 一時物は `cover/_work/` に置く（git管理しない）

詳細は `../.github-private/org-root/build-and-asset-guide.md` を参照。

## ビルド・配布コマンド

```bash
make build       # フルビルド（索引 → PDF → 表紙）
make ship        # dist/ にA5+B5両方を生成（デフォルト）
make ship-a5     # A5のみ
make ship-b5     # B5のみ
make preflight   # dist/ 全サイズのPDFを自動検証
make spread      # 見開きプレビュー画像を生成
```

### ship の処理フロー

1. git commit & push（作業中の変更を保存）
2. dist/{指定サイズ}/ をクリーン
3. ビルド & dist配置
4. git commit & push（生成物を記録）

### Vivliostyle 固有

```bash
make vivliostyle       # PDF組版のみ（原稿確認用）
make cover-b5-prep     # B5表紙をImageMagickで生成（初回のみ）
```

はじめに（preface）は独立ビルドされる:
- `vivliostyle.preface.js` + `theme/preface.css` で独立PDF生成
- ローマ数字ノンブル（i, ii, iii...）
- ship.py が本文PDFと結合して電子版を生成

### Re:VIEW 固有

```bash
cd book && bundle exec review-pdfmaker config.yml  # 直接ビルド
```

- 表紙は `config.yml` の `coverimage` で book.pdf に含まれる
- 裏表紙は ship.py が qpdf で後付け
- `backcover` 設定は null（遊び紙防止）

## 章を追加するとき

### Vivliostyle

1. `manuscript/chXX/main.md` を作成
2. `vivliostyle.config.js` の `entry` に追記
3. `make vivliostyle` で確認

### Re:VIEW

1. `book/chXX.re` を作成
2. `book/catalog.yml` の `CHAPS` に追記
3. `cd book && bundle exec review-pdfmaker config.yml` で確認

## ページ数調整

**遊び紙や空白ページではなく、コンテンツで対処する。**

| 状況 | 対処の優先順位 |
|------|-------------|
| 目標より少ない | ①薄い章にTips・具体例を追加 → ②afterword/colophon を充実 |
| 目標より多い | ①冗長表現の圧縮 → ②図のサイズを縮小 |
| 4の倍数でない | コンテンツ追加で調整（`make preflight` で検出） |
| スカスカページ | 章末にTipsコラムを追加（`make preflight` で検出） |

## 執筆スタイルについて

このテンプレートは執筆スタイルを規定しない。
著者自身のルールを各書籍の `CLAUDE.md` に追記して使うこと。
