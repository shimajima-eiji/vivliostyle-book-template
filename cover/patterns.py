"""
幾何学的なパターンを生成するユーティリティモジュール
"""
import numpy as np
import math
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
        y = height * 0.7 + math.sin(x * 0.005) * 50 + math.sin(x * 0.01) * 20
        points.append((x, y))
    draw.line(points, fill=color, width=2)
    return img

def create_grain(width, height, intensity=20):
    """印刷物のような微細なノイズ質感を加える"""
    noise = np.random.randint(-intensity, intensity, (height, width, 4), dtype=np.int16)
    noise[:, :, 3] = 0
    base = np.zeros((height, width, 4), dtype=np.uint8)
    grain = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(grain, "RGBA")

def create_network(width, height, nodes=15, color=(255, 255, 255, 12)):
    """知識の繋がりを表現するランダムなネットワークグラフ"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    points = np.random.randint(150, [width-150, height-150], (nodes, 2))
    for i in range(nodes):
        for j in range(i + 1, nodes):
            dist = np.linalg.norm(points[i] - points[j])
            if dist < 800:
                draw.line([tuple(points[i]), tuple(points[j])], fill=color, width=1)
    for p in points:
        draw.ellipse([p[0]-4, p[1]-4, p[0]+4, p[1]+4], fill=color)
    return img

def create_frame_accent(width, height, color=(255, 255, 255, 35)):
    """実務書らしい「角」や「端」を強調するライン装飾"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 100
    length = 300
    draw.line([(margin, margin), (margin + length, margin)], fill=color, width=3)
    draw.line([(margin, margin), (margin, margin + length)], fill=color, width=3)
    draw.rectangle([width - margin - 30, height - margin - 30, width - margin, height - margin], fill=color)
    return img
