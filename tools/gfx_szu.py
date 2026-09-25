# -*- coding: utf-8 -*-
"""DATASZU.BIN 의 «구운 글자» 아틀라스를 한글로 다시 그린다.

대상 (자체 청크 포맷: `u32 size|u32 fmt|u16 w|u16 h|u32 0|char[16] tag`)
  0x00000  system        256x256 4bpp  — 상태바(階 Lv HP G, 숫자, HUD 한자)
  0x21100  n_fonticon00  128x128 8bpp  — 이름입력 라벨 앞부분
  0x25120  n_fonticon01  128x128 8bpp  — 이름입력 라벨 뒷부분 (size 필드 0 = 체인 종단)

★팔레트는 이 파일에 없다(런타임 공급). 그러니 **원본이 쓰는 색인 값을 그대로** 써야
  색이 맞는다. 실측 결과 system 은 0=배경 / 1=테두리 / 6=속살 이다.
★트위들은 DATAAPP 폰트와 같은 «y 하위, x 상위» 교차 (tools/font.py 로 검증).
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')
FONT = r"C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf"

CHUNK = {
    'system':       (0x00000, 4, 256, 256),
    'n_fonticon00': (0x21100, 8, 128, 128),
    'n_fonticon01': (0x25120, 8, 128, 128),
}


def tw_lut(w, h):
    def t(x, y):
        v = 0
        for b in range(16):
            v |= ((y >> b) & 1) << (2 * b)
            v |= ((x >> b) & 1) << (2 * b + 1)
        return v
    return [[t(x, y) for x in range(w)] for y in range(h)]


class Atlas:
    def __init__(self, buf, name):
        self.buf = buf
        self.off, self.bpp, self.w, self.h = CHUNK[name]
        self.data_off = self.off + 32
        self.lut = tw_lut(self.w, self.h)
        n = self.w * self.h
        self.px = [[0] * self.w for _ in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                i = self.lut[y][x]
                if self.bpp == 4:
                    b = buf[self.data_off + (i >> 1)]
                    self.px[y][x] = (b >> 4) if (i & 1) else (b & 15)
                else:
                    self.px[y][x] = buf[self.data_off + i]

    def write_back(self):
        for y in range(self.h):
            for x in range(self.w):
                i = self.lut[y][x]
                v = self.px[y][x]
                if self.bpp == 4:
                    p = self.data_off + (i >> 1)
                    b = self.buf[p]
                    self.buf[p] = ((b & 0x0F) | (v << 4)) if (i & 1) else ((b & 0xF0) | v)
                else:
                    self.buf[self.data_off + i] = v

    def clear(self, x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px[y][x] = 0

    def draw_text(self, text, x0, y0, x1, y1, fill, outline, pad=2, ow=1):
        """상자 안에 «테두리 있는» 글자를 그린다. 상자에 꽉 차게 자동 축소.

        ★ow = 테두리 두께. 상태바 원본(階·Lv·HP)은 실측 결과 «2px» 다.
          1px 로 그리면 옆 글자보다 얇고 작아 보인다(실기 2026-08-29).
          pad 2 + ow 2 면 속살 23 + 테두리 4 = 27px 로 원본 階 와 정확히 같다.
        """
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        iw, ih = bw - pad * 2, bh - pad * 2
        size = ih
        while size > 6:
            f = ImageFont.truetype(FONT, size)
            im = Image.new('L', (bw * 4, bh * 4), 0)
            d = ImageDraw.Draw(im)
            bb = d.textbbox((0, 0), text, font=f)
            if bb[2] - bb[0] <= iw and bb[3] - bb[1] <= ih:
                break
            size -= 1
        # ★크게 그린 뒤 «잉크만 잘라» 상자 안쪽에 꽉 차게 줄인다.
        #   폰트 크기만 줄이면 자간·여백 탓에 잉크가 상자보다 2~3px 작게 남는다.
        big = ImageFont.truetype(FONT, 96)
        bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=big)
        tmp = Image.new('L', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), 0)
        ImageDraw.Draw(tmp).text((4 - bb[0], 4 - bb[1]), text, font=big, fill=255)
        tmp = tmp.crop(tmp.getbbox())
        sc = min(iw / tmp.width, ih / tmp.height)
        tmp = tmp.resize((max(1, round(tmp.width * sc)),
                          max(1, round(tmp.height * sc))), Image.LANCZOS)
        im = Image.new('L', (bw, bh), 0)
        im.paste(tmp, ((bw - tmp.width) // 2, (bh - tmp.height) // 2))
        m = im.load()
        core = [[m[x, y] > 110 for x in range(bw)] for y in range(bh)]
        # 테두리 = 속살을 ow px 팽창한 자리
        grow = [r[:] for r in core]
        for _ in range(ow):
            nxt = [r[:] for r in grow]
            for y in range(bh):
                for x in range(bw):
                    if not grow[y][x]:
                        continue
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = y + dy, x + dx
                            if 0 <= yy < bh and 0 <= xx < bw:
                                nxt[yy][xx] = True
            grow = nxt
        out = [[grow[y][x] and not core[y][x] for x in range(bw)]
               for y in range(bh)]
        self.clear(x0, y0, x1, y1)
        for y in range(bh):
            for x in range(bw):
                v = fill if core[y][x] else (outline if out[y][x] else None)
                if v is not None:
                    self.px[y0 + y][x0 + x] = v

    def preview(self, path, scale=3):
        pal = [(0, 0, 0), (200, 40, 40), (0, 200, 0), (0, 0, 220), (255, 255, 0),
               (255, 0, 255), (245, 245, 245), (160, 160, 160), (110, 110, 110),
               (255, 150, 0), (150, 0, 255), (0, 140, 80), (80, 80, 255),
               (210, 210, 120), (120, 210, 210), (255, 255, 255)]
        im = Image.new('RGB', (self.w, self.h))
        p = im.load()
        for y in range(self.h):
            for x in range(self.w):
                v = self.px[y][x]
                p[x, y] = pal[v % 16] if self.bpp == 4 else ((v, v, v) if v else (0, 0, 40))
        im.resize((self.w * scale, self.h * scale), Image.NEAREST).save(path)


def draw_span(atlas, text, segs, fill, outline, pad=1, stretch=False):
    """★아틀라스는 «가로 128px 에서 줄바꿈되는 선형 글자 띠»다.
    라벨 하나가 줄을 넘어가므로(「かな・カナ・英」+ 다음 줄 「数」) 여러 조각으로 준다.
    글자를 조각 폭 합계에 맞춰 한 번에 그린 뒤 조각별로 나눠 붙인다."""
    from PIL import Image, ImageDraw, ImageFont
    W = sum(x1 - x0 + 1 for x0, y0, x1, y1 in segs)
    # ⛔조각마다 «줄 높이»가 다르다(26·26·19px). 가장 높은 줄 기준으로 그리면
    #   낮은 줄에서 아래가 잘려 「전환」이 「너화」로 깨진다(실기 2026-08-29).
    #   그래서 «가장 낮은 줄» 기준으로 그리고 각 조각에 세로 가운데 정렬한다.
    H = min(y1 - y0 + 1 for x0, y0, x1, y1 in segs)
    ih = H - pad * 2
    size = ih
    while size > 6:
        f = ImageFont.truetype(FONT, size)
        d = ImageDraw.Draw(Image.new('L', (1, 1)))
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= W - pad * 2 and bb[3] - bb[1] <= ih:
            break
        size -= 1
    if stretch:
        # ★가로가 빠듯해 글자가 작아진 라벨은 «세로만» 늘려 칸을 채운다.
        #   폭 기준으로 크게 그린 뒤 (W, H) 로 비균등 축소한다.
        big = ImageFont.truetype(FONT, 96)
        d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
        bb = d0.textbbox((0, 0), text, font=big)
        tmp = Image.new('L', (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), 0)
        ImageDraw.Draw(tmp).text((-bb[0] + 2, -bb[1] + 2), text, font=big, fill=255)
        tmp = tmp.crop(tmp.getbbox()).resize((W - pad * 2, H - pad * 2), Image.LANCZOS)
        im = Image.new('L', (W, H), 0)
        im.paste(tmp, (pad, pad))
    else:
        f = ImageFont.truetype(FONT, size)
        im = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(im)
        bb = d.textbbox((0, 0), text, font=f)
        d.text((-bb[0] + (W - (bb[2] - bb[0])) // 2,
                -bb[1] + (H - (bb[3] - bb[1])) // 2), text, font=f, fill=255)
    m = im.load()
    core = [[m[x, y] > 110 for x in range(W)] for y in range(H)]
    out = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if core[y][x]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and core[yy][xx]:
                        out[y][x] = True
                        break
    cx = 0
    for x0, y0, x1, y1 in segs:
        w = x1 - x0 + 1
        atlas.clear(x0, y0, x1, y1)
        oy = (y1 - y0 + 1 - H) // 2            # 조각 안에서 세로 가운데
        for y in range(H):
            for x in range(w):
                v = fill if core[y][cx + x] else (outline if out[y][cx + x] else None)
                if v is not None:
                    atlas.px[y0 + oy + y][x0 + x] = v
        cx += w
    return size


def draw_span_cells(atlas, text, segs, fill, outline, pad=1):
    """★★글자가 «조각 경계»를 넘으면 실기에서 잘린다.

    「영숫자」의 자, 「트리거」의 리, 「전환」의 환이 전부 128px 줄바꿈 자리에 걸려
    잘렸다(실기 2026-08-29). 게임이 줄마다 따로 그리기 때문이다.
    ⇒ 글자를 «통째로» 한 조각 안에 배치한다. 조각에 안 들어가면 다음 조각으로 넘긴다.
    """
    from PIL import Image, ImageDraw, ImageFont
    n = len(text)
    hmin = min(y1 - y0 + 1 for _, y0, _, y1 in segs) - pad * 2
    size = hmin
    while size > 6:
        cap = sum((x1 - x0 + 1) // size for x0, _, x1, _ in segs)
        if cap >= n:
            break
        size -= 1
    # 글자를 조각에 순서대로 채운다
    parts, i = [], 0
    for x0, y0, x1, y1 in segs:
        cnt = min((x1 - x0 + 1) // size, n - i)
        parts.append((text[i:i + cnt], x0, y0, x1, y1))
        i += cnt
    f = ImageFont.truetype(FONT, size)
    for txt, x0, y0, x1, y1 in parts:
        atlas.clear(x0, y0, x1, y1)
        if not txt:
            continue
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        im = Image.new('L', (bw, bh), 0)
        d = ImageDraw.Draw(im)
        # ★★글자마다 «고정 칸»에 그린다. 가변폭으로 이어 그리면 조각 끝에 여백이
        #   남고, 조각을 이어 붙이는 화면에서 그게 «빈틈»으로 보인다
        #   (「영숫 자」·「트리거로  페이지」 — 실기 2026-08-29).
        # ⛔게임이 «줄 끝 몇 픽셀»을 안 그린다 — 조각의 마지막 글자가 잘렸다
        #   (「숫」·「로」·「환」, 실기 2026-08-29). 글자를 칸보다 작게 그려
        #   잉크가 가장자리에 닿지 않게 한다.
        cw = bw / len(txt)
        fi = ImageFont.truetype(FONT, max(8, size - 3))
        for k, ch in enumerate(txt):
            bb = d.textbbox((0, 0), ch, font=fi)
            cx = k * cw + (cw - (bb[2] - bb[0])) / 2
            d.text((cx - bb[0], -bb[1] + (bh - (bb[3] - bb[1])) // 2), ch, font=fi, fill=255)
        m = im.load()
        core = [[m[x, y] > 110 for x in range(bw)] for y in range(bh)]
        out = [[False] * bw for _ in range(bh)]
        for y in range(bh):
            for x in range(bw):
                if core[y][x]:
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < bh and 0 <= xx < bw and core[yy][xx]:
                            out[y][x] = True
                            break
        for y in range(bh):
            for x in range(bw):
                v = fill if core[y][x] else (outline if out[y][x] else None)
                if v is not None:
                    atlas.px[y0 + y][x0 + x] = v
    return size
