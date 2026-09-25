# -*- coding: utf-8 -*-
"""본 빌더 — `my files/tsv2/*.tsv` 전량을 «구간 단위»로 재조립해 디스크에 기록한다.

## 왜 «구간»인가
PoC #2(docs/02_poc2.md)가 실기로 증명한 것: 메시지마다 원본 길이를 맞출 필요는 없고
**재조립 구간의 총 바이트만 보존**하면 된다. 구간 밖 주소가 하나도 안 움직이기 때문이다.

세션3(2026-08-28) 에 그 전제를 전 파일로 검증했다 — `work/ptrscan.txt`:
  DATASCR/SSCR 어디에도 «메시지 시작을 가리키는 포인터 테이블»이 없다
  (u32 오름차순 런의 값이 메시지 시작과 일치한 건 0/9·0/8, 단발 매칭 22·26건은 노이즈).
그래서 구간을 나누는 유일한 실제 제약은 **SSCR 섹션 경계**뿐이다.

## 자원 정책 (사용자 지시 2026-08-28)
**한자 칸만** 한글로 덮는다. 가나·기호·라틴 칸은 나중에 쓸지 모르니 보존한다.
  한자 2,189칸 vs 필요 음절 1,135개 → 여유 1,054칸. 차고 넘친다.

## 예산
구간이 남으면 «반각 공백»으로 채운다. 넘치면 인접 메시지를 끌어들여 여유를 빌리고,
그래도 안 되면 **에러로 보고**한다(조용히 자르지 않는다).

사용: python tools/build_all.py            # 미리보기 (자동 범위)
      python tools/build_all.py --write    # 디스크 기록 (★매번 사람 허락)
"""
import sys, os, re, json, shutil, argparse, collections, struct, subprocess, filecmp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font
from mkglyph import render
from charmap import CharMap, kanji_pool, corpus_usage, ks_syllables, syl_rank
from msgscan import messages
from extract_text import repertoire, ISO, OUTDIR, sscr_sections
from check_tsv import load as load_tsv
from discwrite import TrackWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_DIR = r"C:\claude\roms\dc\Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan (Japan)"
BASE = "Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan! (Japan)"
BUILD = os.path.join(ROOT, 'build', 'kr')

TRACK5_START_LBA, TRACK5_SKIP = 140708, 225
# ★`tools/iso_list.py` 가 뽑은 ISO9660 익스텐트 LBA.
#   ⚠빠진 파일은 «경고만 내고 건너뛴다» — SSCR 이 빠지면 도감·UI 가 통째로 원문으로 남는다.
LBA = {'DATAAPP.BIN': 492080, 'DATASCR.BIN': 164129,
       'SSCR.BIN': 494158, '1NOSDC.BIN': 548051,
       'DATASZU.BIN': 144921,     # 구운 그림(상태바·이름입력 라벨)
       'DATAIDA.BIN': 150689,     # 구운 그림(오프닝 나레이션 OPfont_*)
       'DATABG.BIN': 145004}      # 지명판·던전 이름표 (LZ40 컨테이너)
FONT_NAME = 'nanumb'
PAD = 0x20                      # 반각 공백 — 구간 잔여 바이트 채움
# 여유를 빌리려고 끌어들일 인접 메시지 최대 개수.
# ★간격이 2B(NUL+opcode)인 «순수 문자열 풀»에서만 병합하므로 개수를 늘려도 위험이
#   달라지지 않는다(수치 레코드는 MAX_GAP 이 막는다). 8 -> 32 로 올려 도감처럼
#   «분류 총량은 남는데 국소적으로만 넘치는» 구간을 흡수한다. 32 이상은 이득이 거의 없다.
#   ⚠SSCR 는 실기 미검증이다(PoC#2 는 DATASCR). 「메시지 시작을 가리키는 오프셋이
#     없다」는 스캔 결과에 기대고 있으니, 실기에서 도감·UI 를 반드시 눈으로 볼 것.
# ⛔⛔**2026-08-29 실기로 뒤집혔다 — 병합은 하지 않는다.**
#   금방패 효과가 「게 된다」로 떴다. 빌드 결과를 «원본 오프셋»으로 읽어 보니
#   0x63D7B 가 빈 문자열, 0x63D8A 가 「恵郷」… 즉 **SSCR 문자열은 절대 오프셋으로
#   읽힌다.** 앞 문자열이 길어져 뒤가 밀리면 게임은 문장 «중간»부터 읽는다.
#   「메시지 시작을 가리키는 u32 테이블이 없다」는 스캔 결과는 반증이 못 됐다 —
#   주소를 코드가 «만들어» 쓰면 표가 없어도 절대 오프셋이다.
#   다행히 병합을 꺼도 DATASCR·1NOSDC 는 초과 0행, SSCR 만 494행이 넘쳤고
#   그건 축약 단계가 처리한다. 이득이 없으니 전 파일에서 끈다.
MAX_MERGE = 1
MAX_GAP = 2                     # ★넘어도 되는 «메시지 사이 간격» 상한 (수치 레코드 보호)

BS = chr(0x5c)
ESC = re.compile(r'\\x[0-9A-Fa-f]{2}|\\n|\\t|\\\\')

# 콘솔이 cp949 라 한글/약물이 그대로 안 나간다 — 리포트는 파일로 남기고 화면엔 같이 흘린다.
REPORT = os.path.join(ROOT, 'work', 'build_report.txt')
_lines = []


def say(s=''):
    _lines.append(s)
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', 'replace').decode('ascii'))


def flush_report():
    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(_lines) + '\n')


# ---------------------------------------------------------------- 번역표 읽기
def read_rows():
    """my files/tsv2/*.tsv -> 파일별 행 목록 (오프셋 순)."""
    per = collections.defaultdict(list)
    for fn in sorted(os.listdir(OUTDIR)):
        if not fn.endswith('.tsv'):
            continue
        for ln, r, err in load_tsv(os.path.join(OUTDIR, fn)):
            if err:
                raise SystemExit('%s:%d 형식 오류 — %s' % (fn, ln, err))
            r['_src'] = '%s:%d' % (fn, ln)
            r['_cat'] = fn.rsplit('_', 1)[0]
            per[r['file']].append(r)
    for k in per:
        per[k].sort(key=lambda r: int(r['offset'], 16))
    return per


def untranslated_chars(per):
    """★번역하지 않고 원문 그대로 두는 행이 «아직 가리키는» 문자 — 칸을 예약해야 한다.
    [[feedback_reserve_fnt_slots_of_untranslated]]"""
    keep = set()
    n = 0
    for rows in per.values():
        for r in rows:
            if r['kr'].strip():
                continue
            n += 1
            keep.update(ESC.sub('', r['jp']))
    return keep, n


# ---------------------------------------------------------------- 구간 나누기
def barriers(name, data):
    """구간이 절대 넘어서면 안 되는 오프셋 집합."""
    b = set()
    if name == 'SSCR.BIN':
        # 섹션 테이블(u32 sid, u32 off)이 절대 오프셋을 담는다 — 섹션 경계는 못 넘는다
        for sid, off in sscr_sections(data):
            b.add(off)
    return b


def plan_regions(rows, data, name, cm, max_gap=MAX_GAP, max_merge=MAX_MERGE):
    """(구간) 목록을 만든다. 각 구간은 총 바이트가 원본과 «정확히» 같다.

    구간 = 연속한 메시지 몇 개 + 그 사이 원본 바이트(VM 명령).
    단독으로 예산에 들어가면 단독 구간, 넘치면 뒤 메시지를 끌어들여 여유를 빌린다.

    ★★병합 한도 `max_gap` — 메시지 사이 간격 안에 «수치 레코드»가 있으면 넘지 않는다.
      세션3 실측(work/gapdump.txt): 04_몬스터 73/51 B 간격 = 몬스터 능력치 u16 블록,
      05_아이템명 33 B 간격 = 아이템 수치 블록. 이걸 넘어 병합하면 뒤 메시지가 밀리면서
      수치 블록도 같이 밀려 «글자는 멀쩡한데 게임 규칙이 죽는다».
      [[feedback_field_width_from_reference_patch_columns]]
      작은 간격(1~2 B = NUL + opcode 하나)만 문자열 풀로 보고 병합한다.
    """
    bar = barriers(name, data)
    out, errs = [], []
    seen_err = set()

    def note(kind, r, msg):
        k = (kind, r['id'])
        if k in seen_err:            # 병합 재시도마다 같은 행이 다시 걸린다 — 한 번만
            return
        seen_err.add(k)
        errs.append((kind, r, msg))

    i = 0
    while i < len(rows):
        j = i
        while True:
            start = int(rows[i]['offset'], 16)
            end = int(rows[j]['offset'], 16) + int(rows[j]['budget'])
            # 구간 내용 = [kr_i][gap][kr_i+1][gap]...[kr_j]
            body = bytearray()
            for k in range(i, j + 1):
                r = rows[k]
                off, bud = int(r['offset'], 16), int(r['budget'])
                kr = r['kr'].strip()
                try:
                    body += cm.encode_tsv(kr) if kr else data[off:off + bud]
                except KeyError as e:
                    note('인코딩누락', r, repr(e.args[0]))
                    body += data[off:off + bud]
                if k < j:
                    body += data[off + bud:int(rows[k + 1]['offset'], 16)]   # 원본 보존
            need = end - start
            if len(body) <= need:
                out.append(dict(start=start, end=end, rows=rows[i:j + 1],
                                body=bytes(body), slack=need - len(body)))
                break
            # 넘친다 — 다음 메시지를 끌어들여 여유를 빌릴 수 있는가?
            gap = (int(rows[j + 1]['offset'], 16) - end) if j + 1 < len(rows) else None
            if (gap is None or gap > max_gap or j - i + 1 >= max_merge
                    or int(rows[j + 1]['offset'], 16) in bar):
                note('예산초과', rows[i], '%dB 필요, %dB 가능 (+%d)%s'
                     % (len(body), need, len(body) - need,
                        '' if gap is None else ('  [다음 간격 %dB]' % gap)))
                out.append(dict(start=start, end=end, rows=rows[i:j + 1],
                                body=bytes(body[:need]), slack=0, over=True))
                break
            j += 1
        i = j + 1
    return out, errs


_MARK = ''          # 사용자 영역 — 진짜 백슬래시를 잠시 대신한다


def text_lines(s):
    """TSV 표기를 «화면 줄» 단위로 쪼갠다.

    ⚠순서가 중요하다. `\\\\`(진짜 백슬래시)를 먼저 치워야 그 뒤의 n 을 개행으로
      잘못 읽지 않고, 개행으로 «쪼갠 뒤»에 나머지 이스케이프를 지워야 한다.
      (지우고 나서 쪼개면 줄이 하나로 뭉쳐 상한이 통째로 틀린다.)
    """
    s = s.replace(BS + BS, _MARK)
    return [ESC.sub('', p).replace(_MARK, BS) for p in s.split(BS + 'n')]


def line_limits(per):
    """분류별 «원본이 실제로 쓰는 줄 폭»(반칸). 고정폭이라 한 글자가 2반칸.
    추정하지 말고 실측한다 [[feedback_screen_limits_measure_not_derive]].

    ★★«최대»가 아니라 «3줄 이상 나타나는 최대»를 쓴다.
      01_대사 의 44반칸(22칸)은 **원문 전체에서 딱 한 줄**뿐이고, 그 22번째 칸은
      실기에서 대사창 테두리 위로 삐져나온다(2026-08-28 스샷 실측). 단발 이상치를
      상한으로 삼으면 번역문 전체가 그만큼 넘치게 된다.
      2등 폭은 42반칸 10줄 — 그게 진짜 창 폭이다.
    """
    w = collections.defaultdict(collections.Counter)
    for rows in per.values():
        for r in rows:
            for ln in text_lines(r['jp']):
                w[r['_cat']][len(ln) * 2] += 1          # 고정폭 — 한 글자 한 칸
    lim = {}
    for cat, hist in w.items():
        total = sum(hist.values())
        # ★★「3줄 이상」으로는 부족했다 — 01_대사 는 42반칸(21칸)이 원문에 10줄뿐인데
        #   그걸 상한으로 잡는 바람에 번역문 278줄이 21칸이 됐고, 실기에서 마지막
        #   글자가 잘렸다(「네고로신사에선」의 «선», 2026-08-29).
        #   원문의 «주력 폭»은 40반칸(20칸) 310줄이다. 그래서 «전체의 2%」를 기준으로
        #   삼는다 — 소수 이상치는 건너뛰고 진짜 창 폭에서 멈춘다.
        need = 30 if total >= 300 else 3
        acc = 0
        for width in sorted(hist, reverse=True):
            acc += hist[width]
            lim[cat] = width
            if acc >= need:
                break
    return lim


def byte_cells(line):
    """SJIS 바이트열 한 줄의 화면 폭 (반칸 단위). 제어열은 0.

    ★★**이 게임의 렌더러는 고정폭이다 — 반각도 전각 «한 칸»을 먹는다.**
      2026-08-28 실기 스샷 픽셀 실측: 「　논이 위험하다면,」의 글자 x 를 칸폭 71.4 px·
      원점 116.6 px 로 예측하면 하 543/536 · 다 614/613 · 면 685/688 · , 756/759 로
      맞는다. **공백과 반각 쉼표를 각각 «한 칸»으로 세야** 맞아떨어진다.
      대사창은 21칸이고 22번째 칸은 테두리 위로 삐져나온다(반쯤 보인다).
      ⛔반각을 «반 칸»으로 세면 한 줄에 5~6칸씩 더 들어간다고 착각해 오른쪽이 잘린다.
    """
    n = i = 0
    while i < len(line):
        b = line[i]
        if b == 0x1f:                       # 인자 1바이트를 먹는 제어열
            i += 2; continue
        if b < 0x20 or b == 0x7f:
            i += 1; continue
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc:
            i += 2
        else:
            i += 1
        n += 2                              # 전각·반각 모두 한 칸
    return n


def pad_region(reg, limit=None):
    """구간 잔여 바이트를 «반각 공백»으로 채운다.

    ⛔⛔**NUL 로 채우면 안 된다 — 실기에서 타이틀 START 만 눌러도 크래시났다
      (2026-08-29).** 문자열은 VM 바이트코드 «안»에 박혀 있어서 구조가
      `[명령][본문][NUL][다음 명령]` 이다. 본문 뒤를 NUL 로 채우면 VM 이 문자열을
      일찍 끝내고 **남은 NUL 을 명령어로 실행**한다. 종단자는 «원래 자리»에
      있어야 하므로 채움 바이트는 반드시 «출력 가능한» 값이어야 한다.
    ★[[feedback_pad_before_trailing_control_code]] — 끝에 붙은 제어코드가 패딩을
      «인수»로 먹지 않게, 채움은 «끝의 제어 바이트 런» 앞에 넣는다.
    ⚠부작용: 이름처럼 `%s` 로 이어 붙는 문자열은 꼬리 공백이 화면에 보인다
      (「굴속 마무루␣␣␣를」). 그건 «번역을 예산에 꽉 채워» 없애야 한다.

    ★★★**채움을 «한 줄»에 몰아넣으면 그 줄이 창 폭을 넘어 크래시한다.**
      2026-08-30 실기: 두령「アイテム……ヨコセ……」 장면에서 바이오스로 떨어졌다.
      번역이 마지막 줄(「ウウ……」)을 통째로 빼먹어 남은 16 B 가 앞줄 끝에 몰렸고,
      그 줄이 「아이템……내놔……」 9칸 + 공백 16칸 = **25칸**이 됐다(상한 20칸).
      고정폭이라 반각 공백도 «한 칸»을 먹는다
      [[feedback_monospace_renderer_halfwidth_costs_full_cell]].
      ⇒ 줄마다 «남은 칸»만큼만 넣고, 뒷줄부터 채운다(꼬리 공백이 안 보이는 쪽).
        그래도 남으면 «넘침»으로 세어 빌드가 알려준다 — 조용히 넘기지 않는다.
    """
    slack = reg['slack']
    if slack <= 0:
        return reg['body'], 0
    b = bytes(reg['body'])

    def put(seg, n):
        """그 줄의 «끝 제어열 앞»에 공백 n 개를 넣는다"""
        t = len(seg)
        while t > 0 and (seg[t - 1] < 0x20 or seg[t - 1] == 0x7f):
            t -= 1
        return seg[:t] + bytes([PAD]) * n + seg[t:]

    if not limit or os.environ.get('PAD_OLD'):
        return put(b, slack), 0        # PAD_OLD=1 : 고치기 전 방식(비교용)

    segs = b.split(b'\n')
    add, left = [0] * len(segs), slack
    for i in range(len(segs) - 1, -1, -1):     # 뒷줄부터
        if left <= 0:
            break
        room = max(0, (limit - byte_cells(segs[i])) // 2)
        take = min(left, room)
        add[i] = take
        left -= take
    over = left
    if over:
        add[-1] += over                        # 어쩔 수 없는 나머지
    out = b'\n'.join(put(s, n) if n else s for s, n in zip(segs, add))
    return out, over


# ---------------------------------------------------------------- 빌드
def build(write=False):
    font = Font(os.path.join(ISO, 'DATAAPP.BIN'))
    rep = repertoire(font)
    per = read_rows()

    src = {n: open(os.path.join(ISO, n), 'rb').read()
           for n in ('DATASCR.BIN', 'SSCR.BIN', '1NOSDC.BIN')}

    # --- 1) 원본 대조: 표가 낡지 않았는가 -------------------------------
    stale = 0
    for name, rows in per.items():
        for r in rows:
            off, bud = int(r['offset'], 16), int(r['budget'])
            if len(src[name][off:off + bud]) != bud:
                stale += 1
    if stale:
        raise SystemExit('원본 범위를 벗어난 행 %d개 — 번역표를 다시 뽑아야 한다' % stale)

    # --- 2) 글리프 칸 배정 ---------------------------------------------
    keep, n_keep = untranslated_chars(per)
    use = corpus_usage(font)
    reserved = {font.index[c] for c in keep if c in font.index}
    pool = kanji_pool(font, reserved=reserved, use=use, order='index')

    syl = collections.Counter()
    for rows in per.values():
        for r in rows:
            kr = r['kr'].strip()
            if kr:
                syl.update(c for c in ESC.sub('', kr) if '가' <= c <= '힣')

    # ★남는 한자 칸까지 «KS X 1001 2,350자»로 채운다.
    #   이름입력 漢字 페이지가 폰트 문자표를 SJIS 순으로 훑으므로, 칸을 오름차순으로
    #   두고 음절을 가나다순으로 배정하면 그 화면이 «받침까지 되는 한글 음절표»가 된다.
    #   그래야 「김」「박」 같은 이름을 넣을 수 있다(かな 페이지 120칸으론 불가능).
    must = set(syl)
    room = len(pool) - len(must)
    if room < 0:
        raise SystemExit('한자 칸 %d개 < 필요 음절 %d개' % (len(pool), len(must)))
    extra = sorted((c for c in ks_syllables() if c not in must), key=syl_rank)
    order = sorted(must | set(extra[:room]))
    cm = CharMap(font, pool=pool)
    cm.assign(order)

    say('■ 글리프')
    say('   미번역 %d행이 쓰는 문자 %d종 -> 예약 칸 %d개' % (n_keep, len(keep), len(reserved)))
    say('   한자 풀 %d칸 = 본문에 쓰는 음절 %d개 + 이름입력용 여분 %d개 (남는 칸 %d)'
          % (len(pool), len(must), len(order) - len(must), len(cm.pool)))
    free = sum(1 for i in pool if use[font.chars[i]] == 0)
    say('   «원문 미사용» %d칸, 원문이 쓰는 칸 %d개를 덮음' % (free, len(pool) - free))
    say('   이름입력 漢字 페이지 = 가나다순 한글 %d자 (받침 포함)' % len(order))

    # --- 3) 구간 계획 ----------------------------------------------------
    say('\n■ 구간 재조립')
    plans, all_errs = {}, []
    for name in ('DATASCR.BIN', 'SSCR.BIN', '1NOSDC.BIN'):
        rows = per.get(name, [])
        if not rows:
            continue
        regs, errs = plan_regions(rows, src[name], name, cm)
        plans[name] = regs
        all_errs += [(name,) + e for e in errs]
        merged = sum(1 for r in regs if len(r['rows']) > 1)
        slack = sum(r['slack'] for r in regs)
        say('   %-12s 행 %5d -> 구간 %5d개 (병합 %4d개)  잔여 %6d B'
              % (name, len(rows), len(regs), merged, slack))

    # --- 4) 검증 ---------------------------------------------------------
    kinds = collections.Counter(e[1] for e in all_errs)
    say('\n■ 검증')
    if kinds:
        for k, v in kinds.most_common():
            say('   %-10s %d건' % (k, v))
    else:
        say('   문제 없음')

    log = os.path.join(ROOT, 'work', 'build_errors.txt')
    with open(log, 'w', encoding='utf-8') as fh:
        for name, kind, r, msg in all_errs:
            fh.write('%s\t%s\t%s\t%s\t%s\n' % (kind, name, r['id'], r['_src'], msg))
            fh.write('   jp=%r\n   kr=%r\n' % (r['jp'], r['kr']))
    say('   상세 -> %s' % log)

    # 패딩 통계 (화면 밖으로 밀려나는지 판정용)
    pads = [r['slack'] for regs in plans.values() for r in regs if r['slack'] > 0]
    if pads:
        pads.sort()
        say('   패딩: %d구간, 중앙값 %dB, 최대 %dB' % (len(pads), pads[len(pads) // 2], pads[-1]))

    if kinds.get('인코딩누락'):
        raise SystemExit('\n★인코딩 누락은 빌드 에러다 — 위 로그의 문자를 폰트에 있는 것으로 고칠 것')

    # --- 5) 글리프 굽기 --------------------------------------------------
    for s, idx in cm.map.items():
        font.set_cell(idx, render(s, name=FONT_NAME))
        font.set_width(idx, 0, 25)

    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    cm.snapshot(os.path.join(ROOT, 'data', 'charmap_build.json'))

    # --- 6) 파일 이미지 만들기 -------------------------------------------
    #   패딩은 «줄 폭이 남는 줄»에 나눠 넣는다. 상한은 원본 실측값(분류별 최대 줄 폭).
    limits = line_limits(per)
    outbin, forced = {}, 0
    extra_ok = {}          # 구간 계획 밖이지만 «의도된» 변경 (코드 패치 등)
    for name, regs in plans.items():
        d = bytearray(src[name])
        for reg in regs:
            new, over = pad_region(reg, limits.get(reg['rows'][-1]['_cat']))
            forced += 1 if over else 0
            assert len(new) == reg['end'] - reg['start'], (name, hex(reg['start']))
            d[reg['start']:reg['end']] = new
        assert len(d) == len(src[name]), name
        outbin[name] = bytes(d)
    say('   패딩: 반각 공백 (VM 이 종단자를 원자리에서 읽어야 한다)%.0s' % forced)

    # --- 6.5) 구운 그림 (DATASZU.BIN) — 상태바·이름입력 라벨 -------------
    #   ★텍스트가 아니라 «아틀라스 픽셀»을 고친다. 구간 검증 대상이 아니므로
    #     여기서 따로 만들어 outbin 에 넣는다.
    import gfx_name
    from gfx_szu import Atlas
    szu = bytearray(open(os.path.join(ISO, 'DATASZU.BIN'), 'rb').read())
    src['DATASZU.BIN'] = bytes(szu)
    sysat = Atlas(szu, 'system')
    # ★테두리 2px — 원본 階 는 y5-31(27px)인데 1px 로 그리면 23px 라 옆 Lv·HP 보다
    #   작고 얇아 보인다(사용자 지적 + 색인맵 실측 2026-08-29).
    sysat.draw_text('층', 64, 5, 90, 31, fill=6, outline=1, ow=2)   # 상태바 「階」
    sysat.write_back()
    gfx_name.apply(szu)                                          # 이름입력 라벨
    outbin['DATASZU.BIN'] = bytes(szu)
    n_gfx = sum(1 for a, b in zip(szu, src['DATASZU.BIN']) if a != b)
    say('\n■ 구운 그림')
    say('   DATASZU.BIN  변경 %d B — 상태바 「층」 + 이름입력 라벨 7종' % n_gfx)

    # ★오프닝 나레이션 — 512x512 4bpp 텍스처 6장(OPfont_*). 이것도 «구운 그림»이라
    #   디스크 어디에도 SJIS 로 없다. 제자리에서 고치므로 오프셋은 안 밀린다.
    import gfx_op
    ida = bytearray(open(os.path.join(ISO, 'DATAIDA.BIN'), 'rb').read())
    src['DATAIDA.BIN'] = bytes(ida)
    gfx_op.apply(ida)
    outbin['DATAIDA.BIN'] = bytes(ida)
    n_op = sum(1 for a, b in zip(ida, src['DATAIDA.BIN']) if a != b)
    say('   DATAIDA.BIN  변경 %d B — 오프닝 나레이션 6화면' % n_op)

    # ★지명판·던전 이름표 — `DATABG_rebuild.exe` 가 만든 컨테이너를 그대로 싣는다.
    #   ⚠재빌더 산출물은 «추출기로 되읽기»가 안 된다(무수정 왕복도 마찬가지).
    #     0x34 LZ40 변종을 우리 도구로 못 풀어 내용 검증을 못 했다 — 실기 확인 필요.
    #   원본 익스텐트 크기(1,490,944)에 맞춰 0 으로 패딩한 파일을 쓴다.
    bgp = os.path.join(ROOT, 'work', 'databg', 'DATABG_kr.bin')
    if os.path.exists(bgp):
        bg = open(bgp, 'rb').read()
        src['DATABG.BIN'] = open(os.path.join(ISO, 'DATABG.BIN'), 'rb').read()
        if len(bg) == len(src['DATABG.BIN']):
            outbin['DATABG.BIN'] = bg
            # ★★재빌드한 DATABG 는 CUE LZ40(0x40) 이라 «해제 루틴 패치»가 없으면
            #   부팅이 안 된다. 한 짝이므로 여기서 반드시 같이 건다.
            import patch_1nosdc
            if '1NOSDC.BIN' not in outbin:
                raise SystemExit('1NOSDC.BIN 이 outbin 에 없다 — 패치를 걸 수 없다')
            outbin['1NOSDC.BIN'] = patch_1nosdc.apply(outbin['1NOSDC.BIN'])
            # ⛔src 는 «디스크 원본» 대조에 쓰이므로 절대 건드리지 말 것.
            #   건드리면 7)에서 「디스크 원본이 work 사본과 다르다」로 빌드가 죽는다.
            extra_ok.setdefault('1NOSDC.BIN', set()).update(
                range(*patch_1nosdc.region()))
            a, b2 = patch_1nosdc.region()
            say('   1NOSDC.BIN   LZ40 해제 루틴 패치 0x%X~0x%X (%d B)' % (a, b2, b2 - a))
            n_bg = sum(1 for a, b in zip(bg, src['DATABG.BIN']) if a != b)
            say('   DATABG.BIN   변경 %d B — 지명판 18 + 던전 이름표 105' % n_bg)
        else:
            say('   ⚠DATABG.BIN 크기 불일치 %d != %d — 건너뜀'
                % (len(bg), len(src['DATABG.BIN'])))
    else:
        say('   ⚠DATABG_kr.bin 없음 — 지명판 건너뜀')

    # --- 6.6) 모집단에서 빠진 «짧은 독립 문자열» ---------------------------
    # ★실기 2026-08-29: 「목화살**は**」 — 조사가 일본어로 남았다. `%sは` 는 NUL 로
    #   끝나는 4바이트 독립 문자열이라 추출기가 걸러버려 TSV 에 아예 없다.
    #   («조사 잔여 0행»인데 화면엔 일본어가 남는 지문이 이것이다)
    #   ⚠한글은 cp932 로 못 쓴다 — 반드시 «현재 빌드의 글리프 배정표»로 인코딩한다.
    import patch_missed
    n_ex = 0
    for fname, jp, kr in patch_missed.RULES:
        if fname not in outbin:
            continue
        old = jp.encode('cp932') + b'\x00'
        new = cm.encode_tsv(kr) + b'\x00'
        if len(new) != len(old):
            say('   ⚠추가문자열 길이 불일치 %s: %d != %d — 건너뜀'
                % (kr, len(new), len(old)))
            continue
        d = bytearray(outbin[fname])
        i = 0
        while True:
            i = d.find(old, i)
            if i < 0:
                break
            d[i:i + len(old)] = new
            extra_ok.setdefault(fname, set()).update(range(i, i + len(old)))
            n_ex += 1
            i += len(old)
        outbin[fname] = bytes(d)
    if n_ex:
        say('   추가 문자열 %d곳 — 모집단 누락분(`%%sは` 등)' % n_ex)

    # ★최종 변경 검증 — 바뀐 바이트가 전부 «계획한 구간» 안인가
    for name, d in outbin.items():
        if name not in plans:          # 구운 그림 파일은 구간 계획이 없다
            continue
        planned = set()
        for reg in plans[name]:
            planned.update(range(reg['start'], reg['end']))
        planned.update(extra_ok.get(name, ()))
        stray = [k for k in range(len(d)) if d[k] != src[name][k] and k not in planned]
        if stray:
            raise SystemExit('%s: 계획 밖 변경 %d바이트 (%#x…)' % (name, len(stray), stray[0]))
        say('   %-12s 변경 %6d B / %d B (계획 밖 0)'
              % (name, sum(1 for k in range(len(d)) if d[k] != src[name][k]), len(d)))

    if not write:
        say('\n[미리보기] 실제 디스크 쓰기는 --write')
        return font, cm, outbin

    # --- 7) 디스크 기록 ---------------------------------------------------
    os.makedirs(BUILD, exist_ok=True)
    for n in (1, 2, 3, 4, 5):
        s = os.path.join(ROM_DIR, '%s (Track %d).bin' % (BASE, n))
        t = os.path.join(BUILD, os.path.basename(s))
        # ★track5 는 «매번» 원본에서 새로 받는다. 패치본 위에 또 쓰면 아래 원본 대조가
        #   걸려 빌드가 죽는다(크기가 같아서 「있으면 넘어가기」로는 못 걸러낸다).
        if n == 5 or not os.path.exists(t) or os.path.getsize(t) != os.path.getsize(s):
            say('   복사 track%d ...' % n)
            shutil.copyfile(s, t)
    shutil.copyfile(os.path.join(ROM_DIR, '%s.cue' % BASE), os.path.join(BUILD, '%s.cue' % BASE))

    t5 = TrackWriter(os.path.join(BUILD, '%s (Track 5).bin' % BASE), TRACK5_START_LBA, TRACK5_SKIP)
    assert t5.read_user(LBA['DATAAPP.BIN'], 0, 4) == b'SDRV'
    t5.write_user(LBA['DATAAPP.BIN'], 0, bytes(font.buf))
    for name, d in outbin.items():
        if name not in LBA:
            say('   ⚠ %s 는 LBA 미확정 — 건너뜀' % name)
            continue
        if t5.read_user(LBA[name], 0, len(src[name])) != src[name]:
            raise SystemExit('%s: 디스크 원본이 work 사본과 다르다 — track5 가 이미 패치본' % name)
        t5.write_user(LBA[name], 0, d)
    n = t5.close()
    say('\n기록 완료. EDC/ECC 재계산 섹터 %d개 -> %s' % (n, BUILD))
    make_xdelta(say)
    return font, cm, outbin


VERSION = '0.7'
XDELTA = r"C:\claude\utils\xdelta.exe"


def make_xdelta(say=print):
    """배포 패치를 «빌드할 때마다» 새로 뽑는다 (사용자 지시 2026-08-29).

    Track 5 만 바뀌므로 그 트랙 하나에 대한 델타다. 만든 뒤 «원본에 되적용»해
    빌드본과 바이트가 같은지 확인한다 — 깨진 패치를 배포하는 것보다 1분 더 쓰는 게 낫다.
    """
    src = os.path.join(ROM_DIR, '%s (Track 5).bin' % BASE)
    tgt = os.path.join(BUILD, '%s (Track 5).bin' % BASE)
    out = os.path.join(ROOT, 'asuka_kr_v%s.xdelta' % VERSION)
    if not os.path.exists(XDELTA):
        say('   ⚠xdelta.exe 없음 — 패치 생략')
        return
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, tgt, out], check=True)
    chk = os.path.join(ROOT, 'work', '_xd_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, out, chk], check=True)
    ok = filecmp.cmp(chk, tgt, shallow=False)
    os.remove(chk)
    say('   xdelta v%s  %d B  되적용 검증 %s -> %s'
        % (VERSION, os.path.getsize(out), '일치' if ok else '★불일치',
           os.path.basename(out)))
    if not ok:
        raise SystemExit('xdelta 되적용 결과가 빌드본과 다르다')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    try:
        build(ap.parse_args().write)
    finally:
        flush_report()
