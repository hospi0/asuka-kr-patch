# -*- coding: utf-8 -*-
"""GD-ROM (cue/bin, MODE1/2352) 판독 유틸 - 읽기 전용.

트랙 배치 (실측, 섹터 헤더 MSF 로 확인):
  track1 MODE1  LBA      0 ..    449   (SD area)
  track2 AUDIO                          (SD area)
  track3 MODE1  LBA  45000 .. 139653   (HD area, ISO9660 PVD @ 45016)
  track4 AUDIO                          (HD area)
  track5 MODE1  LBA 140708 .. 549149   (HD area, 파일 선두 225섹터는 pregap)
"""
import os, struct

ROM_DIR = r"C:\claude\roms\dc\Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan (Japan)"
BASE = "Fushigi no Dungeon - Fuurai no Shiren Gaiden - Onna Kenshi Asuka Kenzan! (Japan)"

SEC = 2352
HDR = 16
USER = 2048

def track_path(n):
    return os.path.join(ROM_DIR, "%s (Track %d).bin" % (BASE, n))

class Track:
    def __init__(self, num, start_lba, file_first_sector=0):
        self.num = num
        self.path = track_path(num)
        self.start_lba = start_lba
        self.skip = file_first_sector
        self.sectors = os.path.getsize(self.path) // SEC - file_first_sector
        self.f = open(self.path, 'rb')
    def raw(self, lba, count=1):
        self.f.seek((lba - self.start_lba + self.skip) * SEC)
        return self.f.read(count * SEC)
    def user(self, lba, count=1):
        d = self.raw(lba, count)
        return b''.join(d[i*SEC+HDR:i*SEC+HDR+USER] for i in range(count))
    def contains(self, lba):
        return self.start_lba <= lba < self.start_lba + self.sectors

class Disc:
    def __init__(self):
        self.tracks = [Track(1, 0), Track(3, 45000), Track(5, 140708, 225)]
    def track_of(self, lba):
        for t in self.tracks:
            if t.contains(lba):
                return t
        raise KeyError("LBA %d 는 어떤 데이터 트랙에도 없다" % lba)
    def read(self, lba, nbytes):
        t = self.track_of(lba)
        n = (nbytes + USER - 1) // USER
        avail = t.start_lba + t.sectors - lba
        if n > avail:
            raise ValueError("LBA %d 에서 %d 섹터 요청, 트랙%d 잔여 %d" % (lba, n, t.num, avail))
        return t.user(lba, n)[:nbytes]

def msf_of(raw):
    bcd = lambda b: (b >> 4) * 10 + (b & 15)
    return bcd(raw[12]) * 60 * 75 + bcd(raw[13]) * 75 + bcd(raw[14]) - 150
