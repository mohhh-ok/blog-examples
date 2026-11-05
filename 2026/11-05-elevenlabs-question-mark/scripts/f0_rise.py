"""wav の最後の有声区間で、いちばん低い所から終わり (最後の 30ms) までの F0 の上がりを半音で出す。

uv run --with praat-parselmouth python3 -I scripts/f0_rise.py output
"""
import json
import math
import sys
from pathlib import Path

import parselmouth


def semitones(a: float, b: float) -> float:
    return round(12 * math.log2(b / a), 1)


def voiced_runs(wav: Path):
    pitch = parselmouth.Sound(str(wav)).to_pitch(time_step=0.01, pitch_floor=120, pitch_ceiling=700)
    runs, cur = [], []
    for t, f in zip(pitch.xs(), pitch.selected_array["frequency"]):
        if f > 0:
            cur.append((t, f))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 3]  # 30ms 未満の切れ端は捨てる


def last_rise(wav: Path) -> dict:
    last = voiced_runs(wav)[-1]
    low_t, low_f = min(last, key=lambda x: x[1])
    end_f = sorted(f for _, f in last[-3:])[1]
    return {"min_hz": round(low_f), "min_at": round(low_t, 2), "end_hz": round(end_f), "rise_st": semitones(low_f, end_f)}


if __name__ == "__main__":
    for wav in sorted(Path(sys.argv[1]).glob("*.wav")):
        print(wav.stem, json.dumps(last_rise(wav)))
