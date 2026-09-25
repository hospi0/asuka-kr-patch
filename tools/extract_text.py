# -*- coding: utf-8 -*-
"""번역 모집단 추출 -> 종류별 TSV (`my files/tsv2/`).

모집단 (전 디스크 241개 파일 스캔으로 확정, work/population_scan.txt):
  DATASCR.BIN  본편 스크립트 VM 바이트코드 (인라인 문자열)
  SSCR.BIN     시스템 스크립트 10섹션
  1NOSDC.BIN   실행 파일 안의 UI 문자열 (★대부분은 «가나한자 변환 사전»이라 제외)
그 밖의 파일(DATAOBJ/DATASHF/DATAFIX/2_DP/SFD/PVR/DP*)의 후보는 전부
그래픽·동영상·IME 사전 잡음이었다 — 표본으로 확인했다.

⚠️ 그래픽에 «구워진» 텍스트는 이 모집단에 없다 (별도 조사 대상).
"""
import sys, os, re, json, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from msgscan import messages, JP
from textio import decode, encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')
OUTDIR = os.path.join(ROOT, 'my files', 'tsv2')      # 번역표 «현행» 세대
CHUNK_BYTES = 30 * 1024

# SSCR.BIN 섹션 id -> 분류
SSCR_SECTIONS = {
    0: '09_디버그',
    1: '02_시스템UI',
    2: '03_전투메시지',
    3: '04_몬스터',
    4: '05_아이템명',
    5: '06_아이템설명',
    6: '03_전투메시지',
    7: '07_함정',
    8: '03_전투메시지',
    9: '08_네트워크·기타',
}


def repertoire(font):
    """화면에 그릴 수 있는 글자 + 런타임 매크로."""
    rep = set(font.chars)                                   # 전각 2,472
    rep |= set(chr(c) for c in range(0x20, 0x7f))           # 반각 표 (0x8f800 / 0x95000 실측)
    rep |= set('\n')
    rep |= set('＠')          # ★플레이어 이름 자리표시자 — 폰트에 없지만 본문에 733회 나온다
    return rep


def sscr_sections(d):
    out = []
    for i in range(0, 0x100, 8):
        sid, off = struct.unpack_from('<II', d, i)
        if sid == 0xFFFFFFFF:
            break
        out.append((sid, off))
    out.append((None, len(d)))
    return out


# ★1NOSDC.BIN 실측 (2026-08-25)
#   0x100000~0x160000 는 통째로 «가나한자 변환 사전»(이름입력·드림패스포트 IME)이고,
#   그 밖의 후보는 전부 SH-4 기계어 오검출이었다(400건 전수 확인, 진짜 텍스트 0건).
#   실제 UI 문자열은 아래 두 구간뿐이다.
EXE_RANGES = [
    ('10_실행파일UI',      0x107300, 0x107d00),   # 기본이름·버튼 라벨·VMU 파일명·재생상태
    ('11_이름입력문자표',   0x108300, 0x108900),   # ★가나 팔레트 — 번역이 아니라 «한글 입력 설계»가 필요
]


def write_tsv(rows, category):
    os.makedirs(OUTDIR, exist_ok=True)
    header = ['id', 'file', 'offset', 'budget', 'same_as', 'jp', 'kr']
    head_line = '\t'.join(header)
    parts, cur, size = [], [], 0
    for r in rows:
        line = '\t'.join([r['id'], r['file'], '0x%X' % r['off'], str(len(r['raw'])),
                          r.get('same_as', ''), r['text'], ''])
        b = len(line.encode('utf-8')) + 1
        if cur and size + b > CHUNK_BYTES:
            parts.append(cur); cur, size = [], 0
        if not cur:
            size = len(head_line.encode('utf-8')) + 1
        cur.append(line); size += b
    if cur:
        parts.append(cur)
    paths = []
    for i, p in enumerate(parts, 1):
        fn = os.path.join(OUTDIR, '%s_%02d.tsv' % (category, i))
        with open(fn, 'w', encoding='utf-8', newline='') as f:
            f.write(head_line + '\n')
            f.write('\n'.join(p) + '\n')
        paths.append(fn)
    return paths


def main():
    font = Font(os.path.join(ISO, 'DATAAPP.BIN'))
    rep = repertoire(font)
    buckets = collections.defaultdict(list)
    stats = []

    # --- DATASCR: 본편 대사 ---
    d = open(os.path.join(ISO, 'DATASCR.BIN'), 'rb').read()
    ms = messages(d, rep)
    for i, (off, raw, prev) in enumerate(ms):
        buckets['01_대사'].append(dict(id='SCR%05d' % i, file='DATASCR.BIN',
                                      off=off, raw=raw, prev=prev, text=decode(raw)))
    stats.append(('DATASCR.BIN', len(ms), sum(len(r) for _, r, _ in ms)))

    # --- SSCR: 섹션별 ---
    d = open(os.path.join(ISO, 'SSCR.BIN'), 'rb').read()
    secs = sscr_sections(d)
    ms = messages(d, rep)
    for i, (off, raw, prev) in enumerate(ms):
        cat = '08_네트워크·기타'
        for k in range(len(secs) - 1):
            if secs[k][1] <= off < secs[k + 1][1]:
                cat = SSCR_SECTIONS[secs[k][0]]
                break
        buckets[cat].append(dict(id='SYS%05d' % i, file='SSCR.BIN',
                                 off=off, raw=raw, prev=prev, text=decode(raw)))
    stats.append(('SSCR.BIN', len(ms), sum(len(r) for _, r, _ in ms)))

    # --- 1NOSDC: 실행 파일 UI ---
    d = open(os.path.join(ISO, '1NOSDC.BIN'), 'rb').read()
    allms = messages(d, rep, min_jp=1)
    ms = []
    for cat, a, b in EXE_RANGES:
        sub = [m for m in allms if a <= m[0] < b]
        for i, (off, raw, prev) in enumerate(sub):
            buckets[cat].append(dict(id='EXE%05X' % off, file='1NOSDC.BIN',
                                     off=off, raw=raw, prev=prev, text=decode(raw)))
        ms += sub
    stats.append(('1NOSDC.BIN', len(ms), sum(len(r) for _, r, _ in ms)))

    # --- 가역성 검산 ---
    bad = [r for rows in buckets.values() for r in rows if encode(r['text']) != r['raw']]
    if bad:
        raise SystemExit('가역성 실패 %d건' % len(bad))
    print('왕복 검산 통과 (%d항목)' % sum(len(v) for v in buckets.values()))

    # --- 중복 표시 ---
    first = {}
    for cat in sorted(buckets):
        for r in sorted(buckets[cat], key=lambda r: r['off']):
            key = r['text']
            if key in first:
                r['same_as'] = first[key]
            else:
                first[key] = r['id']

    # --- 출력 ---
    index = []
    for cat in sorted(buckets):
        rows = sorted(buckets[cat], key=lambda r: r['off'])
        paths = write_tsv(rows, cat)
        nb = sum(len(r['raw']) for r in rows)
        nuniq = sum(1 for r in rows if not r.get('same_as'))
        index.append(dict(category=cat, items=len(rows), unique=nuniq, bytes=nb, files=len(paths)))
        print('%-16s 항목 %5d (고유 %5d)  원본 %7d B  TSV %2d개' % (cat, len(rows), nuniq, nb, len(paths)))

    print()
    for f, n, b in stats:
        print('  %-14s %5d 항목  %7d B' % (f, n, b))
    json.dump(index, open(os.path.join(ROOT, 'work', 'corpus_index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
