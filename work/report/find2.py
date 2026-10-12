# -*- coding: utf-8 -*-
"""번역 검색(제어열·공백 무시, 전문 출력)."""
import glob, csv, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
rows = []
for p in sorted(glob.glob('my files/tsv2/*.tsv')):
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) >= 7 and r[0] != 'id': rows.append(r)


def norm(s): return re.sub(re.escape(BS) + r'x[0-9A-Fa-f]{2}|' + re.escape(BS) + r'n|[\s　]', '', s)


for q in sys.argv[1:]:
    hits = [r for r in rows if norm(q) in norm(r[6]) or norm(q) in norm(r[5])]
    print('##', q, len(hits))
    for r in hits[:8]: print('  ', r[0], r[3], '|', r[5].replace(BS + 'n', '⏎'), '|', r[6].replace(BS + 'n', '⏎'))
