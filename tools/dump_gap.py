# -*- coding: utf-8 -*-
"""원본 DATASCR.BIN 의 «구간» 을 문자열 단위로 덤프한다.

  python tools/dump_gap.py 0xB382A 0xB4888

추출표에 빠진 문자열이 있는지 확인할 때 쓴다.
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'iso', 'DATASCR.BIN')


def strings(d, a, b, minlen=6):
    out, i = [], a
    while i < b:
        c = d[i]
        two = (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF) and i + 1 < b and 0x40 <= d[i + 1] <= 0xFC
        if two or 0x20 <= c < 0x7F:
            s = i
            j = i
            while j < b:
                c2 = d[j]
                if (0x81 <= c2 <= 0x9F or 0xE0 <= c2 <= 0xEF) and j + 1 < b and 0x40 <= d[j + 1] <= 0xFC:
                    j += 2
                elif 0x20 <= c2 < 0x7F or c2 in (0x0A, 0x1F):
                    j += 2 if c2 == 0x1F else 1
                else:
                    break
            raw = d[s:j]
            if len(raw) >= minlen:
                out.append((s, raw))
            i = max(j, i + 1)
        else:
            i += 1
    return out


def show(raw):
    t, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == 0x1F and i + 1 < len(raw):
            t.append('\\x1F\\x%02X' % raw[i + 1]); i += 2
        elif c == 0x0A:
            t.append('\\n'); i += 1
        elif (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF) and i + 1 < len(raw):
            t.append(bytes(raw[i:i + 2]).decode('cp932', 'replace')); i += 2
        else:
            t.append(chr(c) if 0x20 <= c < 0x7F else '.'); i += 1
    return ''.join(t)


if __name__ == '__main__':
    a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
    d = open(SRC, 'rb').read()
    res = strings(d, a, b)
    lines = ['0x%X~0x%X  문자열 %d개' % (a, b, len(res))]
    for off, raw in res:
        lines.append('0x%-8X %3d B | %s' % (off, len(raw), show(raw)))
    txt = '\n'.join(lines)
    io.open(os.path.join(ROOT, 'work', 'gap.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)
