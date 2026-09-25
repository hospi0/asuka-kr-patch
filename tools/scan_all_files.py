# -*- coding: utf-8 -*-
"""디스크의 «모든» ISO 파일을 훑어 번역 대상 후보 분량을 센다 (읽기 전용, 스트리밍).

모집단 완전성 확인용. 폰트 레퍼토리에 없는 글자가 든 문자열은 가짜로 본다.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdi import Disc, USER
from iso_extract import walk
from font import Font
from str_scan import strings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK = 4 << 20

def main():
    f = Font(os.path.join(ROOT, 'work', 'iso', 'DATAAPP.BIN'))
    rep = set(f.chars) | set('\n') | set(bytes(range(0x20, 0x7f)).decode())
    D = Disc()
    out = []
    for full, lba, size, fl in walk():
        if fl & 2:
            continue
        try:
            D.track_of(lba)
        except KeyError:
            out.append((full, size, -1, -1, '오디오트랙구간'))
            continue
        nstr = nch = 0
        pos = 0
        tail = b''
        while pos < size:
            n = min(CHUNK, size - pos)
            try:
                blk = D.read(lba + pos // USER, n)
            except Exception as e:
                out.append((full, size, -1, -1, str(e)))
                break
            buf = tail + blk
            for _, s in strings(buf):
                if all(c in rep for c in s) and len(s) >= 4:
                    nstr += 1; nch += len(s)
            tail = buf[-256:]
            pos += n
        else:
            out.append((full, size, nstr, nch, ''))
        print('%-28s %10d  문자열 %6d  글자 %7d %s' % (out[-1][0], out[-1][1], out[-1][2], out[-1][3], out[-1][4]), flush=True)
    json.dump(out, open(os.path.join(ROOT, 'work', 'population_scan.json'), 'w'), ensure_ascii=False)

if __name__ == '__main__':
    main()
