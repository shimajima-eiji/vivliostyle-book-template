"""
用紙サイズ定義。ship.py, preflight-check.py, print_specs.py から参照される。
新しいサイズを追加する場合はここに追記するだけで全スクリプトに反映される。
"""

# JIS規格の実寸（mm）
# VivliostyleのB5はISO B5(176x250)を使うため、JIS B5は実寸指定が必要
PAPER_SIZES = {
    "a4": {"mm": (210, 297), "css": "A4",          "config": "A4",          "review": "a4"},
    "a5": {"mm": (148, 210), "css": "A5",          "config": "A5",          "review": "a5"},
    "a6": {"mm": (105, 148), "css": "A6",          "config": "A6",          "review": "a6"},
    "b5": {"mm": (182, 257), "css": "182mm 257mm", "config": "182mm 257mm", "review": "b5"},
}
