# -*- coding: utf-8 -*-
"""生成 PWA 图标: 深色圆底 + 红点(车站符号), 与CSS .brand-mark 一致"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'icons')
os.makedirs(OUT, exist_ok=True)


def make(size, path):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆角方块底
    r = size * 0.22
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(26, 26, 46, 255))
    # 外圈(白色细环) + 内圈(红点): 车站符号
    cx = cy = size / 2
    d.ellipse([cx - size * 0.30, cy - size * 0.30, cx + size * 0.30, cy + size * 0.30],
              outline=(255, 255, 255, 255), width=max(2, size // 28))
    d.ellipse([cx - size * 0.13, cy - size * 0.13, cx + size * 0.13, cy + size * 0.13],
              fill=(230, 57, 70, 255))
    img.save(path, 'PNG')


make(192, os.path.join(OUT, 'icon-192.png'))
make(512, os.path.join(OUT, 'icon-512.png'))
print('icons written')
