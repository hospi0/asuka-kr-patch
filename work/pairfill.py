# -*- coding: utf-8 -*-
"""아이템 이름 쌍 경계 옮기기 반영(2026-10-09) — 칸 때문에 줄였던 한자 이름(표시용)을 정식 이름으로,
   히라가나 이름 칸도 같은 이름으로(합계 바이트 안에서). 앞머리 제어 코드는 그대로 둔다.
   python work/pairfill.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92)
PRE = re.compile('^(?:' + re.escape(BS) + 'x[0-9A-Fa-f]{2}|' + re.escape(BS) + 't|[×XpLＸZ\\[^:5O])*')
# id: 이름(앞머리 빼고)
NEW = {
    'SYS01069': '강검 만지카브라',
    'SYS01093': '켄고의 카타나',
    'SYS01157': '메아리의 방패', 'SYS01158': '메아리의 방패',
    'SYS01167': '지뢰 나바리의 방패', 'SYS01168': '지뢰나바리방패',
    'SYS01170': '토도방패',
    'SYS01199': '황천무녀신의 방패', 'SYS01200': '황천무녀신의 방패',
    'SYS01247': '백발백중의 팔찌', 'SYS01248': '백발백중의 팔찌',
    'SYS01251': '받아넘기기의 팔찌', 'SYS01252': '받아넘기기의 팔찌',
    'SYS01270': '파코렙킨의 팔찌',
    'SYS01302': '쇠화살',
    'SYS01309': '독화살',
    'SYS01315': '통나무',
    'SYS01372': '꾸불꾸불초', 'SYS01388': '도약초', 'SYS01398': '효험초',
    'SYS01408': '미끌미끌초', 'SYS01412': '흐물흐물초',
    'SYS01429': '폭수족자',                       # 시험 이름 되돌림
    'SYS01556': '가위눌림봉',
    'SYS01749': '황금의 구르는 돌', 'SYS01750': '황금의 구르는 돌',
    'SYS01753': '썩지 않는 주먹밥', 'SYS01754': '썩지않는주먹밥',
    'SYS01755': '지혜의 봉', 'SYS01756': '지혜의 봉',
    'SYS01759': '운명의 뿔피리', 'SYS01760': '운명의 뿔피리',
}
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '05_*.tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) >= 7 and c[0] in NEW:
            pre = re.match('^[^가-힣]*', c[6]).group(0)   # 앞머리 = 첫 한글 앞까지(제어 코드·×)
            new = pre + NEW[c[0]]
            if new != c[6]:
                print(c[0], c[3], repr(c[6]), '→', repr(new)); c[6] = new; L[k] = '\t'.join(c); ch = True; n += 1
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(n, '행')
