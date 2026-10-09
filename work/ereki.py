# -*- coding: utf-8 -*-
"""エレキ 표기 통일 → «에레키» (2026-10-09 사용자 «에레키와 엘렉도 에레키로 통일»)
   일렉·엘렉·엘레키·에레끼·일레키 → 에레키 («エレキープ»는 キープ 말장난이라 «에레킵»).
   칸 넘치면 그대로 두고 보고. tsv2 kr 열만. python work/ereki.py [--write]"""
import difflib, glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92); NL = BS + 'n'
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')
RX = re.compile('일렉|엘렉|엘레키|에레끼|일레키')
FIND = re.compile('일렉|엘렉|엘레키|에레끼|일레키|에레키박스|에레키 상자')
HAND = {'SCR00624': '게다가 에레키상자를 적에게 던지면\\n그 자리서 에레키로봇이 된다구~.\\n상황에 따라선 편리할지도 몰라~.',
        'SYS04358': '에레키상자는 적에 맞아도\\n안 사라진다! 아무튼\\n던지고 던지고 던져야지!'}


def blen(s):
    return sum(1 if ord(c) < 0x80 else 2 for c in ESC.sub('\x01', s))


def width(line):
    return len(ESC.sub('', line))


n = 0; bad = []
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 7 or not FIND.search(c[6]):
            continue
        new = c[6].replace('일렉킵', '에레킵') if 'エレキープ' in c[5] else c[6]
        new = re.sub('(?:일렉|엘렉|엘레키|에레끼|일레키|에레키) ?(?:박스|상자)', '에레키상자', new)   # エレキ箱 = 에레키상자
        new = RX.sub('에레키', new)
        new = HAND.get(c[0], new)
        ow = max(width(x) for x in c[6].split(NL)); nw = max(width(x) for x in new.split(NL))
        if blen(new) > int(c[3]) or nw > max(ow, 20):
            bad.append((c[0], c[3], blen(new), nw, c[6], new)); continue
        for t, a1, a2, b1, b2 in difflib.SequenceMatcher(None, c[6], new).get_opcodes():
            if t != 'equal':
                print(c[0], repr(c[6][max(0, a1 - 5):a2 + 4]), '→', repr(new[max(0, b1 - 5):b2 + 4]))
        c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행 · 넘쳐 그대로', len(bad))
for b in bad:
    print('  그대로', b[0], '칸', b[1], '필요', b[2], '폭', b[3], '|', repr(b[4]), '→', repr(b[5]))
