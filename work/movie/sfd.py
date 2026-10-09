# -*- coding: utf-8 -*-
"""Sofdec SFD(MPEG-1 PS) 분해 — 팩·패킷 목록, 영상 ES, GOP 머리
   python sfd.py OP.SFD   → 요약 출력, op_video.m1v 저장"""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')


def packets(b):
    """(팩 시작, 스트림 id, 패킷 시작, 페이로드 시작, 페이로드 끝) 목록"""
    out = []; i = 0; n = len(b)
    while i < n - 4:
        if b[i:i + 3] != b'\x00\x00\x01':
            raise SystemExit('동기 깨짐 0x%X' % i)
        sid = b[i + 3]
        if sid == 0xBA:                       # MPEG-1 팩 머리 12 B
            i += 12; continue
        if sid == 0xB9:                       # 끝 코드 — 뒤는 FF 채움
            break
        ln = struct.unpack_from('>H', b, i + 4)[0]
        st = i + 6; en = st + ln
        p = st
        if sid not in (0xBB, 0xBE, 0xBF):
            while b[p] == 0xFF:
                p += 1
            if b[p] & 0xC0 == 0x40:
                p += 2
            if b[p] & 0xF0 == 0x20:
                p += 5
            elif b[p] & 0xF0 == 0x30:
                p += 10
            elif b[p] == 0x0F:
                p += 1
        out.append((i, sid, st, p, en))
        i = en
    return out


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    P = packets(b)
    import collections
    c = collections.Counter(x[1] for x in P)
    print({hex(k): v for k, v in c.items()})
    es = b''.join(b[p:e] for _, s, _, p, e in P if s == 0xE0)
    open(sys.argv[2] if len(sys.argv) > 2 else 'op_video.m1v', 'wb').write(es)
    print('영상 ES', len(es))
    # GOP 머리
    k = 0; g = 0; pics = 0
    while True:
        k = es.find(b'\x00\x00\x01', k)
        if k < 0:
            break
        code = es[k + 3]
        if code == 0xB8:
            tc = struct.unpack_from('>I', es, k + 4)[0]
            closed = (tc >> 6) & 1; broken = (tc >> 5) & 1
            if g < 400:
                print('GOP %3d ES 0x%07X  그림 %5d  닫힘 %d 깨짐 %d' % (g, k, pics, closed, broken))
            g += 1
        elif code == 0x00:
            pics += 1
        k += 4
    print('GOP', g, '그림', pics)
