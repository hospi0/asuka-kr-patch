# -*- coding: utf-8 -*-
"""LZ40 (CUE 의 LZX 계열) 해제/압축 — `DATABG.BIN` 이 이 포맷이다.

원본 규격은 `C:\\claude\\utils\\dreamcast\\LZ40_Decompress_SH4\\LZ40_dec.asm`
(VincentNL 의 SH-4 루틴)을 그대로 옮긴 것이다. 같은 저장소의 `Shiren_DataBG_ext`
가 «이 게임의 DATABG.bin» 을 다루는 완결 사례로 등록돼 있다
[[reference_dreamcast_tools]] — 다만 저장소엔 README 만 있고 exe 는 릴리스 자산이라
여기서 다시 구현했다.

스트림 구조
    [매직 1B][해제 길이 3B LE][ 플래그 바이트 + 토큰 ... ]
  플래그는 MSB(0x80)부터 한 비트씩 쓰고, 비트가 서면 «역참조», 아니면 «리터럴».
  역참조: u16 `pos` (LE) → 길이 = pos & 0xF, 거리 = pos >> 4
    길이 0/1 이면 다음 1바이트를 길이로 읽고
      nibble==0 → 길이 += 0x10
      nibble==1 → 다시 1바이트를 상위로 이어 붙이고 길이 += 0x110
"""
import struct


def decompress(buf, off=0):
    """(해제 데이터, 소비한 압축 바이트 수)."""
    p = off + 1                                   # 매직 1바이트는 건너뛴다
    n = buf[p] | (buf[p + 1] << 8) | (buf[p + 2] << 16)
    p += 3
    out = bytearray()
    flags = 0
    mask = 0
    while len(out) < n:
        if mask == 0:
            flags = buf[p]; p += 1
            mask = 0x80
        if flags & mask:                          # 역참조
            pos = buf[p] | (buf[p + 1] << 8); p += 2
            ln = pos & 0xF
            if ln < 2:
                ln = buf[p]; p += 1
                if (pos & 0xF) == 0:
                    ln += 0x10
                else:
                    ln |= buf[p] << 8; p += 1
                    ln += 0x110
            dist = pos >> 4
            if ln:
                if dist == 0 or dist > len(out):
                    raise ValueError('거리 이상 dist=%d len(out)=%d @0x%X' % (dist, len(out), p))
                for _ in range(ln):
                    out.append(out[len(out) - dist])
        else:                                     # 리터럴
            out.append(buf[p]); p += 1
        mask >>= 1
    return bytes(out), p - off


def compress(data, magic=0x40):
    """되빌드용 — 정확성 우선의 단순 탐색(최장 일치).

    ⚠거리는 12비트(pos>>4)라 최대 0xFFF, 길이는 0x110+0xFFFF 까지 표현된다.
    """
    out = bytearray([magic, len(data) & 0xFF, (len(data) >> 8) & 0xFF, (len(data) >> 16) & 0xFF])
    tok = []
    i = 0
    N = len(data)
    while i < N:
        best_l, best_d = 0, 0
        lo = max(0, i - 0xFFF)
        for d in range(1, i - lo + 1):
            j = i - d
            l = 0
            while i + l < N and l < 0x1000 and data[j + l % d if False else j + l] == data[i + l]:
                l += 1
                if j + l >= i + l:
                    pass
            if l > best_l:
                best_l, best_d = l, d
        if best_l >= 3:
            tok.append((best_d, best_l))
            i += best_l
        else:
            tok.append(data[i])
            i += 1
    # 플래그 8개 단위로 묶어 출력
    k = 0
    while k < len(tok):
        grp = tok[k:k + 8]
        fl = 0
        body = bytearray()
        for b, t in enumerate(grp):
            if isinstance(t, tuple):
                fl |= 0x80 >> b
                d, l = t
                if 2 <= l <= 0xF:
                    body += struct.pack('<H', (d << 4) | l)
                elif l <= 0x10 + 0xFF:
                    body += struct.pack('<H', d << 4) + bytes([l - 0x10])
                else:
                    v = l - 0x110
                    body += struct.pack('<H', (d << 4) | 1) + bytes([v & 0xFF, (v >> 8) & 0xFF])
            else:
                body.append(t)
        out.append(fl)
        out += body
        k += 8
    return bytes(out)


def streams(buf):
    """파일 전체를 «연속된 LZ40 스트림»으로 훑는다 -> [(오프셋, 해제데이터, 압축크기)]."""
    out = []
    p = 0
    while p < len(buf) - 4:
        try:
            data, used = decompress(buf, p)
        except Exception:
            break
        if used <= 4 or not data:
            break
        out.append((p, data, used))
        p += used
        while p < len(buf) and buf[p] == 0:        # 정렬 패딩
            p += 1
    return out
