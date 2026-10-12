# -*- coding: utf-8 -*-
"""붙여 쓴 곳 찾기 2 — «조사·어미 뒤에 바로 다음 낱말»만(제보 05~09, 2026-10-12).
  Kiwi 형태소: 앞 형태소가 J*/E*(지+않 포함) 이고 뒤가 체언·용언·부사·관형사 시작인데 원문에 공백이 없는 자리.
  C:/claude/utils/kiwi-venv/Scripts/python work/report/kiwi_scan2.py > work/report/kiwi_scan2.tsv
  열: id 파일 붙은곳수 예산 현재길이 jp kr 표시(붙은 자리에 ^)
"""
import glob, csv, re, sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blen import blen
from kiwipiepy import Kiwi
K = Kiwi()
BS = chr(92)
NAMES = set()
for p in glob.glob('my files/tsv2/*.tsv'):
    nm = os.path.basename(p).startswith(('04_', '05_', '11_'))
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) < 7 or r[0] == 'id': continue
        m = re.match(r'([가-힣＆＠ ]{2,12})「', r[6])
        if m: NAMES.update(w for w in re.split('[＆＠ ]', m.group(1)) if len(w) >= 2)
        if nm and len(r[6]) <= 14: NAMES.update(w for w in re.findall('[가-힣]{2,}', r[6]))
NAMES.update('팔마천 풍래인 두령 코우가 제래국 천륜국 흑뢰선녀 에레키상자 주먹밥 두루마리 기탄 사기 제기 리바 무라도 크론 기토 산주 라군 콧파 아스카 미나모 코요리 덴덴당 삼파성 백사도 칠천경 삼도천 여성풍래인 쿠노이치 수레꾼 마차꾼 레벨업 팔수신'.split())
for w in NAMES:
    try: K.add_user_word(w, 'NNP', 0)
    except Exception: pass
SEG = re.compile(r'[가-힣]+(?:[가-힣 ]*[가-힣])?')
CONTENT = ('NN', 'NP', 'NR', 'VV', 'VA', 'MA', 'MM', 'XR', 'SL', 'SN', 'IC')


def joins(text):
    """원문 공백 없이 붙은 «조사/어미 + 다음 낱말» 자리(문자 위치 목록)."""
    out = []
    for m in SEG.finditer(text):
        seg = m.group(0)
        try: toks = K.tokenize(seg)
        except Exception: continue
        for a, b in zip(toks, toks[1:]):
            if a.start + a.len != b.start: continue
            if seg[b.start - 1:b.start] == ' ' or seg[b.start:b.start + 1] == ' ': continue
            ta, tb = a.tag, b.tag
            ok = (ta.startswith('J') or ta.startswith('E')) and (tb.startswith(CONTENT) or (a.form == '지' and tb.startswith('VX') and b.form in ('않', '못', '말')))
            if ta == 'ETN' or b.form in ('하', '되', '시'): ok = False
            if ok: out.append(m.start() + b.start)
    return out


if __name__ == '__main__':
    n = 0
    for p in sorted(glob.glob('my files/tsv2/*.tsv')):
        for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
            if len(r) < 7 or r[0] == 'id' or not r[3].isdigit() or not re.search('[가-힣]', r[6]): continue
            kr = r[6]
            plain = re.sub(re.escape(BS) + r'x[0-9A-Fa-f]{2}', lambda m: '\x00' * 4, kr).replace(BS + 'n', '\x00\x00')
            js = joins(plain)
            if not js: continue
            mark = ''.join(('^' if i in js else '') + c for i, c in enumerate(kr))
            n += 1
            print('\t'.join([r[0], os.path.basename(p)[:-4], str(len(js)), r[3], str(blen(kr)), r[5], kr, mark]))
    print('#', n, file=sys.stderr)
