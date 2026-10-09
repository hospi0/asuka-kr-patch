# -*- coding: utf-8 -*-
"""にぎり 몬스터 계열 이름 통일(2026-10-09 사용자 «주먹밥 계열»):
   みならい=주먹밥견습생 · へんげ=주먹밥 변화 · 親方=주먹밥대장 · もとじめ=주먹밥 두목
   my files/tsv2 의 kr 열만 바꾼다(fix_tsv 는 돌리지 말 것 — 지금 tsv2 에 돌리면 도감 띄어쓰기를 지운다).
   python work/rename_nigiri.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92); NL = BS + 'n'
REP = [  # 긴 것 먼저
    ('니기리' + NL + '미나라이', '주먹밥' + NL + '견습생'),
    ('니기리미나라이', '주먹밥견습생'), ('니기리 견습생', '주먹밥견습생'), ('니기리견습생', '주먹밥견습생'),
    ('니기리헨게', '주먹밥 변화'), ('니기리 변화', '주먹밥 변화'),
    ('니기리오야카타', '주먹밥대장'), ('니기리대장', '주먹밥대장'),
    ('니기리 모토지메', '주먹밥 두목'), ('니기리모토지메', '주먹밥 두목'), ('니기리 두목', '주먹밥 두목'),
    ('주먹밥요괴', '주먹밥 변화'), ('주먹밥 요괴', '주먹밥 변화'),
]
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')


def blen(s):
    s = ESC.sub('\x01', s)
    return sum(1 if ord(c) < 0x80 else 2 for c in s)


def width(line):
    return len(ESC.sub('', line))


n = 0; bad = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or not c[6]:
            continue
        new = c[6]
        for a, b in REP:
            new = new.replace(a, b)
        # 받침 있는 새 이름(…생·…장·…목) 뒤 조사: 는→은 가→이 를→을 와→과 로→으로 (옛 이름 니기리미나라이·오야카타·모토지메는 받침 없음)
        if new != c[6]:
            new = re.sub('(주먹밥견습생|주먹밥대장|주먹밥 두목)(는|가|를|와|로)',
                         lambda m: m.group(1) + {'는': '은', '가': '이', '를': '을', '와': '과', '로': '으로'}[m.group(2)], new)
        if new == c[6]:
            continue
        bud = int(c[3]); ol = max(width(x) for x in c[6].split(NL)); nl = max(width(x) for x in new.split(NL))
        flag = ''
        if blen(new) > bud:
            flag += ' ⛔예산 %d>%d' % (blen(new), bud)
        if nl > max(ol, 20):
            flag += ' ⚠줄 폭 %d>%d' % (nl, max(ol, 20))
        bad += bool(flag)
        print(c[0], repr(c[6])[:60], '→', repr(new)[:60], flag)
        c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 · 문제', bad)
