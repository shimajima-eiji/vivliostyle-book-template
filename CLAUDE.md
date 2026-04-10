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
assets/
  chapter-data.py   章扉画像データ定義（make chapters で chapter-XX.png を生成）
  chapter-XX.png    章扉画像（原稿の ![](../../assets/chapter-XX.png){.chapter-image} で参照）
  diagrams/         図解画像（採用版。D2/Mermaid等で生成）
scripts/
  index-terms.yaml  索引用語リスト（手動管理）
theme/
  book.css      Vivliostyle テーマ（A5縦型）
cover/
  cover-book.png  表紙画像（make cover-img で生成）
dist/
  book-digital.pdf            本文PDF
  book-digital-with-cover.pdf 表紙込みPDF（配布用）
```

## 表紙アセット運用

- `cover/` 直下には正本と生成スクリプトだけ置く
- 候補は `cover/_candidates/`
- 人手で補正した採用元は `cover/_fixed/`
- 現在採用している fix 入力は `cover/fix-ledger.md` に記録する
- 一時物は `cover/_work/` に置き、`incoming` `scratch` `compare` `preview` を使い分ける
- `_work` 直下にファイルを直置きしない
- 複数書籍で使うツールは `book-template/tools/` に置く
- 横断の完全一時物は `/tmp/nomuraya-books/` を使う
- オーガニゼーション直下に `tmp/` や `tmp-*` を増やさない

詳細は `../.github-private/org-root/build-and-asset-guide.md` を参照。

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
3. `assets/chapter-data.py` の `CHAPTERS` / `TITLE_LINES` にエントリを追加
4. `make chapters` で `assets/chapter-XX.png` を生成
5. `manuscript/chXX/main.md` の冒頭に章扉タグを追加:
   ```markdown
   ![](../../assets/chapter-XX.png){.chapter-image}
   ```
6. `make vivliostyle` で確認

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

---

## AIへの依頼例（プロンプト集）

迷ったときはここを見る。

### 執筆

```
manuscript/ch01/main.md を読んで、[テーマ] について1500字程度で肉付けしてくれ。
体験ベース・具体例必須。執筆ルールに従うこと。
```

```
ch02/main.md の構成を提案してくれ。テーマは [テーマ]。
全体の流れは vivliostyle.config.js のエントリ順を参照。
```

### ページ数調整

```
make validate を実行したら [X]p だった。[目標ページ数] にしたい。
増やすなら manuscript/ の既存章に追記する方向で提案してくれ。削除は避ける。
```

### 索引管理

```
make validate の未登録頻出語リストを見て、scripts/index-terms.yaml に追加すべき用語を判断して反映してくれ。
```

```
索引ヒットなし用語: [用語名] が出た。本文を検索して原因を調べ、
index-terms.yaml の patterns を修正するか、本文側を修正するか判断して対処してくれ。
```

### 章追加

```
第[X]章を追加したい。テーマは [テーマ]。
manuscript/chXX/main.md の作成と vivliostyle.config.js への追記まで一括でやってくれ。
```

### 価格・入稿確認

```
make validate を実行して結果を報告してくれ。
ページ数・索引・印刷費参考値の3点について問題があれば対処方針も出してくれ。
```
