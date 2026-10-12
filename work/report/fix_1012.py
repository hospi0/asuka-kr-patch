# -*- coding: utf-8 -*-
r"""카페 제보 05~09(2026-10-12, 드라크로아 님) 반영 — tsv2 kr 열 직접.
  수정안 = work/report/fix_1012*.tsv (id <TAB> 새 번역, 개행은 \n 두 글자, 같은 id 는 뒤 파일이 이김)
  검사: 예산(B) · 줄 폭(칸, 모든 글자 1칸 — 렌더러 고정폭) · 줄 수 · 제어열(\xNN 순서)·＠·%s/%d 보존.
  python work/report/fix_1012.py [--write]   백업 work/tsv_backup_20261012b/
"""
import glob, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from blen import blen
BS = chr(92)
ESC = re.compile(re.escape(BS) + r'x[0-9A-Fa-f]{2}')
FMT = re.compile(r'%[-0-9.]*l?[sdxXucf]')
ALLOW_CTRL = {'SCR04476', 'SCR01358', 'SCR01360', 'SCR03709'}   # 예전 번역에서  뒤  가 빠져 있던 줄 — 되살림
WIDTH_SKIP = {'SYS00259'}   # \r 로 줄이 나뉘는 메시지
LIM = {'01': 21, '02': 21, '03': 20, '04': 20, '05': 18, '06': 21, '08': 21}


def width(line): return len(ESC.sub('', line).replace('＠', ''))


def load_fixes():
    fx = {}
    for p in sorted(glob.glob(os.path.join(HERE, 'fix_1012*.tsv'))):
        for ln in open(p, encoding='utf-8').read().split('\n'):
            if not ln.strip() or ln.startswith('#'): continue
            k, v = ln.split('\t', 1); fx[k.strip()] = v
    return fx


def check(cat, r, new):
    err = []
    if blen(new) > int(r[3]): err.append('예산 %d>%s' % (blen(new), r[3]))
    if ESC.findall(new) != ESC.findall(r[6]) and r[0] not in ALLOW_CTRL: err.append('제어열 %s→%s' % (ESC.findall(r[6]), ESC.findall(new)))
    if new.count('＠') != r[6].count('＠'): err.append('＠')
    if FMT.findall(new) != FMT.findall(r[6]): err.append('서식')
    L = new.split(BS + 'n'); lim = LIM.get(cat)
    if len(L) > max(len(r[6].split(BS + 'n')), len(r[5].split(BS + 'n'))): err.append('줄 수 %d' % len(L))
    if lim and r[0] not in WIDTH_SKIP:
        old_max = max(width(x) for x in r[6].split(BS + 'n'))
        for x in L:
            if width(x) > max(lim, old_max): err.append('폭 %d>%d «%s»' % (width(x), lim, x))
    return err


def main():
    write = '--write' in sys.argv
    fx = load_fixes(); seen = set(); bad = 0
    bk = os.path.join(ROOT, 'work', 'tsv_backup_20261012b')
    for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
        cat = os.path.basename(p)[:2]
        L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
        for i, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) < 7 or c[0] not in fx: continue
            seen.add(c[0]); new = fx[c[0]]
            if new == c[6]: continue
            e = check(cat, c, new)
            print('%s %s %d/%s %s\n   - %s\n   + %s' % ('✗' if e else '✓', c[0], blen(new), c[3], '; '.join(e),
                  c[6].replace(BS + 'n', '⏎'), new.replace(BS + 'n', '⏎')))
            if e: bad += 1; continue
            c[6] = new; L[i] = '\t'.join(c); ch = True
        if ch and write:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))): shutil.copy2(p, bk)
            open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
    miss = set(fx) - seen
    print('수정안 %d · 문제 %d · 없는 id %s' % (len(fx), bad, sorted(miss)))
    print('기록함' if write else '미리보기(--write 로 기록)')


main()
