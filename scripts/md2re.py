"""
md2re.py — Markdown → Re:VIEW (.re) 変換スクリプト。

著者がMarkdownで書いた原稿をRe:VIEWフォーマットに変換する。
構造的な変換（見出し・太字・コード等）はスクリプトで機械的に処理し、
文脈依存の変換（索引・注釈等）はLLMで後処理する前提。

Usage:
    python md2re.py <input.md> [output.re]
    python md2re.py manuscript/ book/     # ディレクトリ一括変換

変換される要素:
  ◎ 確実: 見出し, 太字, イタリック, インラインコード, コードブロック, リスト, リンク, 水平線
  ○ ほぼ確実: 画像, テーブル
  △ 要確認: ネストしたリスト, 複雑なテーブル
  × LLM後処理: 索引(@<hidx>), 注釈(//note), コラム(//column)
"""
import re
import sys
from pathlib import Path


def convert_md_to_re(md_text: str) -> str:
    """Markdownテキストを Re:VIEW フォーマットに変換する"""
    lines = md_text.split('\n')
    result = []
    in_code_block = False
    code_lang = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        # コードブロック
        if line.strip().startswith('```'):
            if not in_code_block:
                code_lang = line.strip()[3:].strip()
                lang_label = f"[{code_lang}]" if code_lang else ""
                result.append(f"//emlist{lang_label}{{")
                in_code_block = True
            else:
                result.append("//}")
                in_code_block = False
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # 見出し
        m = re.match(r'^(#{1,5})\s+(.+)$', line)
        if m:
            level = len(m.group(1))
            title = _convert_inline(m.group(2))
            prefix = '=' * level
            result.append(f"{prefix} {title}")
            i += 1
            continue

        # 水平線
        if re.match(r'^---+\s*$', line) or re.match(r'^\*\*\*+\s*$', line):
            result.append("//hr")
            i += 1
            continue

        # 画像
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if m:
            alt = m.group(1)
            path = m.group(2)
            # パスからファイル名（拡張子なし）を取得
            name = Path(path).stem
            if alt:
                result.append(f"//image[{name}][{alt}]")
            else:
                result.append(f"//image[{name}][]")
            i += 1
            continue

        # 順序なしリスト
        m = re.match(r'^(\s*)[*-]\s+(.+)$', line)
        if m:
            indent = len(m.group(1)) // 2
            text = _convert_inline(m.group(2))
            prefix = ' *' * (indent + 1)
            result.append(f"{prefix} {text}")
            i += 1
            continue

        # 順序ありリスト
        m = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if m:
            indent = len(m.group(1)) // 2
            text = _convert_inline(m.group(2))
            prefix = ' 1.' if indent == 0 else '  ' * indent + ' 1.'
            result.append(f"{prefix} {text}")
            i += 1
            continue

        # テーブル（簡易対応）
        if '|' in line and i + 1 < len(lines) and re.match(r'^\|[-:|]+\|', lines[i + 1]):
            result.extend(_convert_table(lines, i))
            # テーブルの終わりまでスキップ
            while i < len(lines) and '|' in lines[i]:
                i += 1
            continue

        # 通常テキスト
        result.append(_convert_inline(line))
        i += 1

    return '\n'.join(result)


def _convert_inline(text: str) -> str:
    """インライン要素を変換する"""
    # 太字+イタリック (***text***)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'@<b>{@<i>{\1}}', text)
    # 太字 (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'@<b>{\1}', text)
    # イタリック (*text*)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'@<i>{\1}', text)
    # インラインコード (`code`)
    text = re.sub(r'`([^`]+)`', r'@<code>{\1}', text)
    # リンク [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'@<href>{\2,\1}', text)
    return text


def _convert_table(lines: list[str], start: int) -> list[str]:
    """Markdownテーブルを Re:VIEW テーブルに変換する"""
    result = []
    header = lines[start]
    # ヘッダー行のセルを取得
    cells = [c.strip() for c in header.split('|')[1:-1]]
    # セパレータ行をスキップ（start+1）
    result.append(f"//table[][]{{")
    result.append('\t'.join(cells))
    result.append('-' * 20)
    # データ行
    i = start + 2
    while i < len(lines) and '|' in lines[i]:
        row = [c.strip() for c in lines[i].split('|')[1:-1]]
        result.append('\t'.join(_convert_inline(c) for c in row))
        i += 1
    result.append("//}")
    return result


def convert_file(input_path: Path, output_path: Path):
    """1ファイルを変換する"""
    md_text = input_path.read_text(encoding='utf-8')
    re_text = convert_md_to_re(md_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(re_text, encoding='utf-8')
    print(f"  {input_path.name} → {output_path.name}")


def main():
    if len(sys.argv) < 2:
        print("Usage: md2re.py <input.md> [output.re]")
        print("       md2re.py <manuscript_dir/> <book_dir/>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if input_path.is_dir():
        # ディレクトリ一括変換
        out_dir = output_path or input_path.parent / "book"
        md_files = sorted(input_path.glob("**/*.md"))
        md_files = [f for f in md_files if f.name not in ("README.md", "CLAUDE.md")]
        if not md_files:
            print(f"変換対象のmdファイルがありません: {input_path}")
            sys.exit(1)
        print(f"📝 md→re 変換: {len(md_files)}ファイル")
        for md_file in md_files:
            rel = md_file.relative_to(input_path)
            re_file = out_dir / rel.with_suffix('.re')
            convert_file(md_file, re_file)
    else:
        # 単一ファイル変換
        if output_path is None:
            output_path = input_path.with_suffix('.re')
        print(f"📝 md→re 変換")
        convert_file(input_path, output_path)

    print("✅ 変換完了")
    print("   ⚠️ 索引(@<hidx>)・注釈(//note)・コラム(//column)はLLMで後処理してください")


if __name__ == "__main__":
    main()
