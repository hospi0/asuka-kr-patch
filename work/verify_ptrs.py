# -*- coding: utf-8 -*-
"""빌드 결과(미리보기)에서 분류 목록 «거리» 표와 아이템 ②(설명 창 머리) 포인터가 가리키는 글을 한글로 보여 준다"""
import sys, struct, io, contextlib, os
sys.path.insert(0, 'tools'); sys.stdout.reconfigure(encoding='utf-8')
import build_all as B
f = io.StringIO()
with contextlib.redirect_stdout(f):
    font, cm, out = B.build(write=False)
print([l for l in f.getvalue().split('\n') if '예산초과' in l or '계획 밖' in l or '문제' in l])
src = open('work/iso/SSCR.BIN', 'rb').read(); d = out['SSCR.BIN']
dec = {font.chars[i].encode('cp932'): ch for ch, i in cm.map.items()}
def show(b):
    o = ''; i = 0
    while i < len(b):
        if b[i:i + 2] in dec: o += dec[b[i:i + 2]]; i += 2
        elif b[i] < 0x80: o += chr(b[i]); i += 1
        else: o += '?'; i += 2
    return o
print('분류:', ' / '.join(show(d[q + struct.unpack_from('<H', d, q)[0]:d.index(0, q + struct.unpack_from('<H', d, q)[0])]) for q in range(0x5D9E7, 0x5DA05, 2)))
rows = B.read_rows()['SSCR.BIN']; bad = n = 0
for k in range(len(rows) - 2):
    a, b, nx = rows[k], rows[k + 1], rows[k + 2]
    if B.pair_head(a, b) and int(nx['offset'], 16) - int(b['offset'], 16) - int(b['budget']) >= 31:
        ko, vo = int(a['offset'], 16), int(b['offset'], 16)
        fl = [q for q in range(ko - 64, ko) if struct.unpack_from('<H', src, q)[0] == vo - q]
        if not fl: print('필드없음', a['id']); continue
        t = fl[-1] + struct.unpack_from('<H', d, fl[-1])[0]; head = show(d[t:d.index(0, t)]).rstrip()
        name = show(d[ko:d.index(0, ko)]).rstrip(); n += 1
        want = name if b['kr'] == '=' else b['kr'].strip()
        if b['kr'] and not (head == want or (b['kr'] == '=' and name.endswith(head))):
            bad += 1; print('X', a['id'], name, '| 머리', head, '| 기대', want)
print('쌍', n, '틀림', bad)
print('백지 목록:', ' / '.join(show(d[q + struct.unpack_from('<H', d, q)[0]:d.index(0, q + struct.unpack_from('<H', d, q)[0])]).rstrip() for q in range(0x674E4, 0x6752C, 2)))
