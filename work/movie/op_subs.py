# -*- coding: utf-8 -*-
"""OP.SFD 앞부분 자막 굽기 (2026-10-09 사용자 «초반에 나오는 자막만 밑에 달아줘»)
   1) 원본 영상 앞 N 프레임 + 자막(drawtext) → ffmpeg mpeg1video(원본과 같은 GOP 18·B 2·양자화 표) → op_head.m1v
   2) 원본 ES 에 GOP 0‥SPLICE-1 자리를 바꿔 끼움(원래 바이트 길이까지 0 채움) → GOP SPLICE 부터 원본 그대로
   3) SFD 패킷 자리에 그대로 다시 나눠 넣고, 앞부분 패킷의 PTS/DTS 를 새 그림 위치에 맞게 고침 → OP_kr.SFD
   python op_subs.py [비트레이트k]"""
import os, struct, subprocess, sys, bisect
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfd
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
SPLICE = 49                     # GOP 49 = 표시 프레임 880(29.33초)부터 원본
SUBS = [(2.55, 5.35, '수많은 땅을 여행하며'),
        (5.50, 8.05, '많은 사람들과 어울리고'),
        (8.25, 10.70, '역경에 맞서'),
        (10.85, 13.35, '자신의 지혜와 용기를 시험한다'),
        (13.55, 16.60, '여행의 신 크론의 인도를 받은 그들을'),
        (16.85, 19.65, '사람들은 풍래인이라 불렀다.'),
        (21.05, 24.00, '그리고 이것은 풍래 수행 여행 도중,'),
        (24.20, 28.60, '두 나라를 찾은 한 여검사의 이야기……')]
RATE = sys.argv[1] if len(sys.argv) > 1 else '4'
EARLY = int(sys.argv[2]) if len(sys.argv) > 2 else 32768


def gops(es):
    out = []; k = 0
    while True:
        k = es.find(b'\x00\x00\x01\xb8', k)
        if k < 0:
            return out
        out.append(k); k += 4


def pictures(es):
    out = []; k = 0
    while True:
        k = es.find(b'\x00\x00\x01\x00', k)
        if k < 0:
            return out
        v = struct.unpack_from('>H', es, k + 4)[0]
        out.append((k, (v >> 3) & 7, v >> 6)); k += 4


src = open('OP.SFD', 'rb').read()
P = sfd.packets(src)
es = b''.join(src[p:e] for _, s, _, p, e in P if s == 0xE0)
G = gops(es)
cut = G[SPLICE]
nfr = 16 + 18 * (SPLICE - 1)            # 바꿀 표시 프레임 수(880)
# --- 1) 인코딩 ---------------------------------------------------------
lines = []
for a, b, t in SUBS:
    t = t.replace("'", "\u2019").replace(':', '\\:').replace(',', '\\,')
    lines.append("drawtext=fontfile=mjb.ttf:text='%s':fontsize=21:fontcolor=0x101010:borderw=2:bordercolor=white:"
                 "x=(w-text_w)/2:y=h-46:enable='between(t,%.2f,%.2f)'" % (t, a, b))
open('op_subs_filter.txt', 'w', encoding='utf-8').write(',\n'.join(lines))
mat = ','.join(['8'] + ['32'] * 63)
cmd = [FF, '-v', 'error', '-y', '-i', 'OP.SFD', '-an', '-frames:v', str(nfr + 20), '-/filter:v', 'op_subs_filter.txt',
       '-c:v', 'mpeg1video', '-g', '18', '-bf', '2', '-sc_threshold', '1000000000', '-intra_matrix', mat,
       '-q:v', RATE, '-f', 'mpeg1video', 'op_head.m1v']          # 양자화 고정(원본도 가변 비트레이트)
subprocess.run(cmd, check=True)
he = open('op_head.m1v', 'rb').read()
HG = gops(he)
# 그림 구조 대조(GOP 0‥SPLICE-1)
op = [(t, r) for _, t, r in pictures(es[:cut])]
np_ = [(t, r) for k, t, r in pictures(he) if k < HG[SPLICE]]
assert op == np_, '그림 구조가 원본과 다르다 %d/%d' % (len(op), len(np_))
body = he[HG[0]:HG[SPLICE]]
room = cut - G[0]
print('그림 %d장 구조 같음 · 새 %d B / 자리 %d B (%.0f%%)' % (len(op), len(body), room, 100 * len(body) / room))
assert len(body) <= room, '자리 넘침 — 비트레이트를 낮출 것'
# 그림마다 «원래 시작 위치»에 맞춰 0 을 앞에 채운다(데이터가 너무 일찍 들어가 버퍼가 넘치지 않게)
def units(e, lo, hi):
    pk = [k for k, _, _ in pictures(e) if lo <= k < hi]
    gs = set(gops(e))
    return [k - 8 if (k - 8) in gs else k for k in pk]
ou = units(es, G[0], cut); nu = units(he, HG[0], HG[SPLICE])
assert len(ou) == len(nu)
nu.append(HG[SPLICE])
vstarts = []; _o = 0
for _, sid, _, p, e in P:
    if sid == 0xE0:
        vstarts.append(_o); _o += e - p
def pk_start(o):
    return vstarts[bisect.bisect_right(vstarts, o) - 1]
buf = bytearray(es[:G[0]]); late = 0
for j in range(len(ou)):
    tgt = max(G[0], pk_start(ou[j]) - (EARLY if j >= len(ou) - 18 else 0))  # 그 그림이 원래 시작하던 «패킷의 첫 바이트»(타임스탬프 칸 유지) — EARLY 는 추가 여유
    if len(buf) < tgt:
        buf += bytes(tgt - len(buf))
    late = max(late, len(buf) - ou[j])
    buf += he[nu[j]:nu[j + 1]]
print('끝 위치 %d / 자리 %d · 가장 늦음 %d' % (len(buf), cut, late)); assert len(buf) <= cut
print('가장 늦은 그림 %d B 늦음' % late)
new_es = bytes(buf) + bytes(cut - len(buf)) + es[cut:]
assert len(new_es) == len(es)
# --- 3) 패킷에 다시 나눠 넣기 + 타임스탬프 -------------------------------
pics = pictures(new_es[:cut])
starts = [k for k, _, _ in pics]
gstart = []                              # 코딩 순서 j 의 GOP 첫 그림 번호
gi = 0; gpos = gops(new_es[:cut]); first = 0
for j, (k, t, r) in enumerate(pics):
    while gi < len(gpos) and gpos[gi] < k:
        first = j; gi += 1
    gstart.append(first)


def put_ts(b, o, mark, v):
    b[o] = mark | ((v >> 29) & 0xE) | 1
    b[o + 1] = (v >> 22) & 0xFF; b[o + 2] = ((v >> 14) & 0xFE) | 1
    b[o + 3] = (v >> 7) & 0xFF; b[o + 4] = ((v << 1) & 0xFE) | 1


out = bytearray(src); pos = 0; fixed = stuffed = 0
for i, sid, st, p, en in P:
    if sid != 0xE0:
        continue
    ln = en - p
    out[p:en] = new_es[pos:pos + ln]
    if pos < cut:
        q = st
        while out[q] == 0xFF:
            q += 1
        if out[q] & 0xC0 == 0x40:
            q += 2
        kind = out[q] & 0xF0
        if kind in (0x20, 0x30):
            j = bisect.bisect_left(starts, pos)
            if j < len(pics) and starts[j] < pos + ln:
                _, t, r = pics[j]
                pts = (gstart[j] + r) * 3000; dts = j * 3000
                if kind == 0x30:
                    put_ts(out, q, 0x30, pts); put_ts(out, q + 5, 0x10, dts if t != 3 else pts)
                else:
                    put_ts(out, q, 0x20, pts)
                fixed += 1
            else:                                  # 이 패킷에서 시작하는 그림 없음 → 타임스탬프를 채움 바이트로
                n = 5 if kind == 0x20 else 10      # 머리를 «채움 FF… → STD(있으면) → 0F» 순서로(채움은 STD 앞이어야 한다)
                std = bytes(out[q - 2:q]) if q - 2 >= st and out[q - 2] & 0xC0 == 0x40 else b''
                hl = q + n - st
                out[st:q + n] = b'\xff' * (hl - len(std) - 1) + std + b'\x0f'; stuffed += 1
    pos += ln
assert pos == len(new_es)
open('OP_kr.SFD', 'wb').write(out)
print('타임스탬프 고침 %d · 지움 %d · OP_kr.SFD %d B (원본과 같음 %s)' % (fixed, stuffed, len(out), len(out) == len(src)))
