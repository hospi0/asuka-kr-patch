# -*- coding: utf-8 -*-
"""조작 설명 화면(CA_16 / CB_16, DATABG)을 한글로 다시 그린다.

실측 (CA_16 640x512 RGB):
  · 어두운 갈색 패널 11개, 바탕 RGB(123,85,49). 흰 테두리는 건드리지 않는다.
  · 패널마다 «라벨 1줄»(노랑 또는 초록) + «본문 1~2줄»(크림색).
  · 지우기는 패널 «안쪽»만 — 테두리를 먹으면 상자가 깨진다.

CA_16 과 CB_16 은 A/B 버튼 배치만 다르다(같은 좌표, 본문만 교체).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, 'work', 'databg', 'DATABG_EXT')
FONT = r"C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf"

INSET = 4          # 테두리를 피해 안쪽만 지운다

# ★실측(원본 라벨 줄 색 채취):
#   노랑 (250,196,8) — 트리거·방향키·방향버튼·스타트버튼·Ｙ버튼
#   초록 (139,226,74) — Ａ·Ｂ·Ｘ 버튼만
#   본문 크림 (243,236,236)
#   바탕 (82,60,32) — 방향버튼 칸에서 뽑아 «전 칸에 일괄» 적용 (사용자 지시)
YELLOW = (250, 196, 8)
GREEN = (139, 226, 74)
BODY = (243, 236, 236)
BASE = (82, 60, 32)
GREEN_PANELS = {'CA_16': {4, 6, 8}, 'CB_16': {4, 6, 7}}   # Ａ·Ｂ·Ｘ 버튼 칸
MIX_PANEL = 10                 # 「Ｂ버튼＋Ｒ트리거」 — 버튼만 초록, 뒤는 노랑

MAXSIZE = 22       # ⛔글자 상한 — 없으면 큰 칸에서 글자가 터진다(CB 실패 2026-08-29)

# ★★패널 좌표는 «파일마다» 다르다. CA 것을 CB 에 쓰면 상자가 어긋나고 글자가 터진다.
#   A/B 배치가 바뀌면서 칸의 크기·위치·줄 수가 전부 달라진다. 각각 실측했다.
PANELS = {
 'CA_16': [(287,  40, 419,  99), (457,  40, 590,  98), (456, 123, 565, 184),
           ( 48, 166, 190, 225), (454, 200, 606, 288), ( 49, 236, 189, 294),
           (270, 280, 421, 367), ( 49, 303, 235, 365), (454, 305, 590, 365),
           ( 36, 379, 342, 439), (350, 379, 607, 439)],
 'CB_16': [(287,  40, 419,  99), (457,  40, 590,  98), (456, 123, 565, 184),
           ( 48, 166, 190, 225), (454, 198, 594, 262), ( 49, 236, 189, 294),
           (455, 274, 610, 366), (303, 302, 417, 363), ( 49, 303, 235, 365),
           ( 36, 379, 342, 439), (350, 379, 607, 439)],
}

# (라벨, 본문줄들) — 패널 좌표와 «같은 순서». i대시의 i 는 원문 그대로 둔다(사용자 지시).
JOBS = {
 'CA_16': [
    ('L트리거', ['화살 쏘기']),
    ('R트리거', ['대각선 이동']),
    ('Y버튼', ['메뉴']),
    ('아날로그 방향키', ['i대시']),
    ('B버튼', ['취소·', '돌아보기']),
    ('방향버튼', ['이동']),
    ('X버튼', ['취소·', '대시']),
    ('스타트버튼', ['맵만 표시']),
    ('A버튼', ['결정·공격']),
    ('X버튼＋스타트버튼', ['메시지 기록']),
    ('B버튼＋R트리거', ['맵 그리드 표시']),
 ],
 'CB_16': [
    ('L트리거', ['화살 쏘기']),
    ('R트리거', ['대각선 이동']),
    ('Y버튼', ['메뉴']),
    ('아날로그 방향키', ['i대시']),
    ('B버튼', ['결정·공격']),
    ('방향버튼', ['이동']),
    ('A버튼', ['취소·', '대시']),
    ('X버튼', ['돌아보기']),
    ('스타트버튼', ['맵만 표시']),
    ('X버튼＋스타트버튼', ['메시지 기록']),
    ('A버튼＋R트리거', ['맵 그리드 표시']),
 ],
}


def measure(a, box):
    """패널 안 «바탕색»과 라벨/본문 색을 잰다."""
    x0, y0, x1, y1 = box
    sub = a[y0 + INSET:y1 - INSET + 1, x0 + INSET:x1 - INSET + 1]
    lum = sub.mean(2)
    base = np.median(sub[lum < np.percentile(lum, 60)], 0).astype(int)
    ink = sub[lum > np.percentile(lum, 92)]
    r, g, b = ink[:, 0], ink[:, 1], ink[:, 2]
    yellow = ink[(r > 170) & (g > 130) & (b < 120)]
    green = ink[(g > 150) & (r < 160) & (b < 160)]
    label = (np.median(yellow, 0) if len(yellow) > len(green) else
             (np.median(green, 0) if len(green) else np.median(ink, 0)))
    body = np.median(ink[(r > 200) & (g > 195) & (b > 180)], 0) if (
        ((r > 200) & (g > 195) & (b > 180)).sum() > 20) else np.array([235, 230, 220])
    return (tuple(base), tuple(np.nan_to_num(label).astype(int)),
            tuple(np.nan_to_num(body).astype(int)))


def _fit(text, maxw, maxh):
    for s in range(min(maxh, MAXSIZE), 7, -1):
        f = ImageFont.truetype(FONT, s)
        bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= maxw and bb[3] - bb[1] <= maxh:
            return f, bb
    return f, bb


def draw_panel(img, box, label, body, lcol, mix=False):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    d.rectangle([x0 + INSET, y0 + INSET, x1 - INSET, y1 - INSET], fill=BASE)
    n = 1 + len(body)
    ih = (y1 - y0 + 1 - INSET * 2)
    lh = ih // n
    iw = (x1 - x0 + 1 - INSET * 2) - 6
    ty = y0 + INSET
    for i, (txt, col) in enumerate([(label, lcol)] + [(t, BODY) for t in body]):
        f, bb = _fit(txt, iw, lh - 3)
        cx = x0 + INSET + 3 + (0 if i == 0 else 4)
        yy = ty + (lh - (bb[3] - bb[1])) // 2 - bb[1]
        if i == 0 and mix and '＋' in txt:
            # ★버튼 이름만 초록, ＋뒤는 노랑 (원본과 같은 배색)
            head, tail = txt.split('＋', 1)
            d.text((cx - bb[0], yy), head, font=f, fill=GREEN)
            w = d.textlength(head, font=f)
            d.text((cx - bb[0] + w, yy), '＋' + tail, font=f, fill=YELLOW)
        else:
            d.text((cx - bb[0], yy), txt, font=f, fill=col)
        ty += lh


def build(name):
    p = os.path.join(EXT, name, name + '.png')
    im = Image.open(p).convert('RGB')
    for i, (box, job) in enumerate(zip(PANELS[name], JOBS[name])):
        lcol = GREEN if i in GREEN_PANELS[name] else YELLOW
        draw_panel(im, box, job[0], job[1], lcol, mix=(i == MIX_PANEL))
    return im


def write_ext(name, im):
    """DATABG_EXT 에 되쓴다.

    ★실측: 640x512 논리 이미지를 텍스처 «둘»에 나눠 담는다.
       A(512x512) = 왼쪽 512열
       B(256x256) = 오른쪽 128열을 위/아래로 잘라 «좌·우 반쪽»에 나란히
         B[:, :128] = 상단 우측 (y0-255)   B[:, 128:] = 하단 우측 (y256-511)
    """
    # ⛔모드를 원본과 같게 유지할 것 — 원본은 RGBA 다. RGB 로 저장하면 도구가
    #   그 항목을 «건너뛴다»(2026-08-29: 화면이 일본어 그대로였다).
    d = os.path.join(EXT, name)
    src = Image.open(os.path.join(d, name + '.png'))
    mode = src.mode
    alpha = np.array(src)[..., 3] if mode == 'RGBA' else None
    a = np.array(im.convert('RGB'))
    if alpha is not None:
        a = np.dstack([a, alpha])

    def put(arr, path):
        Image.fromarray(arr, mode).save(path)

    put(a, os.path.join(d, name + '.png'))
    put(a[:, :512].copy(), os.path.join(d, 'PVR', name + 'A.png'))
    ch = a.shape[2]
    b = np.zeros((256, 256, ch), np.uint8)
    b[:, :128] = a[0:256, 512:640]
    b[:, 128:] = a[256:512, 512:640]
    put(b, os.path.join(d, 'PVR', name + 'B.png'))


if __name__ == '__main__':
    import sys
    out = os.path.join(ROOT, 'work', 'atlas')
    for n in ('CA_16', 'CB_16'):
        im = build(n)
        im.save(os.path.join(out, 'kr_%s.png' % n))
        if '--write' in sys.argv:
            write_ext(n, im)
            print(n, 'DATABG_EXT 기록')
        else:
            print(n, 'ok (미리보기 — 기록은 --write)')
