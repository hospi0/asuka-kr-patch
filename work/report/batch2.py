# -*- coding: utf-8 -*-
"""kiwi_scan2.tsv → 손질용 묶음. python work/report/batch2.py 접두 시작 개수"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
pre, s, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
R = [l.rstrip('\n').split('\t') for l in open('work/report/kiwi_scan2.tsv', encoding='utf-8') if l[:3] in ('SCR', 'SYS', 'EXE')]
R = [r for r in R if r[1].startswith(pre)]
print('# 전체', len(R))
for r in R[s:s + n]:
    print('%s b=%s n=%s | %s\n   %s' % (r[0], r[3], r[4], r[5], r[7]))
