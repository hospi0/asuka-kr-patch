# -*- coding: utf-8 -*-
"""조사 자동 선택 + 이름 끝 공백 건너뛰기 — 1NOSDC.BIN(SH-4, 리틀 엔디언) 코드 패치 (2026-10-09)

★끼어드는 자리: 표준 C 라이브러리 printf 의 %s 처리(파일 0x0FB684~)가 `JSR strlen` 하는데,
  그 함수 주소가 리터럴 0x0FB6F4(= 0x8C101774)에 있다. 이 4바이트만 우리 함수 주소로 바꾼다.
  (같은 값 리터럴은 다른 곳에도 많지만 이 자리 하나만 바꾼다 → %s 출력에만 걸린다)

우리 함수(파일 0x10D000, 가나→한자 변환 사전 안의 0 구간 11 KB — 그 구간을 가리키는 주소 0개):
  ① 원래 strlen → 끝의 반각 공백(0x20)을 길이에서 뺀다
     = 이름 칸 채움 공백 때문에 «주먹밥 변화 에»처럼 뜨던 빈칸이 사라진다(이름 1,107개 공통).
  ② 문자열 마지막 글자의 받침 여부 — 2바이트면 빌드 때 만든 비트표(SJIS 코드별, 한글 음절에 배정한 칸),
     ASCII 숫자면 0·1·3·6·7·8 = 받침 있음(영·일·삼·육·칠·팔). 그 밖의 1바이트 글자면 조사를 안 건드린다.
  ③ 서식 문자열에서 %s 바로 뒤 2바이트(호출자 R12 = 's' 자리, +1·+2)가 조사 짝 중 하나이고
     그 다음 바이트가 0x80 미만(공백·끝·영숫자) 또는 0x81(전각 부호 줄)일 때만 받침에 맞는 쪽으로 고쳐 쓴다.
     → «%s이스»·«%s이구려» 처럼 «이»로 시작하는 서술 표현은 안 건드린다. 서식은 RAM 이라 쓸 수 있다.
  짝: 은/는 · 을/를 · 이/가 · 과/와  (으로/로는 길이가 달라 제자리에서 못 바꿔 뺌)
"""
import struct

LOAD = 0x8C010000
HOOK_LIT = 0x0FB6F4          # printf %s 의 strlen 리터럴
STRLEN = 0x8C101774
BASE = 0x10D000              # 우리 코드·표
PAIRS = [('은', '는'), ('을', '를'), ('이', '가'), ('과', '와')]


class Asm:
    def __init__(self, base):
        self.base = base; self.code = []; self.labels = {}; self.fix = []; self.lits = []

    def pc(self):
        return self.base + 2 * len(self.code)

    def L(self, name):
        self.labels[name] = self.pc()

    def w(self, v):
        self.code.append(v & 0xFFFF)

    def br(self, op, label):          # op: 'bt' 'bf' 'bra'
        self.fix.append((len(self.code), op, label)); self.code.append(0)

    def ldl(self, rn, value):         # mov.l @(disp,pc),Rn — 리터럴은 끝 풀에
        self.fix.append((len(self.code), 'lit', (rn, value))); self.code.append(0)

    def build(self):
        # 리터럴 풀(4 정렬)
        if len(self.code) % 2:
            self.code.append(0x0009)
        pool = self.base + 2 * len(self.code)
        litv = []
        for _, op, a in self.fix:
            if op == 'lit' and a[1] not in litv:
                litv.append(a[1])
        lit_addr = {v: pool + 4 * k for k, v in enumerate(litv)}
        for i, op, a in self.fix:
            pc = self.base + 2 * i
            if op == 'lit':
                rn, v = a; disp = (lit_addr[v] - ((pc & ~3) + 4)) // 4
                assert 0 <= disp < 256 and (lit_addr[v] - ((pc & ~3) + 4)) % 4 == 0, ('lit', hex(pc))
                self.code[i] = 0xD000 | (rn << 8) | disp
            else:
                t = self.labels[a]; d = (t - (pc + 4)) // 2
                if op == 'bra':
                    assert -2048 <= d < 2048; self.code[i] = 0xA000 | (d & 0xFFF)
                else:
                    assert -128 <= d < 128, (op, a, d)
                    self.code[i] = (0x8900 if op == 'bt' else 0x8B00) | (d & 0xFF)
        out = b''.join(struct.pack('<H', c) for c in self.code)
        out += b''.join(struct.pack('<I', v) for v in litv)
        return out


def assemble(tab_addr, pair_addr):
    a = Asm(LOAD + BASE)
    W = a.w
    W(0x4F22)            # sts.l pr,@-r15
    W(0x2F86)            # mov.l r8,@-r15
    W(0x2F96)            # mov.l r9,@-r15
    W(0x6843)            # mov r4,r8            ; r8 = 문자열
    a.ldl(0, STRLEN)     # mov.l strlen,r0
    W(0x400B)            # jsr @r0
    W(0x0009)            # nop
    W(0x6903)            # mov r0,r9            ; r9 = 길이
    a.L('trim')
    W(0x2998)            # tst r9,r9
    a.br('bt', 'scan')   # 빈 문자열 — r5=0 으로 끝까지 가서 «조사 안 건드림»
    W(0x6183)            # mov r8,r1
    W(0x319C)            # add r9,r1
    W(0x71FF)            # add #-1,r1
    W(0x6210)            # mov.b @r1,r2
    W(0xE320)            # mov #0x20,r3
    W(0x3320)            # cmp/eq r2,r3
    a.br('bf', 'scan')
    a.br('bra', 'trim')
    W(0x79FF)            # (지연) add #-1,r9
    # --- 마지막 글자 코드 → r5 ---
    a.L('scan')
    # ★괄호 안은 건너뛴다(2026-10-09 실기 «보존항아리[4]을») — 괄호 «바로 앞» 글자로 받침을 정한다.
    #   여는 [ ( 【 ［ （ 를 만나면 r4 += 1, 닫는 ] ) 】 ］ ） 면 r4 -= 1, r4 == 0 일 때만 r5 를 갱신.
    W(0x6183)            # mov r8,r1            ; r1 = 커서
    W(0x6683)            # mov r8,r6
    W(0x369C)            # add r9,r6            ; r6 = 끝
    W(0xE500)            # mov #0,r5
    W(0xE400)            # mov #0,r4            ; r4 = 괄호 깊이
    a.L('sloop')
    W(0x3162)            # cmp/hs r6,r1         ; r1 >= r6 ?
    a.br('bt', 'decide')
    W(0x6214)            # mov.b @r1+,r2
    W(0x622C)            # extu.b r2,r2         ; r2 = 글자 코드
    W(0x6023)            # mov r2,r0
    W(0xCA20)            # xor #0x20,r0         ; 선행 바이트면 0xA1‥0xDC
    W(0x7080)            # add #-128,r0
    W(0x70DF)            # add #-33,r0          ; r0 -= 0xA1
    W(0xE33C)            # mov #0x3C,r3
    W(0x3032)            # cmp/hs r3,r0         ; 1바이트?
    a.br('bt', 'one')
    W(0x6014)            # mov.b @r1+,r0
    W(0x600C)            # extu.b r0,r0
    W(0x4218)            # shll8 r2
    W(0x220B)            # or r0,r2
    a.L('one')
    for c in (0x5B, 0x28):                       # 여는 괄호(1바이트)
        W(0xE300 | c); W(0x3320); a.br('bt', 'opn')      # mov #c,r3 · cmp/eq r2,r3
    for c in (0x8179, 0x816D, 0x8169):           # 【 ［ （
        a.ldl(3, c); W(0x3320); a.br('bt', 'opn')
    for c in (0x5D, 0x29):                       # 닫는 괄호
        W(0xE300 | c); W(0x3320); a.br('bt', 'cls')
    for c in (0x817A, 0x816E, 0x816A):           # 】 ］ ）
        a.ldl(3, c); W(0x3320); a.br('bt', 'cls')
    W(0x2448)            # tst r4,r4
    a.br('bf', 'sloop')  # 괄호 안 — 건너뜀
    a.br('bra', 'sloop')
    W(0x6523)            # (지연) mov r2,r5     ; 마지막 글자 후보
    a.L('opn')
    a.br('bra', 'sloop')
    W(0x7401)            # (지연) add #1,r4
    a.L('cls')
    W(0x2448)            # tst r4,r4
    a.br('bt', 'sloop')  # 짝 없는 닫는 괄호 — 무시
    a.br('bra', 'sloop')
    W(0x74FF)            # (지연) add #-1,r4
    # --- 받침 r7 ---
    a.L('decide')
    W(0x6253)            # mov r5,r2
    W(0x4219)            # shlr8 r2             ; r2 = 상위 바이트
    W(0x2228)            # tst r2,r2
    a.br('bf', 'two')
    W(0x6053)            # mov r5,r0
    W(0x70D0)            # add #-0x30,r0
    W(0xE30A)            # mov #10,r3
    W(0x3032)            # cmp/hs r3,r0
    a.br('bt', 'out')    # 숫자 아니면 조사 안 건드림
    W(0x630B)            # neg r0,r3
    a.ldl(2, 0x1CB)      # 받침 있는 숫자 0·1·3·6·7·8
    W(0x423D)            # shld r3,r2           ; r2 >>= 숫자
    W(0x6023)            # mov r2,r0
    W(0xC901)            # and #1,r0
    a.br('bra', 'josa')
    W(0x6703)            # (지연) mov r0,r7
    a.L('two')
    W(0x6053)            # mov r5,r0
    W(0x600C)            # extu.b r0,r0         ; 하위
    W(0x70C0)            # add #-0x40,r0
    a.ldl(3, 192)
    W(0x3032)            # cmp/hs r3,r0
    a.br('bt', 'out')
    W(0x6603)            # mov r0,r6            ; 열
    W(0x6023)            # mov r2,r0            ; 상위
    a.ldl(3, 0xA0)
    W(0x3032)            # cmp/hs r3,r0
    a.br('bt', 'hib')
    a.ldl(3, 0x81)
    a.br('bra', 'rowok')
    W(0x3038)            # (지연) sub r3,r0
    a.L('hib')
    a.ldl(3, 0xC1)
    W(0x3038)            # sub r3,r0
    a.L('rowok')
    a.ldl(3, 47)
    W(0x3032)            # cmp/hs r3,r0         ; 행 0‥46
    a.br('bt', 'out')
    a.ldl(3, 192)
    W(0x203E)            # mulu.w r3,r0
    W(0x001A)            # sts macl,r0
    W(0x306C)            # add r6,r0            ; 비트 번호
    W(0x6603)            # mov r0,r6
    W(0x4609)            # shlr2 r6
    W(0x4601)            # shlr r6              ; 바이트
    a.ldl(3, tab_addr)
    W(0x336C)            # add r6,r3
    W(0x6230)            # mov.b @r3,r2
    W(0x622C)            # extu.b r2,r2
    W(0xC907)            # and #7,r0
    W(0x600B)            # neg r0,r0
    W(0x420D)            # shld r0,r2
    W(0x6023)            # mov r2,r0
    W(0xC901)            # and #1,r0
    W(0x6703)            # mov r0,r7
    # --- 조사 ---
    a.L('josa')
    W(0x61C3)            # mov r12,r1
    W(0x7101)            # add #1,r1            ; %s 다음
    W(0x6210)            # mov.b @r1,r2
    W(0x622C)            # extu.b r2,r2
    W(0x4218)            # shll8 r2
    W(0x8411)            # mov.b @(1,r1),r0
    W(0x600C)            # extu.b r0,r0
    W(0x220B)            # or r0,r2             ; r2 = 조사 코드
    W(0x8412)            # mov.b @(2,r1),r0
    W(0x600C)            # extu.b r0,r0
    W(0xE37F)            # mov #0x7F,r3
    W(0x3036)            # cmp/hi r3,r0         ; 다음 바이트 > 0x7F ?
    a.br('bf', 'chk')
    a.ldl(3, 0x81)
    W(0x3030)            # cmp/eq r3,r0
    a.br('bf', 'out')
    a.L('chk')
    a.ldl(3, pair_addr)
    W(0xE600 | len(PAIRS))   # mov #짝 수,r6
    a.L('ploop')
    W(0x6435)            # mov.w @r3+,r4
    W(0x644D)            # extu.w r4,r4         ; 받침 있을 때
    W(0x6535)            # mov.w @r3+,r5
    W(0x655D)            # extu.w r5,r5         ; 받침 없을 때
    W(0x3240)            # cmp/eq r4,r2
    a.br('bt', 'hit')
    W(0x3250)            # cmp/eq r5,r2
    a.br('bt', 'hit')
    W(0x4610)            # dt r6
    a.br('bf', 'ploop')
    a.br('bra', 'out')
    W(0x0009)
    a.L('hit')
    W(0x2778)            # tst r7,r7
    a.br('bt', 'usev')
    W(0x6543)            # mov r4,r5
    a.L('usev')
    W(0x6053)            # mov r5,r0
    W(0x4019)            # shlr8 r0
    W(0x2100)            # mov.b r0,@r1
    W(0x6053)            # mov r5,r0
    W(0x8011)            # mov.b r0,@(1,r1)
    a.L('out')
    W(0x6093)            # mov r9,r0
    W(0x69F6)            # mov.l @r15+,r9
    W(0x68F6)            # mov.l @r15+,r8
    W(0x4F26)            # lds.l @r15+,pr
    W(0x000B)            # rts
    W(0x0009)            # nop
    return a.build()


def batchim_bitmap(cm):
    """비트 = ((상위−0x81 | 상위−0xC1) × 192 + (하위−0x40)) — 한글 음절에 배정한 칸 중 받침 있는 것"""
    bm = bytearray(47 * 192 // 8)
    for syl, idx in cm.map.items():
        if (ord(syl) - 0xAC00) % 28 == 0:
            continue
        b = cm.font.chars[idx].encode('cp932')
        hi, lo = b[0], b[1]; row = hi - 0x81 if hi <= 0x9F else hi - 0xC1; col = lo - 0x40
        if 0 <= row < 47 and 0 <= col < 192:
            k = row * 192 + col; bm[k >> 3] |= 1 << (k & 7)
    return bytes(bm)


def apply(buf, cm):
    """→ (패치된 bytes, [(시작, 끝)…] 바뀐 구간)"""
    b = bytearray(buf)
    pairs = b''
    for x, y in PAIRS:
        cx = cm.encode(x); cy = cm.encode(y)
        pairs += struct.pack('<HH', cx[0] << 8 | cx[1], cy[0] << 8 | cy[1])
    bm = batchim_bitmap(cm)
    code_len = len(assemble(1, 2))   # ⚠두 주소가 같으면 리터럴이 합쳐져 4 B 짧게 잰다 → 짝표가 리터럴을 덮었다(2026-10-09 실기 «+4을»)
    pair_off = (BASE + code_len + 3) & ~3; tab_off = pair_off + len(pairs)
    code = assemble(LOAD + tab_off, LOAD + pair_off)
    assert len(code) == code_len and BASE + len(code) <= pair_off, '코드 길이 %d ≠ 잰 길이 %d' % (len(code), code_len)
    end = tab_off + len(bm)
    assert not any(b[BASE:end]), '0x%X‥0x%X 가 0 이 아니다' % (BASE, end)
    b[BASE:BASE + len(code)] = code
    b[pair_off:pair_off + len(pairs)] = pairs
    b[tab_off:end] = bm
    assert struct.unpack_from('<I', b, HOOK_LIT)[0] == STRLEN, 'strlen 리터럴 자리 다름'
    struct.pack_into('<I', b, HOOK_LIT, LOAD + BASE)
    return bytes(b), [(BASE, end), (HOOK_LIT, HOOK_LIT + 4)]
