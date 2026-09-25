# -*- coding: utf-8 -*-
"""PoC 빌드 — 구간(region) 단위 재조립.

PoC #2 의 질문: «인접 메시지끼리 예산을 주고받을 수 있는가?»
  구간 전체 바이트 수는 그대로 두고 앞 메시지를 늘리고 뒤 메시지를 줄인다.
  둘 다 정상 출력되면 이 구간에 «절대 오프셋 참조가 없다»는 뜻이다.

미리보기(무인자)까지가 자동 범위. 실제 디스크 쓰기는 --write 로만.
"""
import sys, os, shutil, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from mkglyph import render
from charmap import CharMap
from discwrite import TrackWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_DIR = r"C:\claude\roms\dc\Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan (Japan)"
BASE = "Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan! (Japan)"
BUILD = os.path.join(ROOT, 'build', 'poc')

TRACK5_START_LBA, TRACK5_SKIP = 140708, 225
LBA_DATAAPP, SZ_DATAAPP = 492080, 612352
LBA_DATASCR = 164129

FONT_NAME = 'nanumb'
OP_STR = 0x10

# --- 패치할 구간 ---------------------------------------------------------
# (시작, 끝) 은 DATASCR.BIN 안의 절대 오프셋. 그 사이를 items 로 «완전히» 재구성한다.
# 'str'  : OP_STR + 인코딩 + NUL
# 'raw'  : 원본 바이트 그대로 (검산용으로 값을 적어 둔다)
REGIONS = [
    dict(
        name='오프닝 소녀 (PoC#2 예산이동)',
        start=0xa426, end=0xa480,
        items=[
            ('str', '소녀「정겨워라\n　언제나　그리운　풍경。'),        # 원본 33B -> 39B (+6)
            ('raw', bytes.fromhex('0103')),
            ('str', '　드디어　돌아왔구나。\n　１년만의　고향……。'),   # 원본 51B -> 45B (-6)
        ],
        expect_jp=['少女「なつかしい\n　いつもの景色。',
                   '　やっと帰ってこれたんだわ。\n　１年ぶりの故郷……。'],
    ),
]
# ------------------------------------------------------------------------


def assemble(cm, region, scr):
    out = bytearray()
    for kind, payload in region['items']:
        if kind == 'str':
            out += bytes([OP_STR]) + cm.encode(payload) + b'\x00'
        elif kind == 'raw':
            out += payload
        else:
            raise ValueError(kind)
    want = region['end'] - region['start']
    if len(out) != want:
        raise SystemExit('%s: 구간 길이 불일치 — 만든 것 %d B, 원본 구간 %d B (차이 %+d)'
                         % (region['name'], len(out), want, len(out) - want))
    return bytes(out)


def build(write=False):
    f = Font(os.path.join(ROOT, 'work', 'iso', 'DATAAPP.BIN'))
    scr = bytearray(open(os.path.join(ROOT, 'work', 'iso', 'DATASCR.BIN'), 'rb').read())

    cm = CharMap(f)
    for r in REGIONS:
        for kind, payload in r['items']:
            if kind == 'str':
                cm.assign([c for c in payload if '가' <= c <= '힣'])
    print('한글 음절 %d개 배정, 남은 칸 %d개' % (len(cm.map), len(cm.pool)))

    # 글리프 삽입
    for syl, idx in sorted(cm.map.items(), key=lambda kv: kv[1]):
        f.set_cell(idx, render(syl, name=FONT_NAME))
        f.set_width(idx, 0, 25)
    print('  %s' % ' '.join('%s->%s' % (s, f.chars[i]) for s, i in cm.map.items()))

    # 구간 재조립
    for r in REGIONS:
        # 원본 검산: 구간 안의 문자열이 예상한 원문인가
        pos = r['start']
        got = []
        while pos < r['end']:
            if scr[pos] == OP_STR:
                j = scr.index(0, pos + 1)
                got.append(bytes(scr[pos + 1:j]).decode('cp932'))
                pos = j + 1
            else:
                pos += 1
        if got != r['expect_jp']:
            raise SystemExit('%s: 원본 문자열 불일치\n  기대 %r\n  실제 %r' % (r['name'], r['expect_jp'], got))
        new = assemble(cm, r, scr)
        print('%s: %#x..%#x (%d B) 재조립 OK' % (r['name'], r['start'], r['end'], len(new)))
        r['_bytes'] = new

    cm.snapshot(os.path.join(ROOT, 'data', 'charmap_poc.json'))

    if not write:
        print('\n[미리보기] 실제 쓰기는 --write')
        return f, cm

    os.makedirs(BUILD, exist_ok=True)
    for n in (1, 2, 3, 4, 5):
        src = os.path.join(ROM_DIR, '%s (Track %d).bin' % (BASE, n))
        dst = os.path.join(BUILD, os.path.basename(src))
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
            print('  복사 track%d ...' % n)
            shutil.copyfile(src, dst)
    shutil.copyfile(os.path.join(ROM_DIR, '%s.cue' % BASE), os.path.join(BUILD, '%s.cue' % BASE))

    t5 = TrackWriter(os.path.join(BUILD, '%s (Track 5).bin' % BASE), TRACK5_START_LBA, TRACK5_SKIP)
    assert t5.read_user(LBA_DATAAPP, 0, 4) == b'SDRV'
    t5.write_user(LBA_DATAAPP, 0, bytes(f.buf))
    for r in REGIONS:
        orig = t5.read_user(LBA_DATASCR, r['start'], r['end'] - r['start'])
        if bytes(orig) != bytes(scr[r['start']:r['end']]):
            raise SystemExit('디스크의 원본 구간이 work 사본과 다르다 — track5 가 이미 패치본이다')
        t5.write_user(LBA_DATASCR, r['start'], r['_bytes'])
    n = t5.close()
    print('\n기록 완료. EDC/ECC 재계산 섹터 %d개 -> %s' % (n, BUILD))
    return f, cm


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    build(ap.parse_args().write)
