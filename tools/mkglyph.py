# -*- coding: utf-8 -*-
"""한글 글리프를 26x26 셀(잉크 24x24, 값 0..3)로 만든다."""
from PIL import Image, ImageFont, ImageDraw

PITCH = 26
INK = 24          # 원본 실측: 잉크 x 1..24 / y 1..24
OX = OY = 1

FONTS = {
    'nanum':     r"C:\claude\utils\font\nanum-gothic\NanumGothic.ttf",
    'nanumb':    r"C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf",
    'mulmaru':   r"C:\claude\utils\font\Mulmaru\Mulmaru.ttf",
    'galmuri11': r"C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf",
}

_cache = {}
def _font(name, size):
    k = (name, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FONTS[name], size)
    return _cache[k]

def render(ch, name='nanum', size=24, gamma=1.0, ox=0, oy=0):
    """26x26 셀(값 0..3) 반환. 글자를 잉크 상자 24x24 안에 중앙 정렬한다."""
    big = Image.new('L', (INK * 4, INK * 4), 0)
    f = _font(name, size * 4)
    d = ImageDraw.Draw(big)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text((-bb[0] + (INK * 4 - (bb[2] - bb[0])) // 2,
            -bb[1] + (INK * 4 - (bb[3] - bb[1])) // 2), ch, font=f, fill=255)
    small = big.resize((INK, INK), Image.LANCZOS)
    px = small.load()
    cell = [[0] * PITCH for _ in range(PITCH)]
    for y in range(INK):
        for x in range(INK):
            v = px[x, y] / 255.0
            if gamma != 1.0:
                v = v ** gamma
            q = int(v * 3 + 0.5)
            cy, cx = OY + y + oy, OX + x + ox
            if 0 <= cy < PITCH and 0 <= cx < PITCH:
                cell[cy][cx] = max(0, min(3, q))
    return cell

def cell_to_image(cell, scale=1):
    im = Image.new('L', (PITCH, PITCH))
    p = im.load()
    for y in range(PITCH):
        for x in range(PITCH):
            p[x, y] = cell[y][x] * 85
    return im.resize((PITCH * scale, PITCH * scale), Image.NEAREST) if scale > 1 else im
