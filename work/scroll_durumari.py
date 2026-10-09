# -*- coding: utf-8 -*-
"""족자 → 두루마리 (2026-10-09 사용자 «다 두루마리로 바꾸고 싶어서 이름을 시험한거야»)
   이름(아이템 쌍)은 [한자 이름][0][히라가나 이름] 합계 바이트 안에서(빌더 pair_head 와 같은 조건),
   히라가나 칸이 모자라면 그쪽만 «족자» 그대로 둔다(표시 안 되는 칸). 그 밖의 행은 자기 칸 안에서만.
   족자·두루마리 둘 다 받침 없음 → 조사 그대로. python work/scroll_durumari.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_all as B
BS = chr(92)
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub('\x01', s))


def width(s):
    return max(len(ESC.sub('', x)) for x in s.split(BS + 'n'))


rows = B.read_rows()['SSCR.BIN'] + B.read_rows().get('DATASCR.BIN', []) + B.read_rows().get('1NOSDC.BIN', [])
srows = B.read_rows()['SSCR.BIN']
pair = {}            # 머리 id -> 꼬리 행
for k in range(len(srows) - 2):
    a, b, n = srows[k], srows[k + 1], srows[k + 2]
    if B.pair_head(a, b) and int(n['offset'], 16) - int(b['offset'], 16) - int(b['budget']) >= 31:
        pair[a['id']] = b
tail_of = {b['id']: a for a, b in ((r, pair[r['id']]) for r in srows if r['id'] in pair)}
byid = {r['id']: r for r in rows}

new = {}; bad = []
for r in rows:
    if '족자' not in r['kr'] or r['id'] in tail_of:
        continue
    t = r['kr'].replace('족자', '두루마리')
    if r['id'] in pair:
        b = pair[r['id']]; tot = int(r['budget']) + 1 + int(b['budget'])
        tb = b['kr'].replace('족자', '두루마리')
        if blen(t) + 1 + blen(tb) > tot:
            tb = b['kr']                      # 히라가나 칸은 옛 이름
        if blen(t) + 1 + blen(tb) > tot:
            bad.append((r['id'], r['kr'], t, '쌍 합계 %d' % tot)); continue
        new[r['id']] = t
        if tb != b['kr']:
            new[b['id']] = tb
    else:
        if blen(t) > int(r['budget']) or width(t) > max(width(r['kr']), 20):
            bad.append((r['id'], r['kr'], t, '칸 %s' % r['budget'])); continue
        new[r['id']] = t
for r in rows:                               # 꼬리만 족자인데 머리는 안 바뀐 경우
    if r['id'] in tail_of and '족자' in r['kr'] and r['id'] not in new and tail_of[r['id']]['id'] in new:
        pass

print('바꿈', len(new), '· 못 바꿈', len(bad))
for i, (a, b, c, d) in enumerate(bad):
    print('  그대로', a, d, '|', a and repr(b)[:60], '→', repr(c)[:60])
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
