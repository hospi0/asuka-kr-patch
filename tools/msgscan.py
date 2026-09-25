# -*- coding: utf-8 -*-
"""메시지 경계 판정 (DATASCR.BIN / SSCR.BIN / 1NOSDC.BIN 공용).

★함정 1 — 메시지 «안»에 제어코드가 들어간다.
  `10 アスカ＠「うぬ、この殺気! 1F 0F 0A 　おぬし…… 00`
  제어 바이트에서 멈추는 단순 역추적은 앞부분을 통째로 날린다(500건 이상 잘려 있었다).

★함정 2 — **0x1F 는 인자 1바이트를 먹는다.** 그 인자가 우연히 SJIS 선두 바이트
  (예 `1F 96`)면 「끝에 반쪽짜리 2바이트 문자가 남은」 꼴이 되어 문자열 전체가
  통째로 탈락한다. 실제로 DATASCR 45건·SSCR 7건의 진짜 대사가 그렇게 사라졌다.
  → 파싱은 반드시 «앞에서 뒤로» 토큰 단위로 한다.

토큰:
  0x00            종단
  0x0A            개행
  0x1F XX         제어 2바이트 (인자 포함)
  0x01~0x1E, 0x7F 제어 1바이트
  0x20~0x7E       반각
  0xA1~0xDF       반각 가나
  lead+trail      전각 1글자
"""
import re

TEXT_OPCODES = (0x10, 0x11)
ARG_CTRL = (0x1f,)          # 인자 1바이트를 먹는 제어코드
JP = re.compile(r'[ぁ-ゟァ-ヿ一-鿿]')
KANA = re.compile(r'[ぁ-ゟァ-ヿ]')
MAX_LEN = 1024
MIN_JP = 2
MAX_CTRL_RATIO = 0.34


def _lead(b):
    return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef


def _trail(b):
    return 0x40 <= b <= 0xfc and b != 0x7f


def _single(b):
    return 0x20 <= b <= 0x7e or 0xa1 <= b <= 0xdf


def parse(d, st, rep, limit=MAX_LEN):
    """st 에서 앞으로 토큰을 읽는다. (끝오프셋, 표시문자열, 제어바이트수) 또는 None."""
    i = st
    n = len(d)
    text = []
    nctrl = 0
    while i < n and i - st < limit:
        b = d[i]
        if b == 0x00:
            return i, ''.join(text), nctrl
        if b == 0x0a:
            text.append('\n'); i += 1; continue
        if b in TEXT_OPCODES:
            # ★텍스트 opcode 는 «다음 메시지의 시작»이다. 메시지 안에 들어올 수 없다.
            #   (이걸 막지 않으면 `00 ! 10 アスカ「…` 처럼 앞 명령 바이트를 삼킨다)
            return None
        if b in ARG_CTRL:
            if i + 1 >= n:
                return None
            nctrl += 2; i += 2; continue
        if b < 0x20 or b == 0x7f:
            nctrl += 1; i += 1; continue
        if _lead(b) and i + 1 < n and _trail(d[i + 1]):
            try:
                c = d[i:i + 2].decode('cp932')
            except UnicodeDecodeError:
                return None
            if rep is not None and c not in rep:
                return None
            text.append(c); i += 2; continue
        if _single(b):
            c = d[i:i + 1].decode('cp932')
            if rep is not None and c not in rep:
                return None
            text.append(c); i += 1; continue
        return None
    return None


def _accept(d, st, rep, min_jp, need_kana):
    if d[st] < 0x20:                      # 선두 제어 바이트는 메시지가 아니라 구분자/명령
        return None
    r = parse(d, st, rep)
    if r is None:
        return None
    end, text, nctrl = r
    if end == st:
        return None
    if len(JP.findall(text)) < min_jp:
        return None
    if need_kana and not KANA.search(text):
        return None
    if nctrl > (end - st) * MAX_CTRL_RATIO:
        return None
    return end


def messages(d, rep, need_kana=False, min_jp=MIN_JP):
    """(시작오프셋, 원본바이트, 앞바이트) 목록, 오프셋 순. 서로 겹치지 않는다."""
    n = len(d)
    cov = bytearray(n)
    found = []

    def take(st, end):
        for k in range(st, end):
            cov[k] = 1
        found.append((st, bytes(d[st:end]), d[st - 1] if st else 0x00))

    # --- 1단계: 확실한 앵커 (텍스트 opcode 뒤 / NUL 뒤 문자열 풀) ---
    i = 0
    while i < n:
        cand = None
        if d[i] in TEXT_OPCODES and i + 1 < n:
            cand = i + 1
        elif i == 0 or d[i - 1] == 0x00:
            cand = i
        if cand is not None and not cov[cand]:
            end = _accept(d, cand, rep, min_jp, need_kana)
            if end is not None and not any(cov[cand:end]):
                take(cand, end)
                i = end + 1
                continue
        i += 1

    # --- 2단계: 남은 NUL 을 종단으로 삼는 «가장 긴» 유효 파싱 ---
    for end in range(n):
        if d[end] != 0 or cov[end]:
            continue
        lo = max(0, end - MAX_LEN)
        for st in range(lo, end):
            if cov[st] or d[st] < 0x20:
                continue
            e = _accept(d, st, rep, min_jp, need_kana)
            if e == end and not any(cov[st:end]):
                take(st, end)
                break

    found.sort()
    return found
