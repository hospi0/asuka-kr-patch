# -*- coding: utf-8 -*-
r"""문단 → 창 폭 줄바꿈 → 수정안 파일(제보 05~09, 몬스터·아이템 설명 다시 쓰기).
  입력 work/report/<이름>_src.tsv : id <TAB> 문단(줄바꿈 없이, 강제 줄바꿈은 «|»)
  출력 work/report/fix_1012_<이름>.tsv (fix_1012.py 가 읽음)
  python work/report/wrapfix.py <이름> <폭> <최대줄수(0=원문 줄 수)>
  원래 번역이 \n 으로 끝나면 끝 \n 을 붙인다. 공백→개행이라 바이트는 그대로.
"""
import csv, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from blen import blen
BS = chr(92); N = BS + 'n'
import re
ESC = re.compile(re.escape(BS) + r'x[0-9A-Fa-f]{2}')


def wd(x): return len(ESC.sub('', x))
name, W, ML = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rows = {}
for p in glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv')):
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) >= 7: rows[r[0]] = r


def wrap(par):
    out = []
    for para in par.split('|'):
        line = ''
        for w in para.split(' '):
            if not line: line = w
            elif wd(line) + 1 + wd(w) <= W: line += ' ' + w
            else: out.append(line); line = w
        out.append(line)
    return out


bad = 0; res = []
for ln in open(os.path.join(HERE, name + '_src.tsv'), encoding='utf-8').read().split('\n'):
    if not ln.strip() or ln.startswith('#'): continue
    ids, par = ln.split('\t', 1)
    for k in ids.split(','):
        r = rows[k]; L = wrap(par.strip())
        new = N.join(L) + (N if r[6].endswith(N) else '')
        e = []
        nl = len(L) + (1 if r[6].endswith(N) else 0)   # 끝 개행도 한 줄로 센다(원문과 같은 자)
        ml = ML or len(r[5].split(N))   # 0 이면 원문 줄 수(끝 개행 포함)
        if nl > ml: e.append('줄 %d>%d' % (nl, ml))
        if any(wd(x) > W for x in L): e.append('폭')
        if blen(new) > int(r[3]): e.append('예산 %d>%s' % (blen(new), r[3]))
        if e:
            bad += 1; print('✗', k, '; '.join(e), '|', ' / '.join(L))
        res.append((k, new))
open(os.path.join(HERE, 'fix_1012_%s.tsv' % name), 'w', encoding='utf-8').write(
    '# wrapfix.py %s 폭 %d 줄 %d 로 생성 — 손으로 고치지 말 것(%s_src.tsv 를 고칠 것)\n' % (name, W, ML, name) +
    ''.join('%s\t%s\n' % kv for kv in res))
print('%d개 · 문제 %d' % (len(res), bad))
