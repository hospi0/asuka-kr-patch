# -*- coding: utf-8 -*-
"""타이틀 로고를 한글로 다시 «그린다» (DATABG: logoonly / demo00 / package).

원본 실측 (logoonly 640x512, ARGB4444):
  1행 「不思議のダンジョン」 y 88-120  x200-470  검정
  2행 「風来のシレン外伝」  y122-190  x170-470  진홍(168,0,24) + 검정 윤곽 + 흰 하이라이트
  3행 「女剣士アスカ見参!」 y195-310  x 40-608
       女剣士 / 見参!  남보라(48,48,120) + 흰 윤곽(216,216,216) + 검정 그림자
       アスカ          빨강→주황→노랑 세로 그라디언트 + 흰 윤곽 + 검정 윤곽

★폰트를 그대로 얹지 않는다 — 기울이고(이탤릭), 획을 부풀리고, 층층이 윤곽을 쌓아
  원본의 «그린 글자» 질감을 흉내낸다.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FDIR = r"C:\claude\utils\font\logo"
F_HEAVY = os.path.join(FDIR, 'BlackHanSans.ttf')   # 극태 고딕 — 아스카·던전
F_BRUSH = os.path.join(FDIR, 'Gugi.ttf')           # 붓 느낌 제목체 — 여검사·견참·풍래

RED = (176, 0, 24)
NAVY = (48, 48, 120)
WHITE = (222, 222, 222)
BLACK = (0, 0, 0)
GRAD = [(0.00, (198, 22, 22)), (0.35, (226, 104, 0)),
        (0.62, (232, 168, 0)), (1.00, (214, 92, 0))]

SKEW = -0.18          # 오른쪽으로 기우는 이탤릭


def _mask(text, font_path, h, skew=SKEW, bold=0):
    """글자를 높이 h 에 맞춘 «알파 마스크»로 만든다."""
    size = max(8, int(h * 1.25))
    for _ in range(40):
        f = ImageFont.truetype(font_path, size)
        bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f)
        if bb[3] - bb[1] <= h:
            break
        size -= 2
    pad = 24
    im = Image.new('L', (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), 0)
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255)
    if bold:
        im = im.filter(ImageFilter.MaxFilter(bold * 2 + 1))
    if skew:
        w, hh = im.size
        dx = int(abs(skew) * hh)
        im = im.transform((w + dx, hh), Image.AFFINE, (1, skew, 0 if skew > 0 else dx, 0, 1, 0),
                          resample=Image.BICUBIC)
    return im.crop(im.getbbox())


def _grow(m, r):
    return m.filter(ImageFilter.MaxFilter(r * 2 + 1))


def _fill(mask, color):
    im = Image.new('RGBA', mask.size, color + (0,))
    im.putalpha(mask)
    return im


def _grad_fill(mask):
    w, h = mask.size
    g = Image.new('RGB', (1, h))
    p = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(len(GRAD) - 1):
            a, ca = GRAD[i]
            b, cb = GRAD[i + 1]
            if a <= t <= b:
                k = (t - a) / max(1e-6, b - a)
                p[0, y] = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
                break
    g = g.resize((w, h))
    out = g.convert('RGBA')
    out.putalpha(mask)
    return out


def piece(text, font_path, box, fill, outer=BLACK, mid=WHITE,
          ow=5, mw=3, shadow=(3, 3), grad=False, bold=0):
    """상자(x0,y0,x1,y1)에 «층층이 윤곽 두른» 글자를 그려 RGBA 로 돌려준다."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    m = _mask(text, font_path, bh - (ow + mw) * 2 - 4, bold=bold)
    # 상자 폭에 맞춰 가로 조정
    sc = min((bw - (ow + mw) * 2 - 4) / m.width, 1.6)
    if sc < 1.0:
        m = m.resize((max(1, int(m.width * sc)), max(1, int(m.height * sc))), Image.LANCZOS)
    pad = ow + mw + 6
    core = Image.new('L', (m.width + pad * 2, m.height + pad * 2), 0)
    core.paste(m, (pad, pad))
    o_mask = _grow(core, ow + mw)
    m_mask = _grow(core, mw)
    lay = Image.new('RGBA', core.size, (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', core.size, (0, 0, 0, 0))
        sh.alpha_composite(_fill(o_mask, (0, 0, 0)))
        lay.alpha_composite(sh, dest=(0, 0))
        lay = Image.alpha_composite(
            Image.new('RGBA', core.size, (0, 0, 0, 0)),
            lay.transform(core.size, Image.AFFINE, (1, 0, -shadow[0], 0, 1, -shadow[1])))
    lay.alpha_composite(_fill(o_mask, outer))
    lay.alpha_composite(_fill(m_mask, mid))
    lay.alpha_composite(_grad_fill(core) if grad else _fill(core, fill))
    return lay, (x0 + (bw - lay.width) // 2, y0 + (bh - lay.height) // 2)
