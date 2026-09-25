# -*- coding: utf-8 -*-
"""DATAAPP.BIN 전각 폰트 판독/기록.

구조 (docs/00_survey.md §3):
  512x512 4bpp 트위들 텍스처 4장. 니블 하위 2비트 = 짝수 페이지, 상위 2비트 = 홀수 페이지.
  페이지당 19열 x 19행, 피치 26px, 총 7페이지 x 361 = 2527칸, 문자표는 2472자.
"""
import struct

TEX = [0x09000, 0x29020, 0x49040, 0x69060]   # 청크 헤더 오프셋 (데이터는 +0x20)
DATA_OFF = 0x20
W = H = 512
PITCH = 26
COLS = ROWS = 19
PER_PAGE = COLS * ROWS          # 361
NPAGES = 7
CHARTAB = 0x8b000
WIDTHTAB = 0x89800
NCHARS = 2472

_TW = None
def _twiddle(x, y):
    n = 0
    for b in range(16):
        n |= ((y >> b) & 1) << (2 * b)
        n |= ((x >> b) & 1) << (2 * b + 1)
    return n

def _lut():
    global _TW
    if _TW is None:
        _TW = [[_twiddle(x, y) for x in range(W)] for y in range(H)]
    return _TW

class Font:
    def __init__(self, path):
        self.path = path
        self.buf = bytearray(open(path, 'rb').read())
        self.chars = self.buf[CHARTAB:CHARTAB + NCHARS * 2].decode('cp932')
        self.index = {c: i for i, c in enumerate(self.chars)}
        # 헤더 검산
        for off in TEX:
            size, fmt, w, h = struct.unpack_from('<IIHH', self.buf, off)
            # 마지막 청크는 size 필드가 0 (체인 종단)
            assert (fmt, w, h) == (0x0501, 512, 512) and size in (0x20020, 0), (hex(off), size, fmt, w, h)

    # --- 셀 좌표 ---
    def locate(self, idx):
        """글리프 인덱스 -> (텍스처번호, 플레인(0=하위2비트,1=상위), x0, y0)"""
        if not 0 <= idx < NPAGES * PER_PAGE:
            raise IndexError(idx)
        page, k = divmod(idx, PER_PAGE)
        tex, plane = divmod(page, 2)
        row, col = divmod(k, COLS)
        return tex, plane, col * PITCH, row * PITCH

    def _pix_off(self, tex, x, y):
        i = _lut()[y][x]
        return TEX[tex] + DATA_OFF + (i >> 1), (i & 1)

    # --- 읽기/쓰기 ---
    def get_cell(self, idx):
        tex, plane, x0, y0 = self.locate(idx)
        out = [[0] * PITCH for _ in range(PITCH)]
        for dy in range(PITCH):
            for dx in range(PITCH):
                bo, hi_nib = self._pix_off(tex, x0 + dx, y0 + dy)
                v = self.buf[bo]
                v = (v >> 4) if hi_nib else (v & 15)
                out[dy][dx] = (v >> 2) if plane else (v & 3)
        return out

    def set_cell(self, idx, cell):
        """cell: 26x26, 값 0..3. 겹쳐 있는 반대 플레인은 보존한다."""
        assert len(cell) == PITCH and all(len(r) == PITCH for r in cell)
        tex, plane, x0, y0 = self.locate(idx)
        for dy in range(PITCH):
            for dx in range(PITCH):
                v2 = cell[dy][dx]
                assert 0 <= v2 <= 3
                bo, hi_nib = self._pix_off(tex, x0 + dx, y0 + dy)
                b = self.buf[bo]
                nib = (b >> 4) if hi_nib else (b & 15)
                nib = ((nib & 0x3) | (v2 << 2)) if plane else ((nib & 0xC) | v2)
                self.buf[bo] = ((b & 0x0F) | (nib << 4)) if hi_nib else ((b & 0xF0) | nib)

    # --- 폭 테이블 ---
    def get_width(self, idx):
        return self.buf[WIDTHTAB + idx * 2], self.buf[WIDTHTAB + idx * 2 + 1]

    def set_width(self, idx, left, right):
        self.buf[WIDTHTAB + idx * 2] = left
        self.buf[WIDTHTAB + idx * 2 + 1] = right

    # --- 문자표 ---
    def set_char(self, idx, ch):
        b = ch.encode('cp932')
        assert len(b) == 2, (ch, b)
        self.buf[CHARTAB + idx * 2:CHARTAB + idx * 2 + 2] = b
        self.chars = self.chars[:idx] + ch + self.chars[idx + 1:]

    def save(self, path):
        open(path, 'wb').write(bytes(self.buf))
