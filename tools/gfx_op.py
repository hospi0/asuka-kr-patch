# -*- coding: utf-8 -*-
"""오프닝 나레이션(OPfont_*, DATAIDA.BIN)을 한글로 다시 굽는다.

★이 문구는 «텍스트가 아니라 구운 그림»이다. 전 트랙 SJIS 0건, 세이브스테이트 RAM
  문자열 4,810개 전수 확인에도 0건이었다. 512x512 4bpp 텍스처 6장에 통짜로 들어있다.

실측(원본):
  · 줄 간격 32px 고정, 글자 높이 28~29px, 가로는 x=256 중앙정렬
  · 최대 줄 폭 473px (512 안)
  · 색인 0=배경 / 1=테두리 / 11=속살 / 7·9·10=안티 (팔레트는 런타임 공급)
⇒ 줄마다 «32px 띠»를 통째로 지우고 같은 자리에 한글을 중앙정렬로 다시 그린다.
  띠 시작이 전부 32의 배수임을 확인했으므로 이웃 줄을 건드리지 않는다.

★한자 병기는 안 한다 — 나눔고딕에 신자체 「国」가 없어 두부로 깨진다(실측).
용어는 기존 번역표를 따른다(리바·콧파·코요리·코가·사이라이국·풍래인).
天輪 은 상태바가 「천륜국초급」이라 «천륜»으로 통일한다.
"""
import os, re, struct, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ★궁서 — 사용자 선택(2026-08-29). 후보 26종을 실제 크기로 뽑아 고른 것.
#   batang.ttc 는 4종 묶음이고 궁서는 «index 3» 이다.
FONT = r"C:\Windows\Fonts\batang.ttc"
FONT_INDEX = 3

BAND = 32          # 줄 간격 (실측)
MAXW = 496         # 좌우 여백을 남긴 최대 줄 폭
MAXH = 30
FILL, OUT = 11, 1  # 속살 / 테두리 색인

TEXT = {
 'OPfont_01': [
   '천륜국.',
   '이곳에는 거대한 고리 모양의 천륜산맥과',
   '그 고리 안에 천륜의 수해가 있다.',
   '깊은 자연에 둘러싸인 땅이다.',
   '지금 이 나라에서는 보름 전부터',
   '한 가지 문제가 불거지고 있었다.',
 ],
 'OPfont_03': [
   '수해 깊숙한 곳에 요새를 둔',
   '「코가」라는 닌자 집단이',
   '어처구니없게도 인근 마을 사람과',
   '나그네를 습격해',
   '그 짐을 빼앗는 사건이',
   '잇따라 일어나고 있다.',
   '하지만 코가는 본래',
   '몬스터 퇴치를 생업으로 삼고',
   '평화를 지키는 자들로 알려져 있었다.',
   '그들은 어째서 변해버린 것일까',
   '하지만',
   '그 의문을 풀 방도를 가진 자는',
   '지금으로선 이 나라에',
   '한 사람도 없었다……',
 ],
 'OPfont_07': [
   '천륜산맥 기슭에 있는',
   '이자요이 마을.',
   '이곳은 풍요로운 전원의 축복을 받은',
   '평온한 땅이다.',
   '그리고 수많은 땅을 여행해 온',
   '이야기 족제비 콧파는',
   '지금 이 마을에 몸을 의탁하고 있었다.',
   '때마침 초목이 짙게 향기를 내는',
   '어느 초여름의 일이다.',
 ],
 'OPfont_10': [
   '이 세계에는',
   '리바 팔수신이라는',
   '사람들에게 널리 사랑받는 신들이 있다.',
   '주신인 운명신 리바',
   '여행의 신 크론　　마도신 도라스',
   '식(食)의 신 부후　　상업신 사카이',
   '주(住)의 신 무라도　　도둑신 기토',
   '덫의 신 카카루',
   '이 여덟 신이다.',
 ],
 'OPfont_12': [
   '사이라이국.',
   '이곳에는 이름 높은',
   '「리바 축제」라는 것이 있다.',
   '그것은 리바 팔수신의 영력을 빌려',
   '이 땅의 사악한 기운을 물리치고',
   '행운을 불러들이는',
   '한 해에 한 번 열리는 성대한 행사이며',
   '특히 길흉을 따지는 풍래인들에게',
   '이 축제를 보는 것은',
   '무엇보다 중요한 일이었다.',
 ],
 'OPfont_15': [
   '지금 이 나라에서는',
   '축제의 최고 책임자인',
   '제사장 코요리 아래',
   '리바 축제 준비가',
   '착착 진행되고 있을',
   '터였다…….',
 ],
}


def tw_lut(w, h):
    return [[sum((((y >> b) & 1) << (2 * b)) | (((x >> b) & 1) << (2 * b + 1))
                 for b in range(16)) for x in range(w)] for y in range(h)]


class Tex4:
    """512x512 4bpp 트위들 텍스처."""

    def __init__(self, buf, off, w, h):
        self.buf, self.base, self.w, self.h = buf, off + 32, w, h
        self.lut = tw_lut(w, h)
        self.px = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                i = self.lut[y][x]
                b = buf[self.base + (i >> 1)]
                self.px[y][x] = (b >> 4) if (i & 1) else (b & 15)

    def write_back(self):
        for y in range(self.h):
            for x in range(self.w):
                i = self.lut[y][x]
                p = self.base + (i >> 1)
                v = self.px[y][x]
                b = self.buf[p]
                self.buf[p] = ((b & 0x0F) | (v << 4)) if (i & 1) else ((b & 0xF0) | v)

    def lines(self):
        """잉크가 있는 «줄 띠»를 찾아 (밴드시작, y0, y1) 로 돌려준다."""
        rows = [any(self.px[y]) for y in range(self.h)]
        res, s = [], None
        for y in range(self.h + 1):
            ink = y < self.h and rows[y]
            if ink and s is None:
                s = y
            elif not ink and s is not None:
                if y - s >= 4:
                    res.append(((s // BAND) * BAND, s, y - 1))
                s = None
        return res

    def clear_band(self, b0):
        for y in range(b0, min(b0 + BAND, self.h)):
            for x in range(self.w):
                self.px[y][x] = 0


def _fit(text):
    for size in range(MAXH, 7, -1):
        f = ImageFont.truetype(FONT, size, index=FONT_INDEX)
        bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= MAXW and bb[3] - bb[1] <= MAXH:
            return f, bb
    return f, bb


def draw_line(tex, band, text):
    """32px 띠를 비우고 그 자리에 «테두리 있는» 한글을 중앙정렬로 그린다."""
    tex.clear_band(band)
    if not text:
        return
    f, bb = _fit(text)
    tw_, th = bb[2] - bb[0], bb[3] - bb[1]
    im = Image.new('L', (tex.w, BAND), 0)
    ImageDraw.Draw(im).text(((tex.w - tw_) // 2 - bb[0], (BAND - th) // 2 - bb[1]),
                            text, font=f, fill=255)
    m = im.load()
    W = tex.w
    # ⛔안티 시도했다가 «되돌림»(사용자 지시 2026-08-29). 2단(속살 11 / 테두리 1)이다.
    core = [[m[x, y] > 110 for x in range(W)] for y in range(BAND)]
    # ★실측(원본 색인 맵): 테두리는 왼쪽·위 1px, «오른쪽·아래 2px» — 즉 1px 윤곽에
    #   오른쪽아래로 1px 어긋난 그림자가 겹쳐 있다. 그 구조를 그대로 만든다.
    dil = [[False] * W for _ in range(BAND)]
    for y in range(BAND):
        for x in range(W):
            if not core[y][x]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < BAND and 0 <= xx < W:
                        dil[yy][xx] = True
    dark = [[dil[y][x] or (y and x and dil[y - 1][x - 1]) for x in range(W)]
            for y in range(BAND)]
    for y in range(BAND):
        for x in range(W):
            if core[y][x]:
                tex.px[band + y][x] = FILL
            elif dark[y][x]:
                tex.px[band + y][x] = OUT


def apply(buf):
    """DATAIDA 버퍼를 제자리에서 고친다. 크기·오프셋 불변."""
    done = []
    for m in re.finditer(rb'OPfont_\d\d\x00', buf):
        tag = m.group().rstrip(b'\x00').decode()
        if tag not in TEXT:
            continue
        o = m.start() - 16
        w, h = struct.unpack_from('<HH', buf, o + 8)
        tex = Tex4(buf, o, w, h)
        bands = [b for b, _, _ in tex.lines()]
        kr = TEXT[tag]
        if len(bands) != len(kr):
            raise SystemExit('%s 줄 수 불일치: 원본 %d, 번역 %d' % (tag, len(bands), len(kr)))
        for b, t in zip(bands, kr):
            draw_line(tex, b, t)
        tex.write_back()
        done.append((tag, tex))
    return done


if __name__ == '__main__':
    p = os.path.join(ROOT, 'work', 'iso', 'DATAIDA.BIN')
    buf = bytearray(open(p, 'rb').read())
    out = os.path.join(ROOT, 'work', 'opfont')
    os.makedirs(out, exist_ok=True)
    for tag, tex in apply(buf):
        im = Image.new('L', (tex.w, tex.h))
        px = im.load()
        for y in range(tex.h):
            for x in range(tex.w):
                px[x, y] = tex.px[y][x] * 17
        im.save(os.path.join(out, 'kr_%s.png' % tag))
        print(tag, 'ok')
