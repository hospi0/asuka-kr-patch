# -*- coding: utf-8 -*-
"""번역 TSV 검사기 — 빌드 전에 «반드시» 통과해야 한다.

검사 항목
  1) 원본(jp) 이 디스크의 그 오프셋 바이트와 일치하는가        (표가 낡지 않았는지)
  2) 번역문(kr) 이 인코딩 가능한가                             (이스케이프 문법)
  3) 번역문에 폰트/문자표로 그릴 수 없는 문자가 있는가          ★인코딩 누락은 빌드 에러
  4) 바이트 예산                                              (구간 총량 규칙은 빌더가 본다)
  5) 매크로·서식 보존:  ＠(플레이어 이름) / %s %d / \\x1FXX 제어열
  6) 줄 수가 원본보다 늘지 않았는가                            (대사창 밖으로 넘어간다)

사용: python tools/check_tsv.py ["my files/tsv2"/*.tsv ...]
"""
import sys, os, glob, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from textio import encode, decode
from extract_text import repertoire, ISO, OUTDIR

FMT = re.compile(r'%[-0-9.]*[sdxXucf]')
CTRL = re.compile(r'\\x1F\\x[0-9A-F]{2}')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        head = f.readline().rstrip('\n').split('\t')
        for ln, line in enumerate(f, 2):
            line = line.rstrip('\n')
            if not line:
                continue
            v = line.split('\t')
            if len(v) != len(head):
                rows.append((ln, None, '열 개수가 %d 여야 하는데 %d' % (len(head), len(v))))
                continue
            rows.append((ln, dict(zip(head, v)), None))
    return rows


def main(paths):
    font = Font(os.path.join(ISO, 'DATAAPP.BIN'))
    rep = repertoire(font)
    src = {}
    for n in ('DATASCR.BIN', 'SSCR.BIN', '1NOSDC.BIN'):
        src[n] = open(os.path.join(ISO, n), 'rb').read()

    errs = collections.Counter()
    n_rows = n_done = 0
    problems = []

    def bad(path, ln, kind, msg):
        errs[kind] += 1
        if len(problems) < 60:
            problems.append('%s:%d [%s] %s' % (os.path.basename(path), ln, kind, msg))

    for path in paths:
        for ln, r, err in load(path):
            if err:
                bad(path, ln, '형식', err); continue
            n_rows += 1
            off = int(r['offset'], 16)
            budget = int(r['budget'])
            raw = src[r['file']][off:off + budget]
            try:
                if encode(r['jp']) != raw:
                    bad(path, ln, '원본불일치', r['id'])
            except Exception as e:
                bad(path, ln, '원본해석불가', '%s %s' % (r['id'], e))
            kr = r['kr'].strip()
            if not kr:
                continue
            n_done += 1
            try:
                kb = encode(kr)
            except Exception as e:
                bad(path, ln, '이스케이프오류', '%s %s' % (r['id'], e)); continue
            # 그릴 수 없는 문자
            miss = sorted({c for c in re.sub(r'\\x[0-9A-Fa-f]{2}|\\n|\\t|\\\\', '', kr)
                           if not ('가' <= c <= '힣') and c not in rep})
            if miss:
                bad(path, ln, '글자없음', '%s %r' % (r['id'], ''.join(miss)))
            # 매크로·서식 보존
            if r['jp'].count('＠') != kr.count('＠'):
                bad(path, ln, '＠누락', r['id'])
            if FMT.findall(r['jp']) != FMT.findall(kr):
                bad(path, ln, '서식불일치', '%s %r -> %r' % (r['id'], FMT.findall(r['jp']), FMT.findall(kr)))
            if CTRL.findall(r['jp']) != CTRL.findall(kr):
                bad(path, ln, '제어열불일치', r['id'])
            # 줄 수
            if kr.count('\\n') > r['jp'].count('\\n'):
                bad(path, ln, '줄수증가', '%s %d -> %d' % (r['id'], r['jp'].count('\\n'), kr.count('\\n')))
            # 예산 (참고용 경고)
            if len(kb) > budget:
                bad(path, ln, '예산초과', '%s %dB -> %dB (+%d)' % (r['id'], budget, len(kb), len(kb) - budget))

    print('행 %d개 / 번역됨 %d개' % (n_rows, n_done))
    if not errs:
        print('문제 없음')
        return 0
    for k, v in errs.most_common():
        print('  %-12s %d건' % (k, v))
    print()
    for p in problems:
        print('   ' + p)
    return 1


if __name__ == '__main__':
    args = sys.argv[1:] or sorted(glob.glob(os.path.join(OUTDIR, '*.tsv')))
    sys.exit(main(args))
