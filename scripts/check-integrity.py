import sys
import os
from PIL import Image

# 規格のロード
script_dir = os.path.dirname(os.path.abspath(__file__))
template_cover_dir = os.path.join(os.path.dirname(script_dir), 'cover')
if os.path.exists(template_cover_dir):
    sys.path.append(template_cover_dir)
import print_specs

def check_book_integrity(book_path):
    cover_dir = os.path.join(book_path, 'cover')
    if not os.path.exists(cover_dir):
        return

    print(f"\n🔍 Checking Integrity: {os.path.basename(book_path)}")
    errors = []
    
    # 1. Source of Truth Check
    fixed_src = os.path.join(cover_dir, '_fixed/front-source.png')
    if not os.path.exists(fixed_src):
        # 特例（ai-writing-guide等の救済）の確認
        if os.path.exists(os.path.join(cover_dir, '_candidates/cover-book.png')):
            print("  ⚠️ Notice: Using _candidates as fallback source.")
        else:
            errors.append("  ❌ Missing SSoT: _fixed/front-source.png is gone and no candidates found.")

    # 2. Master Resolution Check (300dpi)
    for target in ['cover-book.png', 'back-book.png']:
        master_path = os.path.join(cover_dir, target)
        if os.path.exists(master_path):
            img = Image.open(master_path)
            if img.size != (print_specs.TRIM_W_PX, print_specs.TRIM_H_PX):
                errors.append(f"  ❌ Resolution Error: {target} is {img.size}, expected {print_specs.TRIM_W_PX}x{print_specs.TRIM_H_PX}")
            else:
                print(f"  ✅ {target}: 300dpi (OK)")
        else:
            errors.append(f"  ❌ Missing Master: {target}")

    # 3. Decision Log Check
    if not os.path.exists(os.path.join(cover_dir, 'fix-ledger.md')):
        errors.append("  ❌ Missing Ledger: fix-ledger.md not found.")
    else:
        print("  ✅ fix-ledger.md: (OK)")

    if errors:
        for err in errors:
            print(err)
    else:
        print("  ✨ All systems nominal.")

if __name__ == "__main__":
    books = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
    for book in books:
        if os.path.exists(os.path.join(book, 'cover')):
            check_book_integrity(os.path.abspath(book))
