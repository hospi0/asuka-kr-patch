# -*- coding: utf-8 -*-
"""한글 음절 -> «재활용할 원본 전각 글자» 배정표.

- 후보는 원본 텍스트 코퍼스(DATASCR/SSCR/1NOSDC 의 폰트필터 통과 문자열)에서
  출현 0회인 문자표 칸.
- ⛔ 黑(인덱스 2471, SJIS 0xEEEC) 은 제외 — PoC #1 에서 게임이 못 찾고 〒 를 그렸다.
- 배정은 «파일로 스냅샷»한다. 번역이 바뀌면 index 가 통째로 밀리므로
  빌드마다 배정표를 남겨야 재현이 된다.
"""
import os, json, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from str_scan import strings

BS = chr(0x5c)
PLACEHOLDER = '＠'      # 플레이어 이름 자리표시자 — 폰트엔 없고 런타임에 이름으로 바뀐다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = ('DATASCR', 'SSCR', '1NOSDC')
BANNED_INDEX = {2471}          # 黑
# 페이지0(인덱스 0~360)은 약물·ASCII·가나 칸 — 우리 번역문이 쓸 기호가 여기 있으므로
# 「원문에 안 쓰인다」고 해서 함부로 가져가지 않는다. (한글 음절은 한자 칸에서만)
PROTECT_BELOW = 361
POOL_PATH = os.path.join(ROOT, 'data', 'slot_pool.json')

# ★본 빌드용 — 한자 칸만 자원으로 쓴다 (사용자 지시 2026-08-28).
#   가나·기호·라틴·그리스·키릴 칸은 «나중에 쓸지도 모르니» 손대지 않는다.
#   SJIS 0x889F 부터가 한자(JIS 1수준). 실측: 한자 2,189칸 / 가나 169 / 기호 114.
KANJI_SJIS_START = 0x889F


def is_kanji_slot(ch):
    b = ch.encode('cp932')
    return ((b[0] << 8) | b[1]) >= KANJI_SJIS_START


def corpus_usage(font):
    """원문 코퍼스에서 각 문자가 몇 번 쓰이는가 (폰트필터 통과 문자열 기준)."""
    rep = set(font.chars) | set('\n') | set(bytes(range(0x20, 0x7f)).decode())
    use = collections.Counter()
    for n in CORPUS:
        d = open(os.path.join(ROOT, 'work', 'iso', '%s.BIN' % n), 'rb').read()
        for _, s in strings(d):
            if all(c in rep for c in s):
                use.update(s)
    return use


def ks_syllables():
    """KS X 1001 완성형 2,350자를 «가나다순»으로.

    ★이름입력 «漢字» 페이지는 폰트 문자표(DATAAPP.BIN 0x8B242~)를 SJIS 순으로
      그대로 훑어 보여 준다. 그래서 남는 한자 칸을 «가나다순»으로 한글에 배정하면
      그 페이지가 통째로 «받침까지 있는 한글 음절표»가 된다.
    euc-kr 의 0xB0A1~0xC8FE 가 정확히 그 2,350자이고, 바이트 순서가 곧 가나다순이다.
    """
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try:
                out.append(bytes([hi, lo]).decode('euc-kr'))
            except UnicodeDecodeError:
                pass
    return out


# 남는 칸에 넣을 음절을 «쓸모 순»으로 고르기 위한 가중치.
# 이름·일반 한국어에 자주 나오는 중성·종성일수록 앞.
_JUNG_RANK = 'ㅏㅣㅓㅗㅜㅡㅐㅔㅕㅑㅛㅠㅚㅟㅢㅘㅝㅙㅞㅒㅖ'
_JONG_RANK = ' ㄴㅇㄹㅁㄱㅅㅂㅈㅎㅊㅍㅌㄷㅋㄲㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄㅆ'
_JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
_JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'


def syl_rank(ch):
    """음절 하나의 «쓸모» 순위 — 작을수록 먼저 넣는다."""
    n = ord(ch) - 0xAC00
    if not 0 <= n < 11172:
        return (99, 99, 99)
    jung, jong = (n // 28) % 21, n % 28
    return (_JONG_RANK.index(_JONG[jong]), _JUNG_RANK.index(_JUNG[jung]), n)


def kanji_pool(font, reserved=(), use=None, order='usage'):
    """한자 칸만 모아 «덮어도 손해가 적은 순»으로 정렬해 돌려준다.

    정렬 규칙 [[feedback_reserve_fnt_slots_of_untranslated]] §칸을 «빼지» 말고 «순서»를:
      1) 원문이 한 번도 안 쓰는 한자 → 먼저 (공짜)
      2) 원문이 쓰는 한자 → 적게 쓰는 것부터
    `reserved` 는 «우리가 다시 쓰지 않는 문자열»이 아직 가리키는 칸 — 아예 뺀다.
    """
    if use is None:
        use = corpus_usage(font)
    reserved = set(reserved)
    cand = [i for i, c in enumerate(font.chars)
            if i not in BANNED_INDEX and i not in reserved and is_kanji_slot(c)]
    # ★`order='index'` — 칸을 SJIS 오름차순 그대로 쓴다. 어차피 남는 칸까지 전부
    #   한글로 채우므로 «덜 쓰는 순»은 의미가 없고, 대신 이름입력 漢字 페이지가
    #   가나다순 한글표가 된다(그 화면은 문자표를 순서대로 훑는다).
    cand.sort(key=lambda i: i if order == 'index' else (use[font.chars[i]], i))
    return cand


def build_pool(font, save=True):
    rep = set(font.chars) | set('\n') | set(bytes(range(0x20, 0x7f)).decode())
    use = collections.Counter()
    for n in CORPUS:
        d = open(os.path.join(ROOT, 'work', 'iso', '%s.BIN' % n), 'rb').read()
        for _, s in strings(d):
            if all(c in rep for c in s):
                use.update(s)
    pool = [i for i, c in enumerate(font.chars)
            if use[c] == 0 and i not in BANNED_INDEX and i >= PROTECT_BELOW]
    if save:
        json.dump({'indexes': pool,
                   'chars': [font.chars[i] for i in pool]},
                  open(POOL_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return pool


def load_pool(font):
    if os.path.exists(POOL_PATH):
        p = json.load(open(POOL_PATH, encoding='utf-8'))
        assert [font.chars[i] for i in p['indexes']] == p['chars'], '문자표가 바뀌었다 — 풀 재생성 필요'
        return p['indexes']
    return build_pool(font)


class CharMap:
    """한글 음절 -> (글리프 인덱스, 그 칸의 원본 문자)"""
    def __init__(self, font, pool=None):
        self.font = font
        self.pool = list(pool if pool is not None else load_pool(font))
        self.map = {}          # 음절 -> index

    def assign(self, syllables):
        for ch in syllables:
            if ch in self.map:
                continue
            if not self.pool:
                raise SystemExit('슬롯 소진 — 한글 음절 %r 을 넣을 칸이 없다' % ch)
            self.map[ch] = self.pool.pop(0)

    def encode(self, text):
        """한글은 배정된 칸의 «원본 SJIS 코드»로, 나머지는 그대로 cp932."""
        out = bytearray()
        for ch in text:
            if ch == '\n':
                out += b'\x0a'
            elif ch in self.map:
                out += self.font.chars[self.map[ch]].encode('cp932')
            else:
                try:
                    out += ch.encode('cp932')
                except UnicodeEncodeError:
                    raise SystemExit('인코딩 누락: %r (폰트/문자표에 없음)' % ch)
                if ch not in self.font.index:
                    raise SystemExit('문자표에 없는 문자: %r' % ch)
        return bytes(out)

    def encode_tsv(self, text):
        """TSV 표기(textio 이스케이프 + 한글)를 게임 바이트로.

        textio.encode 와 같은 문법을 쓰되 한글은 배정된 칸의 원본 SJIS 코드로 바꾼다.
        ★인코딩 누락은 예외로 던진다 — 조용히 건너뛰면 화면이 깨진다.
        """
        out = bytearray()
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if c == BS:
                if i + 1 >= n:
                    raise KeyError('문자열이 백슬래시로 끝난다')
                k = text[i + 1]
                if k == 'n':
                    out += b'\x0a'; i += 2; continue
                if k == 't':
                    out += b'\x09'; i += 2; continue
                if k == BS:
                    out += b'\x5c'; i += 2; continue
                if k == 'x':
                    out += bytes([int(text[i + 2:i + 4], 16)]); i += 4; continue
                raise KeyError('알 수 없는 이스케이프 %r' % text[i:i + 2])
            if c in self.map:
                out += self.font.chars[self.map[c]].encode('cp932')
                i += 1; continue
            try:
                b = c.encode('cp932')
            except UnicodeEncodeError:
                raise KeyError(c)
            # ★★cp932 로 인코딩된다고 «그릴 수 있는» 게 아니다.
            #   게임은 전각 문자표(2,472자)를 이분탐색하고, 못 찾으면 〒 를 그린다.
            #   반각(0x20~0x7E)은 별도 반각표라 통과. ＠ 는 플레이어 이름 자리표시자.
            if len(b) == 2 and c not in self.font.index and c != PLACEHOLDER:
                raise KeyError(c)
            out += b
            i += 1
        return bytes(out)

    def snapshot(self, path):
        json.dump({'map': {k: v for k, v in self.map.items()},
                   'host': {k: self.font.chars[v] for k, v in self.map.items()},
                   'pool_left': len(self.pool)},
                  open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
