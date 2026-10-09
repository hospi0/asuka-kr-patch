# -*- coding: utf-8 -*-
"""용어·명사·이름 통일 점검 (2026-10-09) — tsv2 를 읽기만 한다.
  ① 이름표 기준: 04_몬스터·05_아이템명 의 (원문 → 번역) 를 표준으로, 원문에 그 이름이 든 다른 행의 번역에 표준 이름(띄어쓰기 무시)이 없으면 보고
  ② 가타카나 낱말: 원문 가타카나(3자↑)마다 번역에서 옮긴 꼴 모으기(가나→한글 어림 표기와 가장 닮은 낱말) — 두 가지 이상이면 보고
  ③ 첫소리 거센/된/예사소리만 다른 낱말 쌍(가에데/카에데 꼴)
  python tools/termcheck.py → work/termcheck.txt"""
import collections, difflib, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BS = chr(92)
ESC = re.compile(re.escape(BS) + r'(x[0-9A-Fa-f]{2}|n|t|r|' + re.escape(BS) + ')')
PRE = re.compile(r'^((?:' + re.escape(BS) + r'x[0-9A-Fa-f]{2}|[×XpLＸ])*)')
JOSA = sorted(['이', '가', '을', '를', '은', '는', '의', '와', '과', '도', '만', '에', '에게', '한테', '께', '로', '으로', '에서', '부터',
               '까지', '이랑', '랑', '하고', '야', '아', '여', '님', '씨', '짱', '이야', '이다', '다', '처럼', '보다', '라고', '이라고',
               '라는', '이라는', '들', '나', '이나', '든', '이든', '요'], key=len, reverse=True)


def rows():
    for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv2', '*.tsv'))):
        cat = os.path.basename(p)[:2]
        for ln in open(p, encoding='utf-8').read().split('\n')[1:]:
            c = ln.split('\t')
            if len(c) >= 7 and c[6]:
                yield cat, c


def clean(s):
    return ESC.sub('', s).replace('　', ' ')


def stem(w):
    for j in JOSA:
        if len(w) > len(j) + 1 and w.endswith(j):
            return w[:-len(j)]
    return w


def check_names(R, out):
    std = {}
    for cat, c in R:
        if cat in ('04', '05'):
            jp = PRE.sub('', clean(c[5])).strip(); kr = PRE.sub('', clean(c[6])).strip()
            if len(jp) >= 2 and kr and '\n' not in jp:
                std.setdefault(jp, collections.Counter())[kr] += 1
    std = {j: k.most_common(1)[0][0] for j, k in std.items()}
    keys = sorted(std, key=len, reverse=True)
    miss = collections.defaultdict(list)
    for cat, c in R:
        if cat in ('04', '05'):
            continue
        jp = clean(c[5]).replace('\n', ''); kr = clean(c[6]).replace(' ', '')
        used = set()
        for j in keys:
            if j in jp and not any(j in u for u in used):
                used.add(j)
                if std[j].replace(' ', '') not in kr:
                    miss[j].append((c[0], c[6][:60]))
    out.append('■ ① 이름표 기준 — 원문에 이름이 있는데 번역에 표준 이름이 없는 행 (이름 %d개 중 %d개)' % (len(std), len(miss)))
    for j, L in sorted(miss.items(), key=lambda x: -len(x[1])):
        out.append('  %s = «%s»  %d행' % (j, std[j], len(L)))
        for i, t in L[:4]:
            out.append('      %s  %s' % (i, t))


K = dict(zip('アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ',
             '아이우에오카키쿠케코사시스세소타치츠테토나니누네노하히후헤호마미무메모야유요라리루레로와오ㄴ가기구게고자지즈제조다지즈데도바비부베보파피푸페포부'))
SMALL = {'ャ': '야', 'ュ': '유', 'ョ': '요', 'ァ': '아', 'ィ': '이', 'ゥ': '우', 'ェ': '에', 'ォ': '오'}


def kana2hangul(w):
    out = ''
    for ch in w:
        if ch == 'ン' and out:
            o = ord(out[-1]) - 0xAC00
            if 0 <= o < 11172 and o % 28 == 0:
                out = out[:-1] + chr(ord(out[-1]) + 4); continue
        if ch in 'ッー・':
            continue
        if ch in SMALL and out:
            o = ord(out[-1]) - 0xAC00
            if 0 <= o < 11172:
                v = (ord(SMALL[ch]) - 0xAC00) % 588 // 28
                out = out[:-1] + chr(0xAC00 + (o // 588) * 588 + v * 28); continue
        out += K.get(ch, '')
    return out


def jamo(s):
    r = []
    for ch in s:
        o = ord(ch) - 0xAC00
        if 0 <= o < 11172:
            r += [o // 588, 100 + (o % 588) // 28, 200 + o % 28]
    return r


def check_katakana(R, out):
    m = collections.defaultdict(collections.Counter); ex = {}
    for cat, c in R:
        toks = [stem(w) for w in re.findall('[가-힣]+', clean(c[6]))]
        for W in set(re.findall('[ァ-ヺー・]{3,}', clean(c[5]))):
            W = W.strip('ー・'); exp = kana2hangul(W)
            if len(exp) < 2:
                continue
            best = max(((difflib.SequenceMatcher(None, jamo(exp), jamo(x)).ratio(), x) for x in toks), default=(0, ''))
            if best[0] >= 0.62:
                m[W][best[1]] += 1; ex.setdefault((W, best[1]), c[0])
    out.append('■ ② 가타카나 낱말 — 번역 꼴이 둘 이상 (꼴별 횟수 · 예 ID)')
    for W, cnt in sorted(m.items(), key=lambda x: -sum(x[1].values())):
        forms = [f for f in cnt if not any(f != g and f.startswith(g) for g in cnt)]   # 접두 꼴(조사 붙은 것) 정리
        if len(cnt) > 1 and sum(cnt.values()) >= 2:
            out.append('  %s  ' % W + ' / '.join('%s(%d,%s)' % (f, n, ex[(W, f)]) for f, n in cnt.most_common()))


G = {0: 0, 1: 0, 15: 0, 3: 3, 4: 3, 16: 3, 7: 7, 8: 7, 17: 7, 12: 12, 13: 12, 14: 12, 9: 9, 10: 9}


def key(w):
    out = []
    for ch in w:
        o = ord(ch) - 0xAC00
        out.append((G.get(o // 588, o // 588), (o % 588) // 28, o % 28) if 0 <= o < 11172 else ch)
    return tuple(out)


def check_variants(R, out):
    words = collections.Counter(); ex = {}; kata = collections.Counter()
    for cat, c in R:
        hk = bool(re.search('[ァ-ヺ]{2,}', c[5]))
        for w in re.findall('[가-힣]+', clean(c[6])):
            s = stem(w)
            if len(s) >= 3:
                words[s] += 1; ex.setdefault(s, c[0]); kata[s] += hk
    groups = collections.defaultdict(set)
    for w in words:
        groups[key(w)].add(w)
    out.append('■ ③ 첫소리만 다른 낱말 쌍(3글자↑, 원문 가타카나 줄)')
    for ws in sorted(groups.values(), key=lambda s: -sum(words[w] for w in s)):
        if len(ws) > 1 and any(kata[w] for w in ws):
            out.append('  ' + ' / '.join('%s(%d,%s)' % (w, words[w], ex[w]) for w in sorted(ws, key=lambda w: -words[w])))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = list(rows()); out = []
    check_names(R, out); out.append(''); check_katakana(R, out); out.append(''); check_variants(R, out)
    open(os.path.join(ROOT, 'work', 'termcheck.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
