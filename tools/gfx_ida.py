# -*- coding: utf-8 -*-
"""DATAIDA.BIN 의 «오프닝 나레이션 글자판»(OPfont_*) 디코더.

★나레이션 문구는 디스크 어디에도 SJIS 로 없다(전 트랙·세이브스테이트 RAM 4,810개
  문자열 전수 확인). 엔진이 글자를 그리는 게 아니라 **512x512 4bpp 텍스처에 구운
  그림**이다. 태그가 `OPfont_NN` 이라 폰트처럼 보이지만 실제로는 «문장 통짜» 이미지다.

청크 헤더는 DATASZU 와 같다: u32 size | u32 fmt | u16 w | u16 h | u32 0 | char[16] tag
fmt 0x0501 = 4bpp 팔레트. 트위들 = y 하위비트 / x 상위비트.
"""
import io, os, re, struct, sys
from PIL import Image

TAGRE = re.compile(rb'(OPfont_\d\d|EDkg_font_\d\d)\x00')


def tw_lut(w, h):
    lut = {}
    for y in range(h):
        for x in range(w):
            i = 0
            for b in range(16):
                i |= ((y >> b) & 1) << (2 * b)
                i |= ((x >> b) & 1) << (2 * b + 1)
            lut[(x, y)] = i
    return lut


def chunks(buf):
    for m in TAGRE.finditer(buf):
        o = m.start() - 16
        if o < 0:
            continue
        size, fmt = struct.unpack_from('<II', buf, o)
        w, h = struct.unpack_from('<HH', buf, o + 8)
        yield o, size, fmt, w, h, m.group(1).decode()


def decode(buf, off, w, h, bpp):
    """트위들 해제 후 인덱스 맵을 돌려준다."""
    base = off + 32
    lut = tw_lut(w, h)
    px = Image.new('L', (w, h))
    p = px.load()
    for y in range(h):
        for x in range(w):
            i = lut[(x, y)]
            if bpp == 4:
                byte = buf[base + (i >> 1)]
                v = (byte >> 4) if (i & 1) else (byte & 0x0F)
                p[x, y] = v * 17
            else:
                lo, hi = buf[base + i * 2], buf[base + i * 2 + 1]
                v = lo | (hi << 8)
                # ARGB1555/RGB565 어느 쪽이든 «글자가 보이는지»만 판단하면 된다
                p[x, y] = min(255, ((v >> 11) & 31) * 8 + ((v >> 5) & 63) * 2)
    return px


if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    buf = open(os.path.join(ROOT, 'work', 'iso', 'DATAIDA.BIN'), 'rb').read()
    outdir = os.path.join(ROOT, 'work', 'opfont')
    os.makedirs(outdir, exist_ok=True)
    want = sys.argv[1] if len(sys.argv) > 1 else 'OPfont'
    for o, size, fmt, w, h, tag in chunks(buf):
        if not tag.startswith(want):
            continue
        bpp = 4 if (fmt & 0xFF00) == 0x0500 else 16
        im = decode(buf, o, w, h, bpp)
        im.save(os.path.join(outdir, tag + '.png'))
        print('%s 0x%08X %dx%d bpp%d' % (tag, o, w, h, bpp))
