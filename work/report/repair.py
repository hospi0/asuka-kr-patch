import glob, sys
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
fix = {'SYS01451': 'X' + BS + 'x02하늘의은혜두루마리', 'SYS02061': '같은 방 적에게' + BS + 'n벼락을 떨어뜨린다' + BS + 'n'}
for p in glob.glob('my files/tsv2/05_아이템명_*.tsv'):
    L = open(p, encoding='utf-8').read().split('\n'); out = []; ch = 0
    i = 0
    while i < len(L):
        c = L[i].split('\t')
        if len(c) >= 7 and c[0] in fix:
            k = c[0]; c[6] = fix[k]; out.append('\t'.join(c)); ch += 1
            # 깨진 이어지는 줄(열 1개짜리) 건너뜀
            while i + 1 < len(L) and len(L[i + 1].split('\t')) == 1 and L[i + 1] != '':
                i += 1
        else:
            out.append(L[i])
        i += 1
    if ch:
        open(p, 'w', encoding='utf-8', newline='').write('\n'.join(out)); print(p, ch)
for p in glob.glob('my files/tsv2/05_아이템명_*.tsv'):
    for n, l in enumerate(open(p, encoding='utf-8').read().split('\n')):
        if l and len(l.split('\t')) != 7: print('열 이상', p, n, l[:60])
