# vivliostyle-book-template

[English](./README.md)

Markdown で原稿を書けば、印刷所にそのまま渡せる PDF ができる。
[Vivliostyle](https://vivliostyle.org/)（CSS 組版）の上に作った同人誌・自費出版テンプレートで、
原稿はプレーンな Markdown のまま、索引・表紙・背表紙・面付けはすべて `make` が生成する。

同じテンプレートで [Re:VIEW](https://reviewml.org/) ビルドも回せる。`book/config.yml` を置けば
エンジンがフォーマットを自動で切り替えるので、Markdown で書き始めて、ツールチェーンを変えずに
Re:VIEW へ移行できる。

ソースを DTP アプリではなく Git に置いておきたい、インディー作家・技術系の自費出版者向け。

[![License: MIT](https://img.shields.io/badge/License-MIT-2a5298.svg?style=flat-square)](#ライセンス)
![Node 24](https://img.shields.io/badge/node-24-339933?style=flat-square&logo=node.js&logoColor=white)
![Vivliostyle](https://img.shields.io/badge/Vivliostyle-CSS%20typesetting-b21f1f?style=flat-square)

## このテンプレートの狙い

自費出版のツールチェーンは、たいてい二者択一を迫る。WYSIWYG エディタで書く（差分も Git も自動化もない）か、
数か月かけて LaTeX と格闘するか。このテンプレートは第三の道をとる。**原稿は Markdown、組版は CSS** に任せる。
きれいな差分、スクリプト化できるビルド、印刷所に出せる PDF が手に入る。

- **原稿は Markdown のまま。** 各章は `manuscript/` に置く。バイナリは持たない。
- **ビルドは 1 コマンド。** `make build` が CSS → 索引 → 章 → 組版 → 表紙 を通す。
- **表紙・背表紙・裏表紙は生成物。** 手で配置しないので、ズレない。
- **印刷所向けの成果物を自動で組む** — 本文・表紙・裏表紙・ネットプリント用 PDF を A5 と B5 で、`make ship` 一発。
- **2 フォーマット、1 ワークフロー。** 既定は Vivliostyle（CSS）。`book/config.yml` を置けば Re:VIEW（LaTeX）。
  エンジンがどちらを使っているか自動判定する。

## 必要なもの

| ツール | 用途 |
|------|------|
| [mise](https://mise.jdx.dev/) | Node.js のバージョン管理（Node 24 に固定） |
| [uv](https://docs.astral.sh/uv/) | 表紙・索引・ビルドスクリプト用の Python 実行環境 |
| ImageMagick（`magick`） | 表紙アートワークのリサイズ・結合 |
| poppler / qpdf | `pdfinfo`・`qpdf`。ページ数チェックと PDF 結合 |

```bash
# macOS
brew install mise uv imagemagick poppler qpdf
mise install   # mise.toml で固定した Node 24 をインストール
```

> Re:VIEW ビルドには別途 Ruby + Re:VIEW + TeX Live のツールチェーン
> （`bundle exec review-pdfmaker`）が要る。Vivliostyle 経路には不要。

## セットアップ

このリポジトリは **コピー元のテンプレート** であって、ここを直接いじるものではない。
自分の書籍リポジトリの隣に置いておき、書籍側から `Makefile.engine` と共有の表紙・索引スクリプトを参照する：

```bash
# 1. テンプレートを "book-template" という名前で clone
git clone https://github.com/shimajima-eiji/vivliostyle-book-template book-template

# 2. 自分の書籍リポジトリを同じ階層に作る
mkdir my-book && cd my-book
git init

# 3. テンプレートのファイルをコピーして初期化
cp -r ../book-template/. .
bash scripts/init.sh
```

`scripts/init.sh` がタイトルと著者を聞き、プレースホルダを埋め、`Makefile` を
`../book-template/Makefile.engine` を include する形に書き換える。できあがる構成：

```
workspace/
  book-template/   # このリポジトリ — 触らない
  my-book/         # 自分の書籍リポジトリ
```

## 執筆

1. `vivliostyle.config.js` で章エントリを定義する。
2. `manuscript/ch01/main.md` から書き始める。
3. ビルド：

```bash
make build         # フルビルド: CSS -> 索引 -> 章 -> 組版 -> 表紙
make vivliostyle   # 組版のみ（執筆中の素早い確認用）-> dist/book-digital.pdf
make index         # 索引のみ再生成
```

`make vivliostyle` は `dist/book-digital.pdf` を生成する。印刷所向けの一式
（本文 + 表紙 + ネットプリント、判型ごと）は `make ship` から作る — 後述。

## 書籍設定

書籍ごとの設定は `book.yaml` に置く：

```yaml
title: "書名"
author: "著者名"

cover:
  title_line1: "書名 1 行目"
  title_line2: ""              # 不要なら空文字
  subtitle_line1: ""
  subtitle_line2: ""
  font_size_title: 110
  bg_image: "cover/_fixed/front-source.png"  # 採用元の canonical source

css:
  chapter_image: false   # 章扉画像を使うなら true

print:
  binding: "wireless"    # "wireless" = 無線綴じ（2 の倍数ページ）
                         # "saddle"   = 中綴じ（4 の倍数ページ）
```

## 表紙・背表紙・章扉画像

表紙アートワークは `make cover-assets` で一括更新する（front / back / spine / preview / print を通す）。
生成をカスタムするなら、以下のスクリプトを書籍側に置く。各スクリプトはテンプレート共有のベース生成器を呼ぶ：

| ファイル | 生成物 |
|------|------|
| `cover/cover-data.py`       | front（`cover/cover-book.png`） |
| `cover/back-cover-data.py`  | back（`cover/back-book.png`） |
| `cover/spine-data.py`       | spine（`cover/spine-book.png`） |
| `assets/chapter-data.py`    | 章扉画像（`assets/chapter-XX.png`） |

各スクリプトはテンプレートのベース生成器を import する（`init.sh` が
`assets/chapter-data.py` を雛形として用意する）：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "book-template" / "cover"))
from gen_cover_base import generate
```

## 印刷所向け PDF のビルド

`make ship` は本を組み上げ、印刷所が必要とする一式を `dist/<SIZE>/` の下に配置する：

```bash
make ship      # A5 と B5 をビルド（既定）
make ship-a5   # A5 のみ
make ship-b5   # B5 のみ
```

判型ごとの出力構成（例: A5）：

```
dist/A5/
  電子版.pdf            # 電子版: 表紙 + 本文 + 裏表紙
  製本版/               # 製本版
    pdf/  本文.pdf 表紙.pdf 裏表紙.pdf ネットプリント.pdf
    raw/  表紙.png 裏表紙.png 背表紙.png
```

`ship` は結果を commit & push もする（Git リポジトリ内で動かす前提）。
B5 は、最初の `make ship-b5` の前に一度だけ `make cover-b5-prep` で B5 表紙マスターを生成しておく。

## 出力の検証

```bash
make preflight   # dist/ 内の全 PDF を検査（ページ数・空白ページ・綴じの倍数）
make spread      # 見開きプレビューを生成
```

`preflight` は `book.yaml` の `print.binding` を読み、ページ数が正しい倍数
（無線綴じ = 2、中綴じ = 4）になっているか検証する。これできれいに折れる。

## Re:VIEW フォーマット（任意）

Re:VIEW / LaTeX で組みたいなら、Markdown を変換すればエンジンが自動でフォーマットを
切り替える — `book/config.yml` があれば Re:VIEW と判定する：

```bash
make convert     # manuscript/*.md を Re:VIEW（.re）に変換し book/ 配下に出力
make ship        # 同じ ship パイプラインを Re:VIEW 経由で
```

`make convert` は構造変換だけを行う。索引・脚注・コラムはそのあとで足す
（LLM 後処理パスについてはプロジェクトの CLAUDE.md を参照）。

## 表紙アセットの置き場ルール

「採用版」「候補」「補正版」「一時物」を混ぜない。ビルドが誤ったファイルを拾わないようにする：

```text
cover/_work/        書籍ごとの一時ワークスペース（gitignore）
  incoming/         受領直後の一時置き場
  scratch/          中間変換・試作
  compare/          比較画像
  preview/          repo 専用の確認物
cover/_candidates/  生成・外部候補（git 管理）
cover/_fixed/       補正版マスター・採用元（git 管理）
cover/fix-ledger.md 台帳: 今どの fixed 入力を採用しているか
cover/              ビルドが参照する正本だけ置く
cover/print/        印刷解像度の出力（A5）。B5 は cover/print-b5/
```

ルール：

- `cover/cover-book.png`・`cover/back-book.png`・`cover/spine-book.png` が、ビルドの読む正本。
- 採用中の入力は `cover/fix-ledger.md` に記録する。
- `copy` や `final2` のような曖昧名を作らない。
- `_work/` 直下にファイルを直置きしない。

## ライセンス

MIT
