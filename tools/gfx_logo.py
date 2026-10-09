# -*- coding: utf-8 -*-
"""타이틀 로고 한글판 그리기 (2026-10-09 다시 시도) — demo00(512x256) 기준 좌표로 그린 로고를
   logoonly(640x512)·package(640x512) 에도 같은 배율로 얹는다.

  원본 3줄: 「不思議のダンジョン」(검정) / 「風来のシレン外伝」(진홍 + 검정 윤곽) /
            「女剣士」「見参!」(남보라 + 흰 윤곽 + 검정 그림자) + 「アスカ」(빨강→주황→노랑 + 흰·검정 윤곽)
  한글: 이상한 던전 / 풍래의 시렌 외전 / 여검사 아스카 등장!  (README 제목과 같음)
  ★4배로 그린 뒤 LANCZOS 축소 → ARGB4444(알파 16단계)로 굽힌다(build_l40 가 인코딩).
  python tools/gfx_logo.py  → work/logo/demo00_kr.png + 비교 work/logo/비교_로고.png
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FD = r'C:\claude\utils\font'
F_HEAVY = os.path.join(FD, 'logo', 'BlackHanSans.ttf')
F_ROUND = os.path.join(FD, 'logo', 'GasoekOne-Regular.ttf')
F_BRUSH = os.path.join(FD, 'logo', 'Gugi.ttf')
F_GOTH = r'C:\Windows\Fonts\malgunbd.ttf'
S = 4                                   # 그리기 배율

RED = (172, 6, 28); NAVY = (52, 50, 128); WHITE = (232, 232, 236); BLACK = (16, 12, 20)
GRAD = [(0.00, (200, 20, 28)), (0.40, (232, 96, 8)), (0.70, (244, 170, 10)), (1.00, (226, 110, 6))]


def mask(text, font, h, skew=0.16, track=0):
    """높이 h(px, 배율 적용 후)인 글자 알파 마스크 — 기울임·자간"""
    size = int(h * 1.35)
    while True:
        f = ImageFont.truetype(font, size)
        bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f)
        if bb[3] - bb[1] <= h or size < 6:
            break
        size -= 1
    w = bb[2] - bb[0] + track * (len(text) - 1) + 40; hh = bb[3] - bb[1] + 40
    im = Image.new('L', (w, hh), 0); d = ImageDraw.Draw(im); x = 20 - bb[0]
    for ch in text:
        d.text((x, 20 - bb[1]), ch, font=f, fill=255)
        x += d.textlength(ch, font=f) + track
    if skew:
        dx = int(abs(skew) * hh)
        im = im.transform((w + dx, hh), Image.AFFINE, (1, skew, -dx if skew > 0 else 0, 0, 1, 0), resample=Image.BICUBIC)   # skew>0 = 위가 오른쪽(원본처럼)
    return im.crop(im.getbbox())


def grow(m, r):
    return m.filter(ImageFilter.MaxFilter(2 * r + 1)) if r > 0 else m


def solid(m, c):
    im = Image.new('RGBA', m.size, c + (0,)); im.putalpha(m); return im


def grad(m):
    w, h = m.size; col = np.zeros((h, 3))
    for y in range(h):
        t = y / max(1, h - 1)
        for (a, ca), (b, cb) in zip(GRAD, GRAD[1:]):
            if a <= t <= b:
                k = (t - a) / (b - a); col[y] = [ca[j] + (cb[j] - ca[j]) * k for j in range(3)]; break
    arr = np.zeros((h, w, 4), np.uint8); arr[..., :3] = col[:, None, :]; arr[..., 3] = np.array(m)
    return Image.fromarray(arr, 'RGBA')


def layered(m, fill, layers, shadow=None):
    """layers = [(두께, 색), …] 바깥부터. fill = 색 | 'grad'"""
    pad = sum(t for t, _ in layers) + 8 * S + (max(shadow) if shadow else 0)
    core = Image.new('L', (m.width + 2 * pad, m.height + 2 * pad), 0); core.paste(m, (pad, pad))
    out = Image.new('RGBA', core.size, (0, 0, 0, 0))
    tot = sum(t for t, _ in layers)
    if shadow:
        sh = solid(grow(core, tot), BLACK)
        out.alpha_composite(sh, dest=shadow)
    acc = tot
    for t, c in layers:
        out.alpha_composite(solid(grow(core, acc), c)); acc -= t
    out.alpha_composite(grad(core) if fill == 'grad' else solid(core, fill))
    return out.crop(out.getbbox()), pad


def place(canvas, piece, cx, cy):
    canvas.alpha_composite(piece, dest=(int(cx - piece.width / 2), int(cy - piece.height / 2)))


def logo(W=512, H=256):
    """demo00 좌표계(512x256) 로고 — 4배로 그려 축소. 원본 잉크 x 26‥369(가운데 197), y 46‥182"""
    c = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    # 3행: 여검사 / 아스카 / 등장! — 폭을 재서 한 줄로 늘어놓음(살짝 겹침)
    p1, _ = layered(mask('여검사', F_BRUSH, 34 * S, track=1 * S), NAVY, [(3 * S, BLACK), (3 * S, WHITE)], shadow=(2 * S, 3 * S))
    p2, _ = layered(mask('아스카', F_HEAVY, 60 * S, skew=0.22, track=0), 'grad', [(2 * S, BLACK), (3 * S, WHITE), (2 * S, BLACK)], shadow=(3 * S, 4 * S))
    p3, _ = layered(mask('등장!', F_BRUSH, 32 * S, track=0), NAVY, [(3 * S, BLACK), (3 * S, WHITE)], shadow=(2 * S, 3 * S))
    ov = 6 * S
    tw = p1.width + p2.width + p3.width - 2 * ov
    x = 197 * S - tw // 2
    c.alpha_composite(p1, dest=(x, 158 * S - p1.height // 2)); x1 = x + p1.width - ov
    c.alpha_composite(p3, dest=(x1 + p2.width - ov, 160 * S - p3.height // 2))
    c.alpha_composite(p2, dest=(x1, 140 * S - p2.height // 2))
    # 2행: 풍래의 시렌 외전
    q, _ = layered(mask('풍래의 시렌 외전', F_BRUSH, 24 * S, track=1 * S), RED, [(2 * S, (40, 0, 8)), (2 * S, WHITE)], shadow=(1 * S, 2 * S))
    place(c, q, 186 * S, 84 * S)
    # 1행: 이상한 던전
    r, _ = layered(mask('이상한 던전', F_GOTH, 12 * S, skew=0, track=1 * S), BLACK, [(2 * S, WHITE)])
    place(c, r, 186 * S, 57 * S)
    return c.resize((W, H), Image.LANCZOS)


def quant4444(im):
    a = np.array(im).astype(np.int32)
    a = (a // 17) * 17
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def main():
    os.makedirs(os.path.join(ROOT, 'work', 'logo'), exist_ok=True)
    L = quant4444(logo())
    L.save(os.path.join(ROOT, 'work', 'logo', 'demo00_kr.png'))
    org = Image.open(os.path.join(ROOT, 'work', 'databg', 'DATABG_EXT', 'demo00', 'PVR', 'demo00.png')).convert('RGBA')
    cmp_ = Image.new('RGBA', (512, 512 + 8), (255, 255, 255, 255))
    for k, im in enumerate((org, L)):
        bg = Image.new('RGBA', (512, 256), (255, 255, 255, 255)); bg.alpha_composite(im); cmp_.paste(bg, (0, k * 264))
    out = os.path.join(ROOT, 'work', 'logo', '비교_로고.png')     # my files 에 그래픽 폴더가 없어 work 에(폴더 만들기 금지)
    cmp_.convert('RGB').resize((1024, 1040), Image.LANCZOS).save(out)
    print('→', out)


if __name__ == '__main__':
    main()
