# -*- coding: utf-8 -*-
r"""祭来国 «재래국» → «제래국»(祭 = 제사 제, 2026-10-12 하스피 «원문을 살려가자»).
  天輪国 «천륜국»은 다른 나라라 그대로(제보 09 «재래국→천륜국»은 착각).
  tsv2 kr 열 + data/overrides.tsv + tools/gfx_op.py(오프닝 나레이션 그림). 받침 같아 조사 그대로.
  python work/report/jerae.py [--write]   백업 work/tsv_backup_20261012/
"""
import glob, os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    write = '--write' in sys.argv
    bk = os.path.join(ROOT, 'work', 'tsv_backup_20261012')
    files = sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv')))
    n = 0
    for p in files:
        L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
        for i, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) < 7 or '재래' not in c[6]: continue
            c[6] = c[6].replace('재래', '제래'); L[i] = '\t'.join(c); ch = True; n += 1
            print(c[0], c[6].replace('\n', '⏎')[:70])
        if ch and write:
            os.makedirs(bk, exist_ok=True)
            if not os.path.exists(os.path.join(bk, os.path.basename(p))): shutil.copy2(p, bk)
            open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
    print('tsv2', n, '줄')
    for rel in ('data/overrides.tsv', 'tools/gfx_op.py'):
        p = os.path.join(ROOT, rel); s = open(p, encoding='utf-8', newline='').read()
        k = s.count('재래'); print(rel, k, '곳')
        if write and k:
            os.makedirs(bk, exist_ok=True); shutil.copy2(p, os.path.join(bk, os.path.basename(p)))
            open(p, 'w', encoding='utf-8', newline='').write(s.replace('재래', '제래'))
    print('기록함' if write else '미리보기(--write 로 기록)')


main()
