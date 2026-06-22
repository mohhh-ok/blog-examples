"""ref.wav と各 probe 出力の F0 (基本周波数) を比較して、声質が保たれているか客観評価。

成人男性: 85-180Hz / 成人女性: 165-255Hz が典型。
"""
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice3_probe"


def median_f0(path: Path) -> float | None:
    y, sr = librosa.load(str(path), sr=None)
    f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    voiced = f0[vflag]
    if len(voiced) == 0:
        return None
    return float(np.median(voiced))


def main() -> None:
    ref_f0 = median_f0(REF)
    print(f"[ref.wav] median F0 = {ref_f0:.1f}Hz", flush=True)
    print()
    for wav in sorted(OUT.glob("*.wav")):
        f0 = median_f0(wav)
        if f0 is None:
            print(f"[{wav.stem:30s}] (no voiced frames)")
            continue
        diff = f0 - ref_f0
        marker = " ★" if abs(diff) < 20 else " (差 大)" if abs(diff) > 50 else ""
        print(f"[{wav.stem:30s}] F0 = {f0:6.1f}Hz (ref 差 {diff:+6.1f}Hz){marker}")


if __name__ == "__main__":
    main()
