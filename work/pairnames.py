# -*- coding: utf-8 -*-
"""아이템 이름 쌍([한자 이름][0][히라가나 이름]) 중 두 번역이 다른 것 — 칸 때문에 줄인 흔적 찾기 (2026-10-09)"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import build_all as B
BS = chr(92)
PRE = re.compile('^(?:' + re.escape(BS) + 'x[0-9A-Fa-f]{2}|' + re.escape(BS) + 't|[×XpLＸZ\\[])*')
rows = B.read_rows()['SSCR.BIN']
for a, b in zip(rows, rows[1:]):
    if B.pair_head(a, b):
        ka = PRE.sub('', a['kr']).strip(); kb = b['kr'].strip()
        if ka.replace(' ', '') != kb.replace(' ', ''):
            print(a['id'], a['budget'], b['budget'], a['jp'], '|', a['kr'], '|', b['kr'])
