"""
A5 印刷用およびデジタル頒布用の共通仕様。
"""

from __future__ import annotations
import math

# --- 印刷用高解像度 (Master / Print) ---
PRINT_DPI = 300
TRIM_W_MM = 148.0
TRIM_H_MM = 210.0
BLEED_MM = 3.0

PX_PER_MM = PRINT_DPI / 25.4
TRIM_W_PX = round(TRIM_W_MM * PX_PER_MM)   # 1748
TRIM_H_PX = round(TRIM_H_MM * PX_PER_MM)   # 2480
BLEED_PX = math.ceil(BLEED_MM * PX_PER_MM) # 36

# --- デジタル用低解像度 (Digital / Web) ---
DIGITAL_DPI = 72
DIGITAL_PX_PER_MM = DIGITAL_DPI / 25.4
DIGITAL_W_PX = round(TRIM_W_MM * DIGITAL_PX_PER_MM) # 420
DIGITAL_H_PX = round(TRIM_H_MM * DIGITAL_PX_PER_MM) # 595

# プレビュー用中間解像度 (Preview)
PREVIEW_DPI = 150
PREVIEW_PX_PER_MM = PREVIEW_DPI / 25.4
PREVIEW_W_PX = round(TRIM_W_MM * PREVIEW_PX_PER_MM) # 874
PREVIEW_H_PX = round(TRIM_H_MM * PREVIEW_PX_PER_MM) # 1240

def mm_to_px(mm: float, dpi: int = PRINT_DPI) -> int:
    return max(1, round(mm * (dpi / 25.4)))
