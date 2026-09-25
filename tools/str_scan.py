# -*- coding: utf-8 -*-
"""NUL 로 끝나는 Shift-JIS 문자열 후보 스캔 (읽기 전용, 분량 하한 추정용).

바이트 앞쪽에 제어 바이트가 붙어 있어도 되도록 «뒤에서 앞으로» 최대 SJIS 런을
잡는다. 종단자(0x00)를 만난 지점에서 역방향으로 확장한다.
"""
import sys, os, re

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

def _lead(b): return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef
def _trail(b): return 0x40 <= b <= 0xfc and b != 0x7f
def _single(b): return b == 0x0a or 0x20 <= b <= 0x7e or 0xa1 <= b <= 0xdf

def strings(d, minchars=2):
    out = []
    n = len(d)
    i = 0
    while i < n:
        if d[i] != 0:
            i += 1; continue
        # i 는 종단자. 앞으로 되짚어 SJIS 런의 시작을 찾는다.
        end = i
        j = end
        starts = []
        while j > 0:
            if j >= 2 and _lead(d[j-2]) and _trail(d[j-1]):
                j -= 2; starts.append(j)
            elif _single(d[j-1]):
                j -= 1; starts.append(j)
            else:
                break
        best = None
        for s in starts:
            raw = d[s:end]
            try:
                t = raw.decode('cp932')
            except UnicodeDecodeError:
                continue
            if len(t) >= minchars and JP.search(t):
                best = (s, t)
        if best:
            out.append(best)
        i += 1
    # 겹치는 후보 제거(가장 긴 것만)
    out.sort()
    ded = []
    last_end = -1
    for s, t in out:
        if s >= last_end:
            ded.append((s, t)); last_end = s + len(t.encode('cp932'))
    return ded

if __name__ == '__main__':
    tot_s = tot_c = 0
    for p in sys.argv[1:]:
        d = open(p, 'rb').read()
        r = strings(d)
        c = sum(len(s) for _, s in r)
        tot_s += len(r); tot_c += c
        print("%-16s strings=%6d chars=%7d" % (os.path.basename(p), len(r), c))
    print("%-16s strings=%6d chars=%7d" % ('TOTAL', tot_s, tot_c))
