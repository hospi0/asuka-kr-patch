# -*- coding: utf-8 -*-
"""지명판(mapname00~17)·던전 이름표(MN00~MN9E)를 한글로 다시 그린다 — DATABG.

구조 (실측):
  · 논리 이미지 512x256 을 256x256 텍스처 «둘»(A=왼쪽, B=오른쪽)로 쪼개 담는다.
  · 팔레트는 16단 회색 램프(index*17) — 즉 그림이 아니라 «농도 마스크»다.
    잉크는 색인 15, 배경 0. 색은 게임이 런타임에 입힌다.
  · 원문은 후리가나가 위에 붙어 있다. 한글엔 필요 없으므로 «본문 한 줄»로 만든다.
  · 잉크 최대 x=480 (MN61) — 게임이 그리는 가로 범위가 최소 거기까지다.
    그래도 여유를 두고 460px 안에 넣는다.

⛔팔레트를 새로 만들면 안 된다(도구 README). 원본 P 이미지의 팔레트를 그대로 쓴다.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, 'work', 'databg', 'DATABG_EXT')
# ★연성체 — 사용자 선택(2026-08-29). 원본은 손글씨 느낌의 둥근 붓고딕이라
#   고딕체는 안 어울린다. 후보 26종을 실제 이름표 크기로 뽑아 고른 것.
#   ⚠연성은 원본보다 획이 얇다 → 1px 팽창으로 두께를 맞춘다(실측 대조).
FONT = r"C:\claude\utils\font\yeonsung\YeonSung-Regular.ttf"

INK = 15
MAXW = 456
LINE_GAP = 8
BOLD = 1        # 렌더 후 팽창 횟수

# 용어는 기존 번역표를 따른다(리바·크론·부후·사카이·기토·무라도·도라스·카카루,
# 코가·호라이산·야카구라 숲·메이오우란). 天輪 은 상태바에 맞춰 «천륜».
MN = {
 'MN00': ['이자요이 마을'],      'MN01': ['이자요이 논'],
 'MN02': ['코다마 고개'],        'MN03': ['마타기 마을'],
 'MN04': ['텐구의 바람굴'],      'MN05': ['야미쿠모 갱도'],
 'MN06': ['네고로 신사'],        'MN07': ['천륜의 수해'],
 'MN08': ['시라카미 늪'],        'MN09': ['지왕의 바위터'],
 'MN10': ['코가 마을'],          'MN11': ['닌자 저택'],
 'MN12': ['비취 동굴'],          'MN13': ['오니메 고분'],
 'MN14': ['염룡의 이빨'],        'MN15': ['요괴 마을'],
 'MN16': ['수룡의 등뼈'],        'MN17': ['메이오우란'],
 'MN18': ['이자요이 논', '남부'], 'MN19': ['천륜의 수해', '동부'],
 'MN20': ['숲신의 지하도'],      'MN21': ['시라카미 늪·동부'],
 'MN22': ['후이고 구리광산'],    'MN23': ['호라이의 바위굴'],
 'MN24': ['호라이산'],           'MN25': ['메이오우란 정상'],
 'MN26': ['코가성'],             'MN27': ['코가성 천수각'],
 'MN28': ['돌 요새터'],          'MN29': ['이치도 마을'],
 'MN30': ['니코타마 마을'],      'MN31': ['삼파성'],
 'MN32': ['시메이 해변'],        'MN33': ['오곡 골짜기'],
 'MN34': ['무묘 마을'],          'MN35': ['시치텐쿄'],
 'MN36': ['야카구라 숲'],        'MN37': ['겐노우 마을'],
 'MN38': ['황천길 가도'],        'MN39': ['제기의 방'],
 'MN40': ['미야코 옛 수로'],     'MN41': ['마츠리 참배길'],
 'MN42': ['여우의 오솔길'],      'MN43': ['얼음 좁은 길'],
 'MN44': ['선착장'],             'MN45': ['히메모리 큰못'],
 'MN46': ['바람의 전원'],        'MN47': ['잊지 못할 무덤터'],
 'MN48': ['구미의 폭포'],        'MN49': ['미소기 계곡'],
 'MN50': ['파묻힌 성'],          'MN51': ['코마이누 숲'],
 'MN52': ['유골단지 벌판'],      'MN53': ['풍경의 숲'],
 'MN54': ['츠마비키 산기슭'],    'MN55': ['코부시 암굴'],
 'MN56': ['반석의 동굴'],        'MN57': ['카스미의 굴'],
 'MN58': ['옛 왕의 분묘'],       'MN59': ['독수 영원'],
 'MN60': ['공작 공동'],          'MN61': ['은자의 샛길'],
 'MN62': ['복수 수원'],          'MN63': ['작은 고개'],
 'MN64': ['무지나 언덕'],        'MN65': ['아지랑이 마을터'],
 'MN66': ['스미야 광산'],        'MN67': ['이름 없는 유적'],
 'MN68': ['거인의 심장'],        'MN69': ['화석의 숲'],
 'MN70': ['무스비 쌀창고'],      'MN71': ['서쪽 폐광'],
 'MN72': ['불씨의 해자'],        'MN73': ['오보로 저수지'],
 'MN74': ['짐승의 소굴'],        'MN75': ['물밑 미궁'],
 'MN76': ['오소로시 못'],        'MN77': ['천년 빙벽'],
 'MN78': ['츠쿠요미 강'],        'MN79': ['리바의 사당'],
 'MN80': ['크론의 사당'],        'MN81': ['카카루의 사당'],
 'MN82': ['부후의 사당'],        'MN83': ['사카이의 사당'],
 'MN84': ['기토의 사당'],        'MN85': ['무라도의 사당'],
 'MN86': ['도라스의 사당'],      'MN87': ['재계의 방'],
 'MN88': ['시라카미 늪 모래톱'], 'MN89': ['이끼신의 무덤'],
 'MN90': ['성화의 대통'],        'MN91': ['성화의 방'],
 'MN92': ['백사도'],             'MN93': ['사두산'],
 'MN94': ['천수각'],             'MN95': ['코가의 숨은 굴'],
 'MN96': ['리바의 시련'],        'MN97': ['크론의 시련'],
 'MN98': ['카카루의', '시련'],   'MN99': ['부후의 시련'],
 'MN9A': ['사카이의 시련'],      'MN9B': ['기토의 시련'],
 'MN9C': ['무라도의 시련'],      'MN9D': ['도라스의 시련'],
 'MN9E': ['구조로 가는 길'],
}

MAPNAME = {
 'mapname00': ['이자요이 마을'],  'mapname01': ['이자요이 논'],
 'mapname02': ['코다마 고개'],    'mapname03': ['마타기 마을'],
 'mapname04': ['텐구의 바람굴'],  'mapname05': ['야미쿠모 수도'],
 'mapname06': ['네고로 신사'],    'mapname07': ['천륜의 수해'],
 'mapname08': ['시라카미 늪'],    'mapname09': ['지왕의 바위터'],
 'mapname10': ['코가 마을'],      'mapname11': ['닌자 저택'],
 'mapname12': ['비취 동굴'],      'mapname13': ['오니메 고분'],
 'mapname14': ['염룡의 이빨'],    'mapname15': ['요괴 마을'],
 'mapname16': ['수룡의 등뼈'],    'mapname17': ['메이오우란'],
}


def ink_box(arr):
    ys = np.where(arr.any(1))[0]
    xs = np.where(arr.any(0))[0]
    return xs.min(), ys.min(), xs.max(), ys.max()


def render(lines, box_h):
    """줄 목록을 «투명 배경 흰 글자» 마스크로 그린다. (mask, w, h) 반환."""
    n = len(lines)
    avail = (box_h - LINE_GAP * (n - 1)) // n
    size = avail
    while size > 8:
        f = ImageFont.truetype(FONT, size)
        d = ImageDraw.Draw(Image.new('L', (1, 1)))
        bbs = [d.textbbox((0, 0), t, font=f) for t in lines]
        if (max(b[2] - b[0] for b in bbs) <= MAXW
                and max(b[3] - b[1] for b in bbs) <= avail):
            break
        size -= 1
    f = ImageFont.truetype(FONT, size)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    bbs = [d0.textbbox((0, 0), t, font=f) for t in lines]
    w = max(b[2] - b[0] for b in bbs)
    lh = max(b[3] - b[1] for b in bbs)
    h = lh * n + LINE_GAP * (n - 1)
    im = Image.new('L', (w + 4, h + 4), 0)
    d = ImageDraw.Draw(im)
    for i, (t, b) in enumerate(zip(lines, bbs)):
        # 각 줄은 «가운데» 정렬
        x = 2 + (w - (b[2] - b[0])) // 2 - b[0]
        d.text((x, 2 + i * (lh + LINE_GAP) - b[1]), t, font=f, fill=255)
    return im


def build(name, lines):
    d = os.path.join(EXT, name)
    src = Image.open(os.path.join(d, name + '.png'))
    pal = src.getpalette()
    arr = np.array(src)
    x0, y0, x1, y1 = ink_box(arr)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    m = render(lines, y1 - y0 + 1)
    ma = np.array(m) > 110
    for _ in range(BOLD):                 # ★획 굵히기 — 원본 두께에 맞춘다
        b = ma.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                b |= np.roll(np.roll(ma, dy, 0), dx, 1)
        ma = b
    out = np.zeros_like(arr)
    ph, pw = ma.shape
    px = max(0, min(512 - pw, cx - pw // 2))
    py = max(0, min(256 - ph, cy - ph // 2))
    out[py:py + ph, px:px + pw] = np.where(ma, INK, 0)
    im = Image.fromarray(out, 'P')
    im.putpalette(pal)
    im.save(os.path.join(d, name + '.png'))
    for half, sx in (('A', 0), ('B', 256)):
        h = Image.fromarray(out[:, sx:sx + 256].copy(), 'P')
        h.putpalette(pal)
        h.save(os.path.join(d, 'PVR', '%s%s.png' % (name, half)))
    return px, py, pw, ph


if __name__ == '__main__':
    todo = dict(MAPNAME)
    todo.update(MN)
    for name in sorted(todo):
        px, py, pw, ph = build(name, todo[name])
        print('%-10s %-24s x%3d y%3d %3dx%-3d' % (name, ' / '.join(todo[name]),
                                                  px, py, pw, ph))
