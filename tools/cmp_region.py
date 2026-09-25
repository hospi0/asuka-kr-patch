# -*- coding: utf-8 -*-
"""원본과 빌드 결과를 «구간 단위로» 나란히 덤프한다 (디스크 안 건드림).

  python tools/cmp_region.py 0x23900 0x24100
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


def chunks(d, a, b):
    """NUL 로 구분된 조각들"""
    res, i = [], a
    while i < b:
        while i < b and d[i] == 0:
            i += 1
        s = i
        while i < b and d[i] != 0:
            i += 1
        if i > s:
            res.append((s, d[s:i]))
    return res


if __name__ == '__main__':
    a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
    import build_all
    _, cm, outbin = build_all.build(write=False)
    org = open(os.path.join(ISO, 'DATASCR.BIN'), 'rb').read()
    new = outbin['DATASCR.BIN']
    per = build_all.read_rows()
    known = {int(r['offset'], 16) for r in per['DATASCR.BIN']}

    lines = ['0x%X~0x%X' % (a, b)]
    for s, raw in chunks(org, a, b):
        nb = new[s:s + len(raw)]
        # 이 조각 안에 번역표 행이 있나
        hit = [o for o in known if s <= o < s + len(raw)]
        tag = ('행 %s' % ','.join('0x%X' % o for o in sorted(hit))) if hit else '★표에 없음'
        lines.append('')
        lines.append('0x%-7X %3d B  %s' % (s, len(raw), tag))
        lines.append('   원본: %s' % show(raw))
        if nb != raw:
            lines.append('   빌드: %s' % show(nb))
    txt = '\n'.join(lines)
    io.open(os.path.join(ROOT, 'work', 'cmpregion.txt'), 'w',
            encoding='utf-8').write(txt)
    print(txt[:8000])
