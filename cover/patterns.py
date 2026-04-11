"""
幾何学的なパターンを生成するユーティリティモジュール
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def create_dot_grid(width, height, spacing=40, dot_size=2, color=(255, 255, 255, 30)):
    """規則正しいドットの方眼を生成"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for x in range(0, width, spacing):
        for y in range(0, height, spacing):
            draw.ellipse([x, y, x + dot_size, y + dot_size], fill=color)
    return img

def create_math_waves(width, height, color=(255, 255, 255, 20)):
    """数理的なサイン波の重ね合わせ（思考のフローを表現）"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    points = []
    for x in range(0, width, 5):
        # 複数の周波数を合成
        y = height * 0.7 + \
            math.sin(x * 0.005) * 50 + \
            math.sin(x * 0.01) * 20
        points.append((x, y))
    
    draw.line(points, fill=color, width=2)
    return img

import math # waveで使用

def create_grain(width, height, intensity=20):
    """印刷物のような微細なノイズ質感を加える"""
    # numpyで高速生成
    noise = np.random.randint(-intensity, intensity, (height, width, 4), dtype=np.int16)
    noise[:, :, 3] = 0 # アルファチャネルはノイズに乗せない
    
    base = np.zeros((height, width, 4), dtype=np.uint8)
    # ノイズを合成
    grain = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(grain, "RGBA")
