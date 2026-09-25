# -*- coding: utf-8 -*-
"""번역 자산의 «가역» 표기 규칙.

TSV 한 칸에 담기 위해 제어 바이트를 이스케이프한다.
  0x0A                     -> \\n   (개행)
  0x09                     -> \\t
  백슬래시                 -> \\\\
  그 밖의 0x00~0x1F, 0x7F  -> \\xNN
  cp932 로 못 읽는 바이트  -> \\xNN
디코드는 SJIS(cp932). 되돌리면 «원본 바이트와 정확히 같아야» 한다.
"""

BS = chr(0x5c)


def decode(raw: bytes) -> str:
    out = []
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if b == 0x0a:
            out.append(BS + 'n'); i += 1; continue
        if b == 0x09:
            out.append(BS + 't'); i += 1; continue
        if b == 0x1f and i + 1 < n:
            # ★0x1F 은 «인자 1바이트»를 먹는 제어열이다. 인자를 글자로 읽으면 안 된다.
            out.append(BS + 'x1F' + BS + 'x%02X' % raw[i + 1]); i += 2; continue
        if b < 0x20 or b == 0x7f:
            out.append(BS + 'x%02X' % b); i += 1; continue
        if b == 0x5c:
            # cp932 에서 0x5C 는 ¥ 로 보이지만 원본 바이트를 보존한다
            out.append(BS + BS); i += 1; continue
        if (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc) and i + 1 < n:
            try:
                out.append(raw[i:i + 2].decode('cp932')); i += 2; continue
            except UnicodeDecodeError:
                pass
        try:
            out.append(raw[i:i + 1].decode('cp932')); i += 1; continue
        except UnicodeDecodeError:
            out.append(BS + 'x%02X' % b); i += 1
    return ''.join(out)


def encode(text: str) -> bytes:
    out = bytearray()
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == BS:
            if i + 1 >= n:
                raise ValueError('문자열이 백슬래시로 끝난다: %r' % text)
            k = text[i + 1]
            if k == 'n':
                out += b'\x0a'; i += 2; continue
            if k == 't':
                out += b'\x09'; i += 2; continue
            if k == BS:
                out += b'\x5c'; i += 2; continue
            if k == 'x':
                out += bytes([int(text[i + 2:i + 4], 16)]); i += 4; continue
            raise ValueError('알 수 없는 이스케이프: %r' % text[i:i + 2])
        out += c.encode('cp932')
        i += 1
    return bytes(out)


def roundtrip_ok(raw: bytes) -> bool:
    try:
        return encode(decode(raw)) == raw
    except Exception:
        return False
