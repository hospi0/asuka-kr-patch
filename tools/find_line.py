# -*- coding: utf-8 -*-
"""원본 바이너리에서 «그 문자열» 을 찾는다 (추출표에 없어도).

  python tools/find_line.py 頭領
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')


def show(raw):
    t, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == 0x1F and i + 1 < len(raw):
            t.append('\\x1F\\x%02X' % raw[i + 1]); i += 2
        elif c == 0x0A:
            t.append('\\n'); i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            t.append(bytes(raw[i:i + 2]).decode('cp932', 'replace')); i += 2
        else:
            t.append(chr(c) if 0x20 <= c < 0x7F else '<%02X>' % c); i += 1
    return ''.join(t)


def around(d, i):
    """i 를 품는 NUL 사이 문자열의 시작·끝"""
    s = d.rfind(b'\x00', 0, i) + 1
    e = d.find(b'\x00', i)
    return s, (e if e >= 0 else len(d))


if __name__ == '__main__':
    pat = sys.argv[1].encode('cp932')
    lines = []
    for name in ('DATASCR.BIN', 'SSCR.BIN'):
        p = os.path.join(ISO, name)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read()
        i, n = 0, 0
        while True:
            i = d.find(pat, i)
            if i < 0:
                break
            s, e = around(d, i)
            if e - s < 400:
                lines.append('%s 0x%X (%d B) | %s' % (name, s, e - s, show(d[s:e])))
                n += 1
            i += 1
        lines.insert(0, '%s: %d건' % (name, n)) if n else None
    txt = '\n'.join(lines)
    io.open(os.path.join(ROOT, 'work', 'findline.txt'), 'w',
            encoding='utf-8').write(txt)
    print(txt[:6000])
