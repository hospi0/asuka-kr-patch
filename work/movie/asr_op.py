# -*- coding: utf-8 -*-
"""OP.SFD 음성 받아쓰기(위스퍼 large-v3) → op_asr.tsv (시작·끝·문장)"""
import sys, wave
import numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
w = wave.open(sys.argv[1] if len(sys.argv) > 1 else 'op.wav')
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
seg, info = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False)
out = open('op_asr.tsv', 'w', encoding='utf-8')
for s in seg:
    line = '%.2f\t%.2f\t%s' % (s.start, s.end, s.text.strip())
    print(line); out.write(line + '\n')
