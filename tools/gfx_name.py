# -*- coding: utf-8 -*-
"""이름입력 화면의 «구운 라벨»을 한글로 바꾼다 (DATASZU.BIN).

아틀라스는 **가로 128px 에서 줄바꿈되는 선형 글자 띠**다. 라벨 하나가 줄을 넘어가므로
(「かな・カナ・英」+ 다음 줄 「数」) 각 라벨의 «픽셀 구간»을 그대로 유지해서 다시 그린다.
그래야 게임이 어느 사각형을 잘라 쓰든 어긋나지 않는다.

색인(팔레트는 파일에 없다 — 런타임 공급):  테두리 0x0C / 속살 0xAF
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx_szu import Atlas, draw_span, draw_span_cells, CHUNK

FILL, OUT = 0xAF, 0x0C

# (아틀라스, 새 문구, [(x0,y0,x1,y1) ...], 세로로 늘릴지)
JOBS = [
    ('n_fonticon00', '한글1·영숫자', [(2, 0, 127, 25), (0, 27, 22, 51)], False),
    # 세로로 채우되 위아래 2px 씩 여백 (사용자 지시 2026-08-29)
    ('n_fonticon00', '한글2',       [(32, 31, 76, 47)], True),
    # ⛔이 라벨은 「おこなう(行う)」가 아니라 **「おぎなう(補う)」** 다 — 확대해 보면
    #   두 번째 글자에 탁점이 붙어 있다. R트리거가 탁점, L트리거가 반탁점을 «보충»하는 짝.
    #   한글 팔레트에선 둘 다 죽은 기능(치환표가 가나만 가리킨다)이라 **비운다**.
    #   ★128px 경계에서 «글자 중간»이 잘려 다음 줄로 이어진다(row2 끝 9px = 「お」 왼쪽 절반).
    ('n_fonticon00', '',            [(119, 27, 127, 51), (0, 53, 76, 76)], False),
    ('n_fonticon00', '끝내기',      [(11, 81, 76, 100)], False),
    ('n_fonticon00', '삭제',        [(79, 78, 122, 103)], False),
    # 하단 안내문
    ('n_fonticon01', 'L·R트리거로 페이지 전환',
     [(3, 0, 127, 25), (0, 26, 127, 51)], False),
    # 3행은 «글자가 더 작은 줄»이다 — 여기까지 이어 쓰면 「전환」만 작아지고 벌어진다.
    ('n_fonticon01', '', [(0, 56, 70, 74)], False),
    # ⛔「Ｌトリガーでおぎなう・」 — 반탁점 보충. 한글엔 없는 기능이라 비운다.
    ('n_fonticon01', '',
     [(80, 56, 127, 74), (0, 83, 120, 100)], False),
    # ⛔한글엔 탁점이 없다 — R트리거 안내는 비운다(치환표가 가나만 가리켜 무반응).
    ('n_fonticon01', '', [(127, 83, 127, 100), (0, 109, 125, 126)], False),
]


# ★★실측: 게임은 아틀라스 줄의 «x116 까지»만 그린다.
#   실기 스샷에서 「숫」이 42px 짜리 글자인데 21px 만 나왔다 — 잉크가 x108.5 에서
#   시작하니 x116 에서 끊긴 것이다. 「로」·「환」도 같은 자리에서 잘렸다.
#   그래서 모든 조각의 오른쪽 끝을 116 으로 자른다.
RIGHT_EDGE = 116


def _clip(segs):
    return [(x0, y0, min(x1, RIGHT_EDGE), y1) for x0, y0, x1, y1 in segs
            if x0 <= RIGHT_EDGE]


def apply(buf):
    per = {}
    for name in ('n_fonticon00', 'n_fonticon01'):
        per[name] = Atlas(buf, name)
    per['n_fonticon00'].clear(32, 27, 76, 51)      # 「漢字」 자리 전체를 먼저 지운다
    # ★상자를 줄인 라벨은 «원본 상자»를 따로 지워야 가장자리에 찌꺼기가 안 남는다
    for x0, y0, x1, y1 in ((32, 27, 76, 51), (11, 78, 76, 103)):
        per['n_fonticon00'].clear(x0, y0, x1, y1)
    for name, text, segs, st in JOBS:      # ★먼저 «자르기 전» 상자를 통째로 지운다
        for x0, y0, x1, y1 in segs:
            per[name].clear(x0, y0, x1, y1)
    for name, text, segs, st in JOBS:
        a = per[name]
        if not text:
            for x0, y0, x1, y1 in segs:
                a.clear(x0, y0, x1, y1)
            continue
        if st:
            draw_span(a, text, _clip(segs), FILL, OUT, stretch=True)
        else:
            draw_span_cells(a, text, _clip(segs), FILL, OUT)
    for a in per.values():
        a.write_back()
    return per


if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(ROOT, 'work', 'iso', 'DATASZU.BIN')
    buf = bytearray(open(src, 'rb').read())
    per = apply(buf)
    for n, a in per.items():
        a.preview(os.path.join(ROOT, 'work', 'atlas', 'prev_%s.png' % n), 4)
    print('ok')
