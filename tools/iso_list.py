# -*- coding: utf-8 -*-
"""track3 의 ISO9660 디렉터리 트리를 나열한다 (읽기 전용)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdi import Track, SEC, HDR, USER

T3 = Track(3, 45000)

def read_lba(lba, nbytes):
    n = (nbytes + USER - 1) // USER
    return T3.user(lba, n)[:nbytes]

def parse_dir(lba, size, path=""):
    data = read_lba(lba, size)
    out = []
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:
            i = (i // USER + 1) * USER
            continue
        rec = data[i:i+ln]
        ext = struct.unpack_from('<I', rec, 2)[0]
        dlen = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33+nlen]
        i += ln
        if nlen == 1 and name in (b'\x00', b'\x01'):
            continue
        nm = name.decode('ascii', 'replace').split(';')[0]
        full = path + "/" + nm
        out.append((full, ext, dlen, flags))
        if flags & 2:
            out.extend(parse_dir(ext, dlen, full))
    return out

def main():
    pvd = T3.user(45016)
    root = pvd[156:156+34]
    rlba = struct.unpack_from('<I', root, 2)[0]
    rsize = struct.unpack_from('<I', root, 10)[0]
    volsize = struct.unpack_from('<I', pvd, 80)[0]
    print("volume id  :", pvd[40:72].decode('ascii','replace').strip())
    print("vol sectors:", volsize, " root lba:", rlba, "size:", rsize)
    ents = parse_dir(rlba, rsize)
    print("entries    :", len(ents))
    for full, lba, size, flags in ents:
        print("%-40s %8d %10d %s" % (full, lba, size, 'DIR' if flags & 2 else ''))

if __name__ == '__main__':
    main()
