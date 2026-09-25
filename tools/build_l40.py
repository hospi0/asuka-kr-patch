# -*- coding: utf-8 -*-
"""DATABG 멤버(.l40)를 직접 조립한다 — 재빌드 도구가 CA_16/CB_16 을 안 건드려서.

실측한 멤버 구조 (CA_16.l40 을 lzx -d 로 푼 결과 113,408 B):
    [청크A 32B 헤더][PVR 페이로드][32의 배수로 0 패딩]
    [청크B 32B 헤더][PVR 페이로드][패딩]
  헤더 = u32 size(패딩 포함 청크 전체) | u32 fmt | u16 w | u16 h | u32 0 | char[16] tag
  ★마지막 청크의 size 는 0 (체인 종단) — DATASZU 와 같은 규약.
  pypvr 가 낸 .PVR 은 앞 16B 가 컨테이너 헤더(PVRT|size|fmt|w|h)라 그건 떼고 넣는다.
"""
import os, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, 'work', 'databg', 'DATABG_EXT')
LZX = os.path.join(ROOT, 'work', 'databg', 'lzx.exe')
PYPVR = r"C:\claude\utils\dreamcast\PyPVR\pypvr.exe"


def encode_pvr(png, args):
    d = os.path.dirname(png)
    subprocess.run([PYPVR, os.path.basename(png)] + args + ['-o', '.'],
                   cwd=d, check=True, capture_output=True)
    return os.path.splitext(png)[0] + '.PVR'


def chunk(tag, fmt, w, h, payload, last=False):
    body = payload + b'\x00' * ((-len(payload)) % 32)
    total = 32 + len(body)
    hdr = struct.pack('<IIHHI', 0 if last else total, fmt, w, h, 0)
    hdr += tag.encode('ascii').ljust(16, b'\x00')
    return hdr + body, total


def build(name, parts, args=('-vq', '-mm', '-565')):
    """parts = [(tag, png경로, fmt, w, h), ...]  -> .l40 을 새로 쓴다."""
    d = os.path.join(EXT, name, 'PVR')
    blob = b''
    for i, (tag, png, fmt, w, h) in enumerate(parts):
        pvr = encode_pvr(os.path.join(d, png), list(args))
        raw = open(pvr, 'rb').read()
        assert raw[:4] == b'PVRT', pvr
        c, _ = chunk(tag, fmt, w, h, raw[16:], last=(i == len(parts) - 1))
        blob += c
    tmp = os.path.join(d, '_new.bin')
    open(tmp, 'wb').write(blob)
    subprocess.run([LZX, '-ewl', '_new.bin'], cwd=d, check=True, capture_output=True)
    out = os.path.join(d, name + '.l40')
    old = os.path.getsize(out)
    new = os.path.getsize(tmp)
    os.replace(tmp, out)
    return len(blob), old, new


def plates():
    """지명판·던전 이름표 — 256x256 4bpp(fmt 0x0500) 두 장, 패딩 없음."""
    ns = [d for d in sorted(os.listdir(EXT))
          if (d.startswith('mapname') or (d.startswith('MN') and d not in ('MNUM', 'MNTEMP')))]
    bad = []
    for n in ns:
        raw, old, new = build(n, [(n + 'A', n + 'A.png', 0x0500, 256, 256),
                                  (n + 'B', n + 'B.png', 0x0500, 256, 256)],
                              args=('-pal4', '-1555'))
        if new > old:
            bad.append('%s %d>%d' % (n, new, old))
    print('이름표 %d장 재조립 / 원본보다 커진 것 %d개 %s'
          % (len(ns), len(bad), ' '.join(bad[:6])))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('all', 'ctrl'):
        for n in ('CA_16', 'CB_16'):
            raw, old, new = build(n, [(n + 'A', n + 'A.png', 0x0401, 512, 512),
                                      (n + 'B', n + 'B.png', 0x0401, 256, 256)])
            print('%s  해제 %d B / .l40 %d -> %d B  (%s)'
                  % (n, raw, old, new, '여유 있음' if new <= old else '★원본보다 큼'))
    if what in ('all', 'plates'):
        plates()
