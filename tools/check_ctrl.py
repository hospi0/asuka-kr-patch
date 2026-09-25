# -*- coding: utf-8 -*-
"""빌드 결과의 «VM 이 읽는 불변식» 을 전 구간에서 검사한다 (디스크 안 건드림).

  python tools/check_ctrl.py [0xB3000 0xB5000]

크래시의 전형적 원인:
  ①제어코드 `\\x1F\\xNN` 의 «인수 바이트»가 잘림 (구간 끝에 \\x1F 만 남음)
  ②제어코드 개수가 원문과 달라짐 (번역에서 빠뜨림)
  ③구간 안에 NUL 이 새로 생김 — VM 이 명령어로 실행한다
     [[feedback_nul_padding_crashes_vm_embedded_strings]]
  ④종단자 위치가 원본과 달라짐 [[feedback_padding_ate_voice_filename]]
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')


def ctrl_spots(b):
    """(위치, 인수) 목록. 인수가 없으면 인수 None."""
    out, i = [], 0
    while i < len(b):
        if b[i] == 0x1F:
            out.append((i, b[i + 1] if i + 1 < len(b) else None))
            i += 2
        else:
            i += 1
    return out


def show(raw):
    t, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == 0x1F:
            t.append('\\x1F\\x%02X' % raw[i + 1] if i + 1 < len(raw) else '\\x1F<잘림>')
            i += 2
        elif c == 0x0A:
            t.append('\\n'); i += 1
        elif c == 0x00:
            t.append('<NUL>'); i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            t.append(bytes(raw[i:i + 2]).decode('cp932', 'replace')); i += 2
        else:
            t.append(chr(c) if 0x20 <= c < 0x7F else '<%02X>' % c); i += 1
    return ''.join(t)


if __name__ == '__main__':
    import build_all
    font, cm, outbin = build_all.build(write=False)
    lo = int(sys.argv[1], 16) if len(sys.argv) > 2 else None
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else None

    per = build_all.read_rows()
    bad, lines = 0, []
    for name in ('DATASCR.BIN', 'SSCR.BIN'):
        if name not in outbin:
            continue
        org = open(os.path.join(ISO, name), 'rb').read()
        new = outbin[name]
        for r in per.get(name, []):
            off, bud = int(r['offset'], 16), int(r['budget'])
            if lo is not None and not (lo <= off < hi):
                continue
            a, b = org[off:off + bud], new[off:off + bud]
            if a == b:
                continue
            msgs = []
            ca, cb = ctrl_spots(a), ctrl_spots(b)
            if len(ca) != len(cb):
                msgs.append('제어코드 %d개 -> %d개' % (len(ca), len(cb)))
            if any(x[1] is None for x in cb):
                msgs.append('★인수 잘린 \\x1F 있음')
            if [x[1] for x in ca] != [x[1] for x in cb]:
                msgs.append('제어코드 인수가 다름 %s -> %s'
                            % ([hex(x[1]) if x[1] is not None else '?' for x in ca],
                               [hex(x[1]) if x[1] is not None else '?' for x in cb]))
            na, nb = a.count(0), b.count(0)
            if nb != na:
                msgs.append('NUL %d개 -> %d개' % (na, nb))
            if a.find(0) != b.find(0):
                msgs.append('종단자 위치 %d -> %d' % (a.find(0), b.find(0)))
            if msgs:
                bad += 1
                lines.append('%s %s 0x%X (예산 %d)' % (name, r['id'], off, bud))
                for m in msgs:
                    lines.append('   ! ' + m)
                lines.append('   원본: %s' % show(a))
                lines.append('   빌드: %s' % show(b))
    txt = '\n'.join(lines) if lines else '문제 없음'
    io.open(os.path.join(ROOT, 'work', 'ctrlcheck.txt'), 'w',
            encoding='utf-8').write(txt)
    print('\n=== 제어코드·종단자 검사: 문제 %d건' % bad)
    print(txt[:4000])
