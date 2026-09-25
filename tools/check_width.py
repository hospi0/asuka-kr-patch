# -*- coding: utf-8 -*-
"""빌드 결과에서 «창 폭을 넘는 줄» 을 전부 찾는다 (디스크 안 건드림).

  python tools/check_width.py

★2026-08-30 실기: 폭을 넘긴 줄에서 바이오스 크래시가 났다.
  패딩을 한 줄에 몰아넣으면 그 줄이 부풀어 창 버퍼를 넘는다.
"""
import io, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')


def show(raw):
    t, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == 0x1F and i + 1 < len(raw):
            t.append('<P>'); i += 2
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            t.append(bytes(raw[i:i + 2]).decode('cp932', 'replace')); i += 2
        else:
            t.append(chr(c) if 0x20 <= c < 0x7F else '<%02X>' % c); i += 1
    return ''.join(t)


if __name__ == '__main__':
    import build_all
    _, cm, outbin = build_all.build(write=False)
    per = build_all.read_rows()
    lim = build_all.line_limits(per)

    bad = collections.Counter()
    lines = []
    for name in ('DATASCR.BIN', 'SSCR.BIN'):
        if name not in outbin:
            continue
        org = open(os.path.join(ISO, name), 'rb').read()
        new = outbin[name]
        for r in per.get(name, []):
            off, bud = int(r['offset'], 16), int(r['budget'])
            L = lim.get(r['_cat'])
            if not L:
                continue
            a, b = org[off:off + bud], new[off:off + bud]
            if a == b:
                continue
            body = b.split(b'\x00')[0]
            for k, seg in enumerate(body.split(b'\n')):
                c = build_all.byte_cells(seg)
                if c > L:
                    bad[name] += 1
                    lines.append('%s\t%s\t0x%X\t%d번째줄\t%d칸>%d칸\t%s'
                                 % (name, r['id'], off, k, c // 2, L // 2,
                                    show(seg).rstrip()))
                    break
    lines.insert(0, '창 폭 초과 %s' % dict(bad))
    txt = '\n'.join(lines) if len(lines) > 1 else '창 폭을 넘는 줄 없음'
    io.open(os.path.join(ROOT, 'work', 'widthcheck.txt'), 'w',
            encoding='utf-8').write(txt)
    print('\n=== 창 폭 초과: %s' % (dict(bad) or '없음'))
    print(txt[:3000])
