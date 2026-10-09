# -*- coding: utf-8 -*-
"""조사 자동 선택(tools/patch_josa.py) 준비 — tsv2 kr 열만:
   ① «%s을(를)» → «%s을 »(괄호 병기 대신 엔진이 고름, 조사 뒤 띄어씀)
   ② 보고: %s 바로 뒤 조사(은는을를이가과와) 다음이 붙은 한글이라 자동 선택이 안 걸리는 줄
   python work/josa_prep.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = 0; stuck = []
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or not c[6]:
            continue
        new = re.sub(r'%s을\(를\) ?', '%s을 ', c[6])
        if c[0] in ('SYS03114', 'SYS03469', 'SYS03691'):        # 진짜 조사인데 띄어쓰기 빠짐 → 자동 선택 걸리게
            new = re.sub(r'%s([가를])(?=[가-힣])', r'%s\1 ', new)
        if new != c[6]:
            print(c[0], repr(c[6]), '→', repr(new)); c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
        for m in re.finditer(r'%s([은는을를이가과와])([가-힣])', c[6]):
            stuck.append((c[0], c[6][max(0, m.start() - 6):m.end() + 6]))
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 바꿈')
print('자동 선택 안 걸리는 자리(조사 뒤 붙은 한글)', len(stuck))
for s in stuck[:40]:
    print('  ', s)
