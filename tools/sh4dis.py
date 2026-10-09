# -*- coding: utf-8 -*-
"""1NOSDC.BIN SH-4(리틀 엔디언) 역어셈블 — 테라 프로젝트 sh2_disasm(빅 엔디언)에 워드를 뒤집어 넣는다.
  FPU·SH-4 전용 명령은 «?» 로 나올 수 있다. 적재 주소 LOAD(기본 0x8C010000).
  python tools/sh4dis.py 파일오프셋(16진) [개수]"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOAD = 0x8C010000
EXE = os.path.join(ROOT, 'work', 'iso', '1NOSDC.BIN')
_src = open(r'C:\claude\project\terra-kr-patch\tools\sh2_disasm.py', encoding='utf-8').read().split("if __name__")[0]
_ns = {}; exec(_src, _ns)


def dis(off, n=80, g=None):
    g = g or open(EXE, 'rb').read()
    raw = g[off:off + n * 2]
    be = b''.join(raw[i + 1:i + 2] + raw[i:i + 1] for i in range(0, len(raw) - 1, 2))
    out = []
    for a, w, t in _ns['disasm_sh2'](be, LOAD + off, n):
        out.append('%06X %08X  %04X  %s' % (a - LOAD, a, w, t))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(dis(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 80)))
