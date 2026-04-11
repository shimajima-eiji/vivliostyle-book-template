"""
印刷用およびデジタル頒布用の共通仕様。
PAPER_SIZE 環境変数で A5/B5 を切り替え可能（デフォルト: A5）。
"""

from __future__ import annotations
import math
import os

PRINT_DPI = 300
BLEED_MM = 3.0

# 用紙サイズ定義
PAPER_SIZES = {
    "a5": (148.0, 210.0),
    "b5": (182.0, 257.0),
}

_paper = os.environ.get("PAPER_SIZE", "a5").lower()
TRIM_W_MM, TRIM_H_MM = PAPER_SIZES.get(_paper, PAPER_SIZES["a5"])

PX_PER_MM = PRINT_DPI / 25.4
TRIM_W_PX = round(TRIM_W_MM * PX_PER_MM)
TRIM_H_PX = round(TRIM_H_MM * PX_PER_MM)
BLEED_PX = math.ceil(BLEED_MM * PX_PER_MM)

# デジタル用低解像度
DIGITAL_DPI = 72
DIGITAL_PX_PER_MM = DIGITAL_DPI / 25.4
DIGITAL_W_PX = round(TRIM_W_MM * DIGITAL_PX_PER_MM)
DIGITAL_H_PX = round(TRIM_H_MM * DIGITAL_PX_PER_MM)

# プレビュー用中間解像度
PREVIEW_DPI = 150
PREVIEW_PX_PER_MM = PREVIEW_DPI / 25.4
PREVIEW_W_PX = round(TRIM_W_MM * PREVIEW_PX_PER_MM)
PREVIEW_H_PX = round(TRIM_H_MM * PREVIEW_PX_PER_MM)

def mm_to_px(mm: float, dpi: int = PRINT_DPI) -> int:
    return max(1, round(mm * (dpi / 25.4)))
