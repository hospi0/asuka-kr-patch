import glob, csv, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')
rows = []
for p in sorted(glob.glob('my files/tsv2/*.tsv')):
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r) >= 7 and r[0] != 'id': rows.append((os.path.basename(p), r))


def norm(s): return re.sub(r'\\n|\s|　', '', s)


for q in sys.argv[1:]:
    hits = [(f, r) for f, r in rows if norm(q) in norm(r[6])]
    print('##', q, len(hits))
    for f, r in hits[:6]: print('  ', r[0], r[3], '|', r[5][:50].replace('\\n', '⏎'), '|', r[6][:80].replace('\\n', '⏎'))
