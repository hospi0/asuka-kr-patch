# -*- coding: utf-8 -*-
"""항아리 이름 «X항아리» → «X의 항아리» (2026-10-09 사용자 «~의 항아리로 해도 괜찮을듯»)
   대상 = 원문이 «〜の壺» 인 아이템 이름(05). 같은 이름이 나오는 다른 행(원문에 그 일본어 이름이 있는 줄)도 같이.
   칸 넘치면 그대로 두고 보고. python work/pot_names.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_all as B
BS = chr(92); N = BS + 'n'
CTRL = '[' + chr(0) + '-' + chr(31) + ']'
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')|' + CTRL)


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub(chr(1), s))


def width(s):
    return max(len(ESC.sub('', x)) for x in s.split(N))


per = B.read_rows()
srows = per['SSCR.BIN']
pair = {}
for k in range(len(srows) - 2):
    a, b, n = srows[k], srows[k + 1], srows[k + 2]
    if B.pair_head(a, b) and int(n['offset'], 16) - int(b['offset'], 16) - int(b['budget']) >= 31:
        pair[a['id']] = b
# 1) 이름 대응
names = {}                                   # 옛 이름 -> (새 이름, 일본어 이름)
for r in srows:
    if r['_cat'].startswith('05') and r['id'] in pair:
        jp = re.sub('^[^ぁ-んァ-ヶ一-龥]*', '', r['jp'])
        kr = re.sub('^[^가-힣]*', '', r['kr'])
        if jp.endswith('の壺') and kr.endswith('항아리') and not kr.endswith('의 항아리'):
            base = re.sub('의? ?항아리$', '', kr).strip()
            names[kr] = ((base + ' 항아리') if re.search('(진|은|한|짝)$', base) else (base + '의 항아리'), jp)   # 꾸밈말(밑빠진·깜짝)은 «의» 없이
for o, (nw, jp) in sorted(names.items(), key=lambda x: x[1][1]):
    print('이름', jp, ':', o, '→', nw)
# 2) 행마다 바꾸기
new = {}; bad = []
for rows in per.values():
    for r in rows:
        t = r['kr']
        if not t or t == '=':
            continue
        for o, (nw, jp) in sorted(names.items(), key=lambda x: -len(x[0])):
            base = re.sub(' ?항아리$', '', o)
            if jp in r['jp']:
                t = re.sub('(?<![가-힣])' + re.escape(base) + '(의)? ?항아리', nw, t)   # 띄어쓰기 변형(창고 항아리)까지
        t = {'SYS04350': '풍래인「난 변화의 항아리가 좋아…。', 'SYS04496': '풍래인「난 변화의 항아리가 좋더라…'}.get(r['id'], t)   # 칸 2 B 모자람 — 손질
        if t == r['kr']:
            continue
        if r['id'] in pair:
            ok = blen(t) + 1 + (0 if pair[r['id']]['kr'] == '=' else blen(pair[r['id']]['kr'])) <= int(r['budget']) + 1 + int(pair[r['id']]['budget'])
        else:
            ok = blen(t) <= int(r['budget']) and width(t) <= max(width(r['kr']), 20)
        if ok:
            new[r['id']] = t; print(r['id'], '|', r['kr'].replace(N, ' / ')[:70], '→', t.replace(N, ' / ')[:70])
        else:
            bad.append((r['id'], r['budget'], r['kr'], t))
print('바꿈', len(new), '· 못 바꿈', len(bad))
for x in bad:
    print('  그대로', x[0], '칸', x[1], '|', x[2].replace(N, ' / ')[:70], '→', x[3].replace(N, ' / ')[:70])
if '--write' in sys.argv:
    for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
        L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
        for k, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) >= 7 and c[0] in new and c[6] != new[c[0]]:
                c[6] = new[c[0]]; L[k] = '\t'.join(c); ch = True
        if ch:
            open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
    print('기록')
