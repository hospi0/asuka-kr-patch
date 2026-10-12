# -*- coding: utf-8 -*-
"""04 몬스터 설명(에레키상자 창) 덤프: python work/report/mon_dump.py 시작 개수"""
import csv, glob, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work/report')
from blen import blen
BS = chr(92)
s, n = int(sys.argv[1]), int(sys.argv[2])
rows = []
for p in sorted(glob.glob('my files/tsv2/04_*.tsv')):
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) >= 7 and r[0] != 'id' and r[5].count(BS + 'n') >= 5: rows.append(r)
seen = {}
for r in rows[s:s + n]:
    if r[5] in seen: print('%s = %s' % (r[0], seen[r[5]])); continue
    seen[r[5]] = r[0]
    print('%s b=%s n=%d | %s\n   %s' % (r[0], r[3], blen(r[6]), r[5].replace(BS + 'n', ''), r[6].replace(BS + 'n', '⏎')))
