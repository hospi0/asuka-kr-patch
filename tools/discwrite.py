# -*- coding: utf-8 -*-
"""트랙 BIN 안의 «ISO 파일 내용»을 바이트 단위로 덮어쓰고 EDC/ECC 를 재계산한다."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdrom_ecc import fix_sectors

SEC, HDR, USER = 2352, 16, 2048

class TrackWriter:
    """start_lba: 트랙의 INDEX01 LBA / skip: 파일 선두의 pregap 섹터 수"""
    def __init__(self, path, start_lba, skip=0):
        self.f = open(path, 'r+b')
        self.start_lba = start_lba
        self.skip = skip
        self.dirty = []

    def _bin_off(self, lba, in_sec):
        return (lba - self.start_lba + self.skip) * SEC + HDR + in_sec

    def write_user(self, lba, offset, data):
        """파일 시작 LBA 와 파일 내 바이트 오프셋으로 기록."""
        pos = offset
        i = 0
        while i < len(data):
            s_lba = lba + pos // USER
            in_sec = pos % USER
            n = min(USER - in_sec, len(data) - i)
            bo = self._bin_off(s_lba, in_sec)
            self.f.seek(bo)
            self.f.write(data[i:i + n])
            self.dirty.append((bo, n))
            i += n; pos += n

    def read_user(self, lba, offset, n):
        out = bytearray()
        pos = offset
        while len(out) < n:
            s_lba = lba + pos // USER
            in_sec = pos % USER
            k = min(USER - in_sec, n - len(out))
            self.f.seek(self._bin_off(s_lba, in_sec))
            out += self.f.read(k)
            pos += k
        return bytes(out)

    def close(self):
        cnt = fix_sectors(self.f, self.dirty)
        self.f.close()
        return cnt
