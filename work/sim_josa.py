# -*- coding: utf-8 -*-
"""patch_josa 함수만 돌려 보는 SH-4 부분 에뮬레이터 (2026-10-09 조사 미작동 원인 찾기)
   RAM = work/fly_ram2.bin (8C000000‥), strlen(0x8C101774) 은 파이썬으로 대신."""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
ram = bytearray(open('work/fly_ram2.bin', 'rb').read())
B = 0x8C000000
def rb(a): return ram[(a & 0x1FFFFFFF) - 0x0C000000]
def wb(a, v): ram[(a & 0x1FFFFFFF) - 0x0C000000] = v & 0xFF
def rw(a): return rb(a) | rb(a + 1) << 8
def rl(a): return rw(a) | rw(a + 2) << 16
def wl(a, v):
    for i in range(4): wb(a + i, v >> (8 * i))
def sx8(v): v &= 0xFF; return v - 256 if v & 0x80 else v
def sx16(v): v &= 0xFFFF; return v - 65536 if v & 0x8000 else v
M = 0xFFFFFFFF


def run(s_bytes, fmt_bytes):
    S = 0x8C700000; F = 0x8C700100
    for i, c in enumerate(s_bytes + b'\0'): wb(S + i, c)
    for i, c in enumerate(fmt_bytes + b'\0'): wb(F + i, c)
    r = [0] * 16; r[4] = S; r[12] = F + 1; r[15] = 0x8C7F0000
    T = 0; pr = 0xDEAD0000; macl = 0
    pc = 0x8C11D000; delay = None; steps = 0
    while True:
        steps += 1; assert steps < 100000
        if pc == 0x8C101774:            # strlen
            n = 0
            while rb(r[4] + n): n += 1
            r[0] = n; pc = pr; continue
        if pc == 0xDEAD0000:
            return r[0], bytes(rb(F + i) for i in range(len(fmt_bytes)))
        op = rw(pc); n = (op >> 8) & 15; m = (op >> 4) & 15; npc = pc + 2; d = None
        h = op >> 12
        if op == 0x0009: pass
        elif op == 0x000B: d = pr
        elif op & 0xF0FF == 0x4012: r[n] = (r[n] - 4) & M; wl(r[n], macl)
        elif op & 0xF0FF == 0x4016: macl = rl(r[n]); r[n] = (r[n] + 4) & M
        elif op & 0xFF00 == 0xC800: T = int((r[0] & op & 0xFF) == 0)
        elif op & 0xF0FF == 0x4022: r[n] = (r[n] - 4) & M; wl(r[n], pr)
        elif op & 0xF0FF == 0x4026: pr = rl(r[n]); r[n] = (r[n] + 4) & M
        elif op & 0xF0FF == 0x400B: d = r[n]; pr = pc + 4
        elif op & 0xF00F == 0x2006: r[n] = (r[n] - 4) & M; wl(r[n], r[m])
        elif op & 0xF00F == 0x6006: r[n] = rl(r[m]); r[m] = (r[m] + 4) & M if n != m else r[n]
        elif op & 0xF00F == 0x6003: r[n] = r[m]
        elif h == 0xD: r[n] = rl(((pc + 4) & ~3) + (op & 0xFF) * 4)
        elif h == 0xE: r[n] = sx8(op) & M
        elif h == 0x7: r[n] = (r[n] + sx8(op)) & M
        elif op & 0xF00F == 0x2008: T = int(r[n] & r[m] == 0)
        elif op & 0xF00F == 0x300C: r[n] = (r[n] + r[m]) & M
        elif op & 0xF00F == 0x3008: r[n] = (r[n] - r[m]) & M
        elif op & 0xF00F == 0x6000: r[n] = sx8(rb(r[m])) & M
        elif op & 0xF00F == 0x6004: r[n] = sx8(rb(r[m])) & M; r[m] = (r[m] + 1) & M if n != m else r[n]
        elif op & 0xF00F == 0x6005: r[n] = sx16(rw(r[m])) & M; r[m] = (r[m] + 2) & M if n != m else r[n]
        elif op & 0xF00F == 0x600C: r[n] = r[m] & 0xFF
        elif op & 0xF00F == 0x600D: r[n] = r[m] & 0xFFFF
        elif op & 0xF00F == 0x600B: r[n] = (-r[m]) & M
        elif op & 0xF00F == 0x3000: T = int(r[n] == r[m])
        elif op & 0xF00F == 0x3002: T = int(r[n] >= r[m])
        elif op & 0xF00F == 0x3006: T = int(r[n] > r[m])
        elif op & 0xFF00 == 0xCA00: r[0] ^= op & 0xFF
        elif op & 0xFF00 == 0xC900: r[0] &= op & 0xFF
        elif op & 0xF0FF == 0x4018: r[n] = (r[n] << 8) & M
        elif op & 0xF0FF == 0x4019: r[n] >>= 8
        elif op & 0xF0FF == 0x4009: r[n] >>= 2
        elif op & 0xF0FF == 0x4001: T = r[n] & 1; r[n] >>= 1
        elif op & 0xF0FF == 0x4010: r[n] = (r[n] - 1) & M; T = int(r[n] == 0)
        elif op & 0xF00F == 0x200B: r[n] |= r[m]
        elif op & 0xF00F == 0x200E: macl = (r[n] & 0xFFFF) * (r[m] & 0xFFFF) & M
        elif op & 0xF0FF == 0x001A: r[n] = macl
        elif op & 0xF00F == 0x400D:
            s = r[m] if r[m] < 0x80000000 else r[m] - (1 << 32)
            r[n] = (r[n] << (s & 31)) & M if s >= 0 else (0 if (s & 31) == 0 else r[n] >> (32 - (s & 31)))
        elif op & 0xFF00 == 0x8400: r[0] = sx8(rb(r[m] + (op & 15))) & M
        elif op & 0xFF00 == 0x8000: wb(r[m] + (op & 15), r[0])
        elif op & 0xF00F == 0x2000: wb(r[n], r[m])
        elif op & 0xFF00 == 0x8900:
            if T: npc = pc + 4 + sx8(op) * 2
        elif op & 0xFF00 == 0x8B00:
            if not T: npc = pc + 4 + sx8(op) * 2
        elif h == 0xA:
            dd = op & 0xFFF; dd = dd - 4096 if dd & 0x800 else dd; d = pc + 4 + dd * 2
        else:
            raise SystemExit('모르는 명령 %04X @ %08X' % (op, pc))
        if delay is not None:
            pc, delay = delay, None; continue
        if d is not None:
            delay = d; pc = npc; continue
        pc = npc


def enc(s):
    import json
    cm = json.load(open('data/charmap_build.json', encoding='utf-8'))
    raise SystemExit


if __name__ == '__main__':
    name = bytes.fromhex('8f6b8d5f9394934b') + b'      '
    fmt = bytes.fromhex('257392e02093b992b88bbd2e202020')
    n, f = run(name, fmt)
    print('길이', n, '서식', f.hex(' '))
    n, f = run(bytes.fromhex('8f6b8d5f9394') + b'  ', fmt)
    print('길이', n, '서식', f.hex(' '))
    n, f = run(b'abc+4', fmt)
    print('길이', n, '서식', f.hex(' '))
