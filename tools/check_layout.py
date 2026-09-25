# -*- coding: utf-8 -*-
"""★패딩·번역이 «화면 폭»을 넘기지 않는지 검사.

예산(바이트)과 화면 폭(칸)은 다른 제약이다 [[feedback_cell_limit_not_byte_budget]].
상한은 추정하지 말고 «원본이 실제로 쓰는 최대 줄 폭»에서 실측한다
[[feedback_screen_limits_measure_not_derive]].

폭 단위는 폰트 폭표(VWF)가 아니라 «칸»으로 센다:
  전각 1칸 / 반각 0.5칸 — 원본과 번역을 같은 자로 재기 위한 상대 척도.
"""
import sys, os, re, collections, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from charmap import CharMap, kanji_pool, corpus_usage
from extract_text import ISO, OUTDIR
from check_tsv import load as load_tsv
import build_all as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTRL = re.compile(r'\\x[0-9A-Fa-f]{2}')


def cells(line):
    """한 줄의 화면 폭 (전각=2, 반각=1 의 «반칸» 단위)."""
    return sum(1 if ord(c) < 0x80 else 2 for c in line)


def lines_of(s):
    """★빌더와 «같은» 함수를 쓴다 — 두 벌로 두면 상한이 어긋난다."""
    return B.text_lines(s)


def main(top=25):
    per = B.read_rows()
    src = {n: open(os.path.join(ISO, n), 'rb').read()
           for n in ('DATASCR.BIN', 'SSCR.BIN', '1NOSDC.BIN')}

    # --- 원본이 실제로 쓰는 최대 줄 폭 (카테고리별 실측) ---
    lim = B.line_limits(per)

    out = ['=== 원본 최대 줄 폭 (반칸 단위, 전각=2) ===']
    for k in sorted(lim):
        out.append('   %-22s %3d  (전각 %.1f자)' % (k, lim[k], lim[k] / 2.0))

    # --- 번역문이 그 폭을 넘는가 (패딩 «전») ---
    out.append('')
    out.append('=== 번역문이 원본 최대 줄 폭을 넘는 행 ===')
    bad = collections.Counter()
    worst = []
    for rows in per.values():
        for r in rows:
            if not r['kr'].strip():
                continue
            for i, ln in enumerate(lines_of(r['kr'])):
                w = cells(ln)
                if w > lim[r['_cat']]:
                    bad[r['_cat']] += 1
                    worst.append((w - lim[r['_cat']], w, lim[r['_cat']], r, i, ln))
                    break
    for k, v in bad.most_common():
        out.append('   %-22s %5d행' % (k, v))
    out.append('   합계 %d행' % sum(bad.values()))

    worst.sort(key=lambda x: -x[0])
    out.append('')
    out.append('=== 초과가 큰 %d행 ===' % top)
    for d, w, l, r, i, ln in worst[:top]:
        out.append('   %s %s  %d줄째 폭 %d > 상한 %d (+%d)' % (r['_cat'], r['id'], i + 1, w, l, d))
        out.append('      %r' % ln)

    # --- 패딩이 마지막 줄을 얼마나 늘리는가 ---
    font = Font(os.path.join(ISO, 'DATAAPP.BIN'))
    keep, _ = B.untranslated_chars(per)
    use = corpus_usage(font)
    reserved = {font.index[c] for c in keep if c in font.index}
    syl = collections.Counter()
    for rows in per.values():
        for r in rows:
            if r['kr'].strip():
                syl.update(c for c in B.ESC.sub('', r['kr']) if '가' <= c <= '힣')
    cm = CharMap(font, pool=kanji_pool(font, reserved=reserved, use=use))
    cm.assign([c for c, _ in syl.most_common()])

    out.append('')
    out.append('=== 패딩 «후» 줄 폭이 상한을 넘는 구간 ===')
    out.append('   (빌더의 실제 pad_region 을 그대로 돌려서 «만들어진 바이트»를 잰다)')
    npad = nover = 0
    ex = []
    for name in ('DATASCR.BIN', 'SSCR.BIN', '1NOSDC.BIN'):
        if not per.get(name):
            continue
        regs, _e = B.plan_regions(per[name], src[name], name, cm)
        for reg in regs:
            if reg['slack'] <= 0:
                continue
            npad += 1
            r = reg['rows'][-1]
            limit = lim[r['_cat']]
            body, forced = B.pad_region(reg, limit)
            # 줄 경계는 0x0A 와 «메시지 종단자 0x00» 둘 다
            worst_w = max(B.byte_cells(l) for l in re.split(rb'[\n\x00]', body))
            if worst_w > limit:
                nover += 1
                ex.append((worst_w - limit, worst_w, limit, r, reg['slack']))
    out.append('   패딩 구간 %d개 중 상한 초과 %d개' % (npad, nover))
    ex.sort(key=lambda x: -x[0])
    for d, w, l, r, sl in ex[:top]:
        out.append('   %s %s  패딩 %dB -> 최대 줄 폭 %d > 상한 %d (+%d)'
                   % (r['_cat'], r['id'], sl, w, l, d))
        out.append('      kr=%r' % r['kr'][:120])

    path = os.path.join(ROOT, 'work', 'layout_check.txt')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')
    print('-> %s' % path)
    print('원본폭초과 %d행 / 패딩후초과 %d구간' % (sum(bad.values()), nover))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=25)
    main(ap.parse_args().top)
