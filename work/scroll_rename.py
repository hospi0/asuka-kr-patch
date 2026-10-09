# -*- coding: utf-8 -*-
"""족자 이름 정리 (2026-10-09 사용자 «나무위키 참고해서 전부 족자로»)
   아이템 이름(巻物) = 앞부분 + «족자» — «의»·띄어쓰기 뺌. 앞부분은 나무위키(풍래의 시렌/등장 아이템)와 다른 것만 맞춤.
   설명문·대사에 나오는 옛 이름(«감정의 족자» 등)도 새 이름으로. 칸(바이트)·줄 폭 넘치면 그 행은 그대로 두고 보고.
   tsv2 kr 열만. python work/scroll_rename.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92); NL = BS + 'n'
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')
WIKI = {'감정': '식별', '빛': '밝힘', '액막이': '살풀이', '단지확대': '단지증대',
        '하늘의은혜': '하늘의은총', '대지의은혜': '땅의은총'}


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub('\x01', s))


def width(line):
    return len(ESC.sub('', line))


files = sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv')))
data = {p: open(p, encoding='utf-8', newline='').read().split('\n') for p in files}
# ① 아이템 이름표에서 «옛 앞부분 → 새 앞부분» 표
PRE = re.compile(r'^((?:' + re.escape(BS) + r'x[0-9A-Fa-f]{2}|[×XpL])*)')
names = {}                     # 옛 앞부분(띄어쓰기 없앤 것) → 새 앞부분
for p in files:
    if '05_아이템명' not in p:
        continue
    for ln in data[p]:
        c = ln.split('\t')
        if len(c) >= 7 and ('巻物' in c[5] or 'まきもの' in c[5]) and c[6].endswith('족자'):
            pre = PRE.match(c[6]).group(1)
            body = re.sub(r'의?\s*족자$', '', c[6][len(pre):]).replace(' ', '')
            if body:
                names[body] = WIKI.get(body, body)
print('족자 이름', len(names))
# 옛 이름 꼴(띄어쓰기·의 유무 여러 가지) → 새 이름
pats = []
for old, new in sorted(names.items(), key=lambda x: -len(x[0])):
    sp = r'\s?'.join(map(re.escape, old))                     # 글자 사이 띄어쓰기 허용(«큰 방», «몬스터 하우스»)
    pats.append((re.compile(sp + r'\s?의?\s?족자'), new + '족자'))
n = 0; bad = []
for p in files:
    L = data[p]; ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or '족자' not in c[6]:
            continue
        new = c[6]
        for rx, rep in pats:
            new = rx.sub(rep, new)
        if new == c[6]:
            continue
        ow = max(width(x) for x in c[6].split(NL)); nw = max(width(x) for x in new.split(NL))
        if blen(new) > int(c[3]) or nw > max(ow, 20):
            bad.append((c[0], c[3], c[6], new)); continue
        import difflib
        for t, a1, a2, b1, b2 in difflib.SequenceMatcher(None, c[6], new).get_opcodes():
            if t != 'equal':
                print(c[0], repr(c[6][max(0, a1 - 6):a2 + 4]), '→', repr(new[max(0, b1 - 6):b2 + 4]))
        c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 바꿈 · 칸 넘쳐 그대로', len(bad))
for b in bad:
    print('  그대로', b)
