# -*- coding: utf-8 -*-
"""구간의 «여유 바이트» 원본에 진짜 데이터가 들어 있는지 검사한다.

  python tools/check_slack.py

번역문이 짧아 남는 자리를 패딩으로 채우는데, 그 자리에 원본이 «다른 데이터»를
두고 있으면 덮어버려 크래시한다 ([[feedback_padding_ate_voice_filename]]).
정상이면 여유는 전부 NUL 이어야 한다.
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
            t.append('\\x1F\\x%02X' % raw[i + 1]); i += 2
        elif c == 0x0A:
            t.append('\\n'); i += 1
        elif c == 0x00:
            t.append('·'); i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            t.append(bytes(raw[i:i + 2]).decode('cp932', 'replace')); i += 2
        else:
            t.append(chr(c) if 0x20 <= c < 0x7F else '<%02X>' % c); i += 1
    return ''.join(t)


if __name__ == '__main__':
    import build_all
    per = build_all.read_rows()
    lines, bad = [], collections.Counter()
    for name in ('DATASCR.BIN', 'SSCR.BIN'):
        p = os.path.join(ISO, name)
        if not os.path.exists(p):
            continue
        org = open(p, 'rb').read()
        for r in per.get(name, []):
            off, bud = int(r['offset'], 16), int(r['budget'])
            reg = org[off:off + bud]
            z = reg.find(0)
            if z < 0:
                continue                       # 종단자가 구간 안에 없다
            tail = reg[z + 1:]
            if not tail:
                continue
            junk = [c for c in tail if c != 0]
            if junk:
                bad[name] += 1
                if len(lines) < 60:
                    lines.append('%s %s 0x%X 예산%d 종단%d 여유%d'
                                 % (name, r['id'], off, bud, z, len(tail)))
                    lines.append('   본문: %s' % show(reg[:z]))
                    lines.append('   여유: %s' % show(tail))
    txt = '\n'.join(lines) if lines else '여유는 전부 NUL — 덮어쓸 데이터 없음'
    io.open(os.path.join(ROOT, 'work', 'slackcheck.txt'), 'w',
            encoding='utf-8').write(txt)
    print('여유에 데이터가 있는 행: %s' % (dict(bad) or '없음'))
    print(txt[:3000])
