# -*- coding: utf-8 -*-
"""Shift-JIS 후보 문자열 스캔 (읽기 전용)."""
import sys, re, os

def is_lead(b): return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef
def is_trail(b): return 0x40 <= b <= 0xfc and b != 0x7f

def scan(data, minchars=3):
    out=[]; i=0; n=len(data)
    while i < n-1:
        if is_lead(data[i]) and is_trail(data[i+1]):
            j=i; cnt=0
            while j < n-1 and is_lead(data[j]) and is_trail(data[j+1]):
                j+=2; cnt+=1
            if cnt>=minchars:
                try:
                    s=data[i:j].decode('cp932')
                    if not re.fullmatch(r'[\u3000-\u303f\uff00-\uffef]+', s):
                        out.append((i,cnt,s))
                except UnicodeDecodeError:
                    pass
            i=j
        else:
            i+=1
    return out

if __name__=='__main__':
    for p in sys.argv[1:]:
        d=open(p,'rb').read()
        r=scan(d)
        tot=sum(c for _,c,_ in r)
        print("%-40s hits=%5d chars=%7d" % (os.path.basename(p), len(r), tot))
