# -*- coding: utf-8 -*-
"""조사 자동 선택이 생겼으니 빠졌던 조사를 넣는다 (2026-10-09 실기 «도우타누키+1 장비했다» · «을(를)»)
   ① «%s은(는)»류 괄호 병기 → «%s은 »
   ② 원문 %sを/%sは/%sが 인데 번역 %s 뒤 조사가 없으면 → %s을/은/이 (엔진이 받침 보고 고름, 뒤는 띄어씀)
   칸(바이트) 넘치면 그 행은 그대로 두고 보고. tsv2 kr 열만. python work/josa_fill.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92)
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')
J = {'を': '을', 'は': '은', 'が': '이'}
PART = '을를은는이가의에과와로'


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub('\x01', s))


n = 0; bad = []
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or not c[6]:
            continue
        new = re.sub(r'%s(은|을|이|과)\((는|를|가|와)\) ?', r'%s\1 ', c[6])
        jp = [m.group(1) for m in re.finditer(r'%s([をはが]?)', c[5])]
        ks = list(re.finditer(r'%s', new))
        for idx in reversed(range(min(len(jp), len(ks)))):
            j = jp[idx]
            if not j:
                continue
            e = ks[idx].end()
            if new[e:e + 1] and new[e:e + 1] in PART:
                continue
            rest = new[e:].lstrip(' ')
            new = new[:e] + J[j] + (' ' + rest if rest else '')     # 끝이면 띄어쓰기 없이(NUL 이 «끝»으로 판정됨)
        new = {'SYS03690': '가짜%s이 터졌다', 'SYS03938': '%s을 통달!', 'SYS03943': '%s을 통달!'}.get(c[0], new)
        if new == c[6]:
            continue
        if blen(new) > int(c[3]):
            # 넘치면 «다/했다» 끝 부호·공백부터 줄여 본다
            t = re.sub(r'[.。!！]$', '', new)
            if blen(t) <= int(c[3]):
                new = t
            else:
                bad.append((c[0], c[3], c[6], new, blen(new))); continue
        print(c[0], c[3], repr(c[6]), '→', repr(new))
        c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 · 칸 넘쳐 그대로', len(bad))
for b in bad:
    print('  그대로', b)
