# md2re 変換ガイド

## 概要

Markdownで執筆した原稿をRe:VIEW（.re）に変換する。機械的な構造変換はスクリプトで、文脈依存の変換はLLMで行う。

## 使い方

```bash
# 単一ファイル
make convert FILE=manuscript/ch01.md   # → book/ch01.re

# ディレクトリ一括
make convert                           # manuscript/ → book/ 全ファイル

# 直接実行
python book-template/scripts/md2re.py manuscript/ch01.md book/ch01.re
python book-template/scripts/md2re.py manuscript/ book/
```

## スクリプトが変換するもの

| Markdown | Re:VIEW | 備考 |
|----------|---------|------|
| `# 見出し` | `= 見出し` | `##` → `==`, `###` → `===` |
| `**太字**` | `@<b>{太字}` | |
| `*イタリック*` | `@<i>{イタリック}` | |
| `` `code` `` | `@<code>{code}` | |
| ` ```lang ` | `//emlist[lang]{` | コードブロック |
| `![alt](path)` | `//image[name][alt]` | パスからファイル名を自動抽出 |
| `[text](url)` | `@<href>{url,text}` | |
| `- item` | ` * item` | |
| `1. item` | ` 1. item` | |
| `---` | `//hr` | |
| Markdownテーブル | `//table{}` | |

## LLMが後処理するもの

スクリプト変換後、以下をLLMに依頼する。

### 索引（必須）

本文中のキーワードに`@<hidx>{}`を付与する。

```
# 変換前
Vue.jsは、UIを構築するためのフレームワークです。

# LLM後処理後
@<hidx>{Vue.js}Vue.jsは、@<hidx>{UI}UIを構築するための@<hidx>{フレームワーク}フレームワークです。
```

**LLMへの指示例:**
```
book/ch01.re を読んで、読者が索引から引きそうなキーワードに @<hidx>{} を付けてください。
対象: 技術用語、ツール名、概念名。一般的な日本語（「方法」「理由」等）には付けない。
1章あたり15〜30語が目安。
```

### 注釈・コラム（任意）

補足説明を`//note{}`で囲む。

```
//note[SPAとは？]{
ページ遷移なしで画面を書き換えるWebアプリの仕組み。
//}
```

**LLMへの指示例:**
```
book/ch01.re を読んで、初心者が「ここ何？」と思いそうな用語に //note[用語]{説明//} を追加してください。
1章あたり2〜4個が目安。入れすぎると読みにくくなる。
```

### コラム（任意）

本題から外れるが有用な話題を`//column{}`で囲む。

```
//column[Vue 2とVue 3の違い]{
ネットで検索するとVue 2の記事がまだ多い。見分け方は...
//}
```

### Tips（空白ページ対策）

章末に空白ができる場合、Tipsコラムを追加して埋める。

```
//note[Tips: 困ったときの調べ方]{
エラーメッセージが出たら、そのままコピーして検索窓に貼ってみましょう。
//}
```

**LLMへの指示例:**
```
make preflight でスカスカページが検出されました。
book/ch01.re の末尾にTipsを1〜2個追加して空白を埋めてください。
内容は章のテーマに関連する実用的なアドバイスにしてください。
```

## Re:VIEW 記法で注意すること

### インラインコマンドのネスト禁止

```
# NG: @<b>{} の中に @<code>{} は入れられない
@<b>{③@<code>{.value}の付け忘れ}

# OK: テキストとして書く
③ .valueの付け忘れ——@<code>{<script>}の中で...
```

### 波カッコのエスケープ

Re:VIEWのインラインコマンド内で `}` を使うときは `\}` にエスケープする。
`//emlist` 等のブロック内ではエスケープ不要。

```
@<code>{{{ count \}\}}    # テンプレート構文の表示
```

### 画像の参照

`@<image>{name}` の `name` は `book/images/name.png` の拡張子なしファイル名。
パスは書かない。

## 変換後の確認手順

```bash
make convert                    # md→re変換
# LLMで索引・注釈を後処理
cd book && bundle exec review-pdfmaker config.yml  # ビルド確認
make ship                       # dist生成
make preflight                  # 品質検証
```
