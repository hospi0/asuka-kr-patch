# -*- coding: utf-8 -*-
r"""아이템 이름 «~의» 뒤 띄어쓰기 일괄(2026-10-11 사용자) — 05_아이템명 kr 열. «의» 다음이 한글이면 공백 1칸.
  python work/report/ui_space.py [--write]  백업 work/tsv_backup_20261011_ui/
"""
import csv, glob, os, re, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAT = re.compile('의(?=[가-힣])')


def main():
    out = {}; n = 0; ids = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '05_아이템명_*.tsv'))):
        L = open(p, encoding='utf-8').read().split('\n'); ch = False
        for i, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) < 7 or c[0] == 'id' or '의' not in c[6]: continue
            new = PAT.sub('의 ', c[6])
            if new != c[6]:
                n += 1; ids.append(c[0]); print(c[0], c[3], c[6], '→', new); c[6] = new; L[i] = '\t'.join(c); ch = True
        if ch: out[p] = '\n'.join(L)
    print('바뀐 줄', n)
    if '--write' in sys.argv:
        bk = os.path.join(ROOT, 'work', 'tsv_backup_20261011_ui'); os.makedirs(bk, exist_ok=True)
        for p, s in out.items():
            shutil.copy(p, os.path.join(bk, os.path.basename(p))); open(p, 'w', encoding='utf-8', newline='').write(s)
        open(os.path.join(ROOT, 'work', 'report', 'ui_space_ids.txt'), 'w').write('\n'.join(ids))
        print('썼음')


if __name__ == '__main__':
    main()
