# -*- coding: utf-8 -*-
"""SCR01488 — 빠진 마지막 줄을 채운다.

2026-08-30 실기: 이 대사가 나오는 순간 바이오스 크래시.
원문은 3줄인데 번역이 마지막 줄 「　ウウ……」을 통째로 빼먹어 16 B 가 남았고,
그 채움이 둘째 줄 끝에 몰려 그 줄이 25칸(상한 20칸)이 됐다.
"""
import io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'my files', 'tsv2', '01_대사_06.tsv')
C = '\x1f\x0f'                      # 이 표의 한국어 칸은 «생 제어바이트»를 쓴다
NEW = ('두령「우우' + C + '…' + C + '…' + C + '\\n'
       '아이템……' + C + '내놔……' + C + '\\n'
       '우우……')

if __name__ == '__main__':
    lines = io.open(P, encoding='utf-8', newline='').read().split('\n')
    hit = 0
    for i, ln in enumerate(lines):
        c = ln.rstrip('\r').split('\t')
        if c and c[0] == 'SCR01488':
            old = c[6]
            c[6] = NEW
            lines[i] = '\t'.join(c)
            hit += 1
            print('이전: %r' % old)
            print('이후: %r' % NEW)
    if not hit:
        raise SystemExit('SCR01488 을 못 찾았다')
    io.open(P, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s (%d행 수정)' % (P, hit))
