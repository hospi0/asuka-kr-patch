# -*- coding: utf-8 -*-
"""설명문·대사 속 족자 이름을 아이템 이름표(05_아이템명 표기형)와 맞춤 (2026-10-09)
   원문에 «○○の巻物»가 있고 번역에 «△△의 족자 / △△ 족자 / △△의족자»(△△ ≠ 이름표)가 있으면 이름표 이름으로.
   python work/scroll_text_sync.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92); NL = BS + 'n'
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')
PRE = re.compile(r'^((?:' + re.escape(BS) + r'x[0-9A-Fa-f]{2}|[×XpL])*)')


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub('\x01', s))


def width(line):
    return len(ESC.sub('', line))


files = sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv')))
data = {p: open(p, encoding='utf-8', newline='').read().split('\n') for p in files}
name = {}                                    # 원문 앞부분(漢字형) → 한글 이름표
for p in files:
    if '05_아이템명' in p:
        for ln in data[p]:
            c = ln.split('\t')
            if len(c) >= 7 and c[5].endswith('の巻物') and c[6].endswith('족자'):
                jp = PRE.sub('', c[5])[:-3]; kr = c[6][len(PRE.match(c[6]).group(1)):]
                name[jp] = kr
MULTI = ['갖고 돌아가기 족자', '지참 귀환의 족자', '땅의 축복 족자', '하늘축복 족자']
SKIP = {'SCR03583'}            # 「識」만 색 코드로 감싼 줄 — 손으로
n = 0; bad = []
for p in files:
    if '05_아이템명' in p:
        continue
    L = data[p]; ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or '족자' not in c[6] or c[0] in SKIP:
            continue
        want = [name[j] for j in name if j + 'の巻物' in ESC.sub('', c[5]).replace(NL, '')]
        new = c[6]
        for w in want:
            if w in new:
                continue
            # 이름표에 없는 꼴의 «… 족자» 하나를 이 이름으로: 직전 1~3어절 + (의) + 족자
            m = None
            for pat in MULTI:                                        # 여러 낱말 옛 이름(손으로)
                if pat in new:
                    new = new.replace(pat, w); break
            else:
                m = re.search(r'([가-힣]+)\s?의?\s?족자', new)        # 이름 바로 앞 한 낱말만
            if m and not any(x in m.group(0) for x in name.values()) and '기묘한' not in m.group(0):
                new = new[:m.start()] + w + new[m.end():]
        if new == c[6]:
            continue
        ow = max(width(x) for x in c[6].split(NL)); nw = max(width(x) for x in new.split(NL))
        if blen(new) > int(c[3]) or nw > max(ow, 20):
            bad.append((c[0], c[6], new)); continue
        print(c[0], '|', c[5][:30], '|', repr(c[6])[:60], '→', repr(new)[:60])
        c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 · 칸 넘쳐 그대로', len(bad))
for b in bad:
    print('  그대로', b)
