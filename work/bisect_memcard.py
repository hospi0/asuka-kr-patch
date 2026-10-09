# -*- coding: utf-8 -*-
"""메모리카드 접근 때 BIOS 로 튕김 — 시험판 만들기(2026-10-09)
   python work/bisect_memcard.py nopot   : 항아리 «〜의항아리» → «〜항아리» 로 되돌린 빌드
   python work/bisect_memcard.py noarrow : patch_missed «↓盾→↓방» 만 뺀 빌드
   결과 Track 5 를 F:\…\시험_<이름>\ 폴더(cue + 트랙 1‥5)로 복사. 끝나면 번역표·도구는 원래대로 되돌린다."""
import glob, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, 'my files', 'tsv2')
BAK = os.path.join(ROOT, 'work', 'tsv_backup_20261009_pot')
PM = os.path.join(ROOT, 'tools', 'patch_missed.py')
FDIR = r'F:\hospi\roms\dc roms\Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan (Japan)'
BASES = ['손묶기', '흘려보내기', '토도', '삼위일체', '삼신일체', '보존', '창고', '합성', '저주', '회복', '변화', '약화', '강화',
         '유품', '손봉인', '환금', '축복', '풀효과', '식별', '뇌운', '응원']
mode = sys.argv[1]
pm_orig = open(PM, encoding='utf-8').read()
try:
    if mode == 'nopot':
        rx = re.compile('(?<![가-힣])(%s)의항아리' % '|'.join(BASES))
        n = 0
        for p in glob.glob(os.path.join(TSV, '*.tsv')):
            s = open(p, encoding='utf-8', newline='').read(); t = rx.sub(r'\1항아리', s)
            n += len(rx.findall(s))
            if t != s:
                open(p, 'w', encoding='utf-8', newline='').write(t)
        print('되돌림', n)
    elif mode == 'noarrow':
        open(PM, 'w', encoding='utf-8').write(pm_orig.replace("    ('SSCR.BIN',    '↓盾', '↓방'),\n", ''))
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_all.py'), '--write'], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    print(r.stdout[-400:]); assert r.returncode == 0, r.stderr[-2000:]
    out = FDIR + '\\시험_' + mode
    os.makedirs(out, exist_ok=True)
    B = os.path.join(ROOT, 'build', 'kr')
    for f in os.listdir(B):
        if f.endswith(('.bin', '.cue')):
            shutil.copyfile(os.path.join(B, f), os.path.join(out, f))
    print('복사', out)
finally:
    for f in glob.glob(os.path.join(BAK, '*.tsv')):
        shutil.copyfile(f, os.path.join(TSV, os.path.basename(f)))
    open(PM, 'w', encoding='utf-8').write(pm_orig)
    print('번역표·patch_missed 원래대로')
