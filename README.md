# vivliostyle-book-template

Markdownで原稿を書き、VivliostyleでPDFに変換する同人誌制作テンプレート。

## 必要なもの

- [mise](https://mise.jdx.dev/)（Node.jsバージョン管理）
- [uv](https://docs.astral.sh/uv/)（Python実行環境）
- ImageMagick（表紙結合に使用）
- poppler（pdfinfo・pdfunite、ページ数チェック・表紙結合に使用）

```bash
# macOS
brew install mise uv imagemagick poppler

# mise で Node.js をインストール（mise.toml で node=24 を指定済み）
mise install
```

## セットアップ

```bash
# 1. このリポジトリをclone（book-template という名前で置く）
git clone https://github.com/shimajima-eiji/vivliostyle-book-template book-template

# 2. 自分の書籍リポジトリを同じ階層に作る
mkdir my-book && cd my-book
git init

# 3. book-template からファイルをコピーして初期化
cp -r ../book-template/. .
bash scripts/init.sh
```

ディレクトリ構成はこうなる：

```
workspace/
  book-template/   ← このリポジトリ（触らない）
  my-book/         ← 自分の書籍リポジトリ
```

## 初期化後の作業

1. `vivliostyle.config.js` で章エントリを設定
2. `manuscript/ch01/main.md` から執筆開始
3. `make build` でPDF生成

```bash
make build        # フルビルド（索引 → PDF → 表紙結合）
make vivliostyle  # 組版のみ（原稿確認用）
make index        # 索引のみ再生成
```

生成物は `dist/book-digital-with-cover.pdf`。

## 書籍設定

`book.yaml` で書籍固有の設定を管理する。

```yaml
title: "書名"
author: "著者名"

cover:
  title_line1: "書名1行目"
  title_line2: "書名2行目"  # 不要なら空文字
  subtitle_line1: ""
  subtitle_line2: ""
  font_size_title: 110
  bg_image: "cover/bg_draft.png"

css:
  chapter_image: false  # 章扉画像を使う場合は true
```

## 表紙・章扉画像

Pillowで生成する場合は以下のスクリプトを書籍側に置く：

| ファイル | 用途 |
|---------|------|
| `cover/cover-data.py` | 表紙画像生成（`cover/cover-book.png` を出力） |
| `assets/chapter-data.py` | 章扉画像生成（`assets/chapter-XX.png` を出力） |

各スクリプトは `book-template` のベーススクリプトを参照する：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "cover"))
from gen_cover_base import generate
```

## 表紙アセットの置き場ルール

表紙まわりは「採用版」「候補」「補正版」「一時物」を混ぜない。

```text
cover/_work/    その書籍の一時ワークスペース
  incoming/     受領直後の一時置き場
  scratch/      中間変換・試作
  compare/      比較画像
  preview/      repo専用の確認物
cover/_candidates/  外部ツールや生成候補。git管理する
cover/_fixed/   補正版・採用元マスター。git管理する
cover/fix-ledger.md  採用中のfix入力と生成経路の台帳
cover/          ビルドが参照する正本だけ置く
cover/print/    印刷用の生成物
book-template/tools/  複数書籍で使う確認ツール
/tmp/nomuraya-books/  完全に使い捨ての横断比較物
```

- `cover/cover-book.png` `cover/back-book.png` `cover/spine-book.png` が正本
- `cover/fix-ledger.md` に「今どの fix 入力を採用しているか」を書く
- `copy` `final2` のような曖昧名を作らない
- `_work` 直下にファイルを直置きしない
- オーガニゼーション直下に `tmp/` や `tmp-*` を作らない
- 詳細運用は [`.github-private/org-root/build-and-asset-guide.md`](../.github-private/org-root/build-and-asset-guide.md) を参照

## ライセンス

MIT
