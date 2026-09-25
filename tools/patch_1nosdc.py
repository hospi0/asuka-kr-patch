# -*- coding: utf-8 -*-
"""게임 실행파일 `1NOSDC.BIN` 의 LZ40 해제 루틴 패치 (VincentNL DATABG 도구 동봉).

★재빌드한 `DATABG.bin` 은 CUE LZ40(매직 0x40) 로 다시 구워진다. 원본 게임은 자기
  변종(매직 0x34)만 읽으므로 그대로 넣으면 **부팅이 안 된다**(실기 확인 2026-08-29).
  도구는 추출이 끝난 뒤 「Update Game — 새 압축에 맞게 게임 데이터를 갱신할까요?」
  대화상자로 이 패치를 적용한다. 그 창이 안 떠서 여기에 옮겨 심는다.

출처: `DATABG_ext.exe` 내부 pyc 상수 — `'r+b'`, 오프셋 14184(0x3768),
      hex 443자(=148바이트) 순서로 박혀 있다.
검증: 원본 0x3768 `01 75 54 66 54 60 6c 66 ...` / 패치 `06 75 54 66 54 60 6c 66 ...`
      — 첫 명령(`add #1,r5` -> `add #6,r5`)만 다르고 뒤가 이어진다. 같은 루틴이다.
"""

OFFSET = 0x3768
HEX = (
    "06 75 54 66 54 60 6C 66 0C 60 18 40 0B 26 54 60 0C 60 28 40 0B 26 66 2F"
    " 4C 36 00 E3 62 34 37 89 38 23 04 8B 54 67 7C 67 7B 67 80 E3 3C 63 33 60"
    " 79 20 08 20 03 8B 54 61 10 24 27 A0 01 74 54 61 1C 61 54 60 0C 60 18 40"
    " 0B 21 13 62 23 60 0F C9 03 62 02 E0 02 32 0E 89 54 62 2C 62 13 60 0F C9"
    " 08 20 01 8B 07 A0 10 72 54 60 0C 60 18 40 0B 22 44 E0 08 40 0C 32 28 22"
    " 08 89 09 41 09 41 43 60 18 30 00 60 00 24 01 74 10 42 F8 8B C6 AF 01 43"
    " 0B 00 F6 60"
)
PATCH = bytes.fromhex(HEX.replace(' ', ''))


def apply(buf):
    """bytes/bytearray 를 받아 패치된 bytes 를 돌려준다. 크기 불변."""
    b = bytearray(buf)
    assert OFFSET + len(PATCH) <= len(b), '1NOSDC.BIN 이 너무 짧다'
    b[OFFSET:OFFSET + len(PATCH)] = PATCH
    return bytes(b)


def region():
    return OFFSET, OFFSET + len(PATCH)
