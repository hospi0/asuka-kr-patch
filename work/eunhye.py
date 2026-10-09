# -*- coding: utf-8 -*-
"""은총 → 은혜 (2026-10-09 사용자 «은총은 은혜로 바꾸자») — 받침 없어지니 뒤 조사도 고친다. 길이 같음.
   python work/eunhye.py [--write]"""
import difflib, glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = [('을', '를'), ('이', '가'), ('은', '는'), ('과', '와'), ('으로', '로'), ('이라', '라'), ('이랑', '랑'), ('이나', '나'), ('이야', '야')]


def conv(t):
    out = ''; i = 0
    while True:
        k = t.find('은총', i)
        if k < 0:
            return out + t[i:]
        out += t[i:k] + '은혜'; i = k + 2
        for a, b in sorted(J, key=lambda x: -len(x[0])):
            if t.startswith(a, i) and (a not in ('이', '은') or i + len(a) >= len(t) or not ('가' <= t[i + len(a)] <= '힣')):
                out += b; i += len(a); break


n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) >= 7 and '은총' in c[6]:
            new = conv(c[6])
            for t, a1, a2, b1, b2 in difflib.SequenceMatcher(None, c[6], new).get_opcodes():
                if t != 'equal':
                    print(c[0], repr(c[6][max(0, a1 - 4):a2 + 4]), '→', repr(new[max(0, b1 - 4):b2 + 4]))
            c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행')
