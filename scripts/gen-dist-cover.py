import sys
import os
from PIL import Image

# テンプレートのパスを取得してインポートに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
template_cover_dir = os.path.join(os.path.dirname(script_dir), 'cover')
if os.path.exists(template_cover_dir):
    sys.path.append(template_cover_dir)

import print_specs

def generate(book_dir):
    src = os.path.join(book_dir, 'cover/cover-book.png')
    dst = os.path.join(book_dir, 'cover/cover.jpeg')
    
    if not os.path.exists(src):
        print(f"Source not found: {src}")
        return

    img = Image.open(src)
    # デジタル用解像度にリサイズ
    img = img.resize((print_specs.DIGITAL_W_PX, print_specs.DIGITAL_H_PX), Image.Resampling.LANCZOS)
    img.convert('RGB').save(dst, 'JPEG', quality=85)
    print(f"Generated digital cover: {dst} ({print_specs.DIGITAL_W_PX}px width)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate(sys.argv[1])
    else:
        generate(os.getcwd())
