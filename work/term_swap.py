# -*- coding: utf-8 -*-
"""단지→항아리 · 봉→지팡이 (2026-10-09 사용자 «아이템 단지도 마찬가지 전부 항아리로 바꿔줘 봉은 지팡이로»)
   원문에 그 물건(壺/つぼ · 杖/つえ)이 있는 줄에서만, 낱말 경계로만 바꾼다(봉인 보호).
   받침 바뀌면(봉→지팡이) 뒤 조사도 고친다. 아이템 이름 쌍은 [한자][0][히라가나] 합계 바이트로(빌더가 묶음),
   히라가나 칸이 모자라면 그쪽은 띄어쓰기·«의»를 뺀 꼴. 그 밖의 행은 자기 칸 안에서, 줄 폭 넘치면 줄을 다시 나눔.
   python work/term_swap.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_all as B
BS = chr(92); N = BS + 'n'
CTRL = '[' + chr(0) + '-' + chr(31) + ']'
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')|' + CTRL)
HAS_CTRL = re.compile(CTRL + '|' + re.escape(BS) + 'x')
RULES = [(('壺', 'つぼ', 'ツボ'), r'단지', '항아리'),
         (('杖', 'つえ'), r'(?<![가-힣])봉(?![인투사쇄착건급지합우래])|(?<=[가-힣])봉(?=$|[^가-힣]|[을이은과으엔에의도만뿐까])', '지팡이')]
JOSA = [('으로', '로'), ('이나', '나'), ('이라', '라'), ('이다', '다'), ('이야', '야'), ('이랑', '랑'),
        ('을', '를'), ('은', '는'), ('과', '와'), ('이', '가')]


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub(chr(1), s))


def width(s):
    return max(len(ESC.sub('', x)) for x in s.split(N))


def bat(ch):
    return (ord(ch) - 0xAC00) % 28 != 0


def swap(t, jp):
    for keys, rx, new in RULES:
        if not any(k in jp for k in keys):
            continue
        out = ''; i = 0
        for m in re.finditer(rx, t):
            if m.start() < i:
                continue
            out += t[i:m.start()] + new; i = m.end()
            ob, nb = bat(m.group(0)[-1]), bat(new[-1])
            if ob != nb:
                for a, b in JOSA:
                    have, want = (a, b) if ob else (b, a)
                    nxt = t[i + len(have):i + len(have) + 1]
                    if t.startswith(have, i) and (have not in ('이', '가') or nxt == '' or not ('가' <= nxt <= '힣')):
                        out += want; i += len(have); break
        t = out + t[i:]
    return t


def reflow(t, W, nl):
    """줄 다시 나누기 — 제어 코드 없는 행만, 줄 수는 원래 이하, 끝 줄바꿈 유지"""
    if HAS_CTRL.search(t):
        return t
    end = N if t.endswith(N) else ''
    words = ' '.join(x.strip() for x in t[:len(t) - len(end)].split(N)).split(' ')
    lines = ['']
    for w in words:
        if not w:
            continue
        cand = (lines[-1] + ' ' + w) if lines[-1] else w
        if len(cand) <= W:
            lines[-1] = cand
        else:
            lines.append(w)
    out = N.join(lines) + end
    return out if out.count(N) <= nl and max(len(x) for x in lines) <= W else t


per = B.read_rows()
srows = per['SSCR.BIN']
pair = {}
for k in range(len(srows) - 2):
    a, b, n = srows[k], srows[k + 1], srows[k + 2]
    if B.pair_head(a, b) and int(n['offset'], 16) - int(b['offset'], 16) - int(b['budget']) >= 31:
        pair[a['id']] = b
tails = {b['id'] for b in pair.values()}
new = {}; bad = []
for rows in per.values():
    for r in rows:
        if r['id'] in tails or not r['kr']:
            continue
        t = swap(r['kr'], r['jp'])
        if r['id'] in pair:
            b = pair[r['id']]; tb = swap(b['kr'], r['jp'])
            if t == r['kr'] and tb == b['kr']:
                continue
            tot = int(r['budget']) + 1 + int(b['budget'])
            if blen(t) + 1 <= tot:                    # ② 칸은 «=» — 빌더가 설명 창 머리를 ① 이름으로 돌린다
                new[r['id']] = t; new[b['id']] = '='; continue
            base = re.sub('(의 ?)?(항아리|지팡이|두루마리)$', '', tb).strip()
            cands = [(t, tb), (t, tb.replace(' ', '')), (t, re.sub('의 ?(?=(항아리|지팡이)$)', '', tb).replace(' ', '')),
                     (t, base.replace(' ', '')), (t.replace(' ', ''), base.replace(' ', '')),
                     (re.sub('의 ?(?=(항아리|지팡이)$)', '', t).replace(' ', ''), base.replace(' ', ''))]
            for ct, cb in cands:
                if cb and blen(ct) + 1 + blen(cb) <= tot:
                    t, tb = ct, cb; break
            if blen(t) + 1 + blen(tb) > tot:
                bad.append((r['id'], r['budget'], r['kr'], t)); continue
            new[r['id']] = t; new[b['id']] = tb
        else:
            if t == r['kr']:
                continue
            W = max(width(r['kr']), 20)
            if blen(t) <= int(r['budget']) and width(t) > W:
                t = reflow(t, W, r['kr'].count(N))
            if blen(t) > int(r['budget']) or width(t) > W:
                bad.append((r['id'], r['budget'], r['kr'], t)); continue
            new[r['id']] = t
cnt = 0
for rows in per.values():
    for r in rows:
        if r['id'] in new and new[r['id']] != r['kr']:
            cnt += 1
            print(r['id'], '|', r['kr'].replace(N, ' / ')[:80], '→', new[r['id']].replace(N, ' / ')[:80])
print('바꿈', cnt, '· 못 바꿈', len(bad))
for x in bad:
    print('  그대로', x[0], '칸', x[1], '|', x[2].replace(N, ' / ')[:80], '→', x[3].replace(N, ' / ')[:80])
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
