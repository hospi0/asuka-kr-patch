# -*- coding: utf-8 -*-
"""ISO9660 트리를 나열/추출한다 (읽기 전용, 대상은 --out 아래에만 쓴다)."""
import sys, os, struct, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdi import Disc, USER

D = Disc()
PVD_LBA = 45016

def walk():
    pvd = D.read(PVD_LBA, USER)
    rlba = struct.unpack_from('<I', pvd, 158)[0]
    rsize = struct.unpack_from('<I', pvd, 166)[0]
    out = []
    def rec(lba, size, path):
        data = D.read(lba, size)
        i = 0
        while i < len(data):
            ln = data[i]
            if ln == 0:
                i = (i // USER + 1) * USER
                continue
            r = data[i:i+ln]
            ext = struct.unpack_from('<I', r, 2)[0]
            dl = struct.unpack_from('<I', r, 10)[0]
            fl = r[25]; nl = r[32]
            nm = r[33:33+nl]
            i += ln
            if nl == 1 and nm in (b'\x00', b'\x01'):
                continue
            name = nm.decode('ascii', 'replace').split(';')[0]
            full = path + "/" + name
            out.append((full, ext, dl, fl))
            if fl & 2:
                rec(ext, dl, full)
    rec(rlba, rsize, "")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    ents = [e for e in walk() if not (e[3] & 2)]
    for full, lba, size, fl in ents:
        if a.only and not any(k.upper() in full.upper() for k in a.only):
            continue
        if not a.out:
            print("%-40s lba=%7d size=%10d track=%d" % (full, lba, size, D.track_of(lba).num))
            continue
        dst = os.path.join(a.out, full.lstrip('/').replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(D.read(lba, size))
        print("wrote", dst, size)

if __name__ == '__main__':
    main()
