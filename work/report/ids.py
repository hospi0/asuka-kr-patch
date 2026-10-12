# -*- coding: utf-8 -*-
"""id 로 번역 행 보기: python work/report/ids.py SCR00001 SYS00002 ..."""
import glob, csv, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work/report')
from blen import blen
want = set(sys.argv[1:])
for p in sorted(glob.glob('my files/tsv2/*.tsv')):
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) >= 7 and r[0] in want:
            print('%s b=%s n=%d | %s\n   %s' % (r[0], r[3], blen(r[6]), r[5], r[6]))
