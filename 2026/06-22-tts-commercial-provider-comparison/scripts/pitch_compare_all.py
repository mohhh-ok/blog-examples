"""ref.wav と各モデル出力の F0 を全 wav 通して比較。"""
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output"


def median_f0(path: Path) -> float | None:
    y, sr = librosa.load(str(path), sr=None)
    f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    voiced = f0[vflag]
    if len(voiced) == 0:
        return None
    return float(np.median(voiced))


def main() -> None:
    ref_f0 = median_f0(REF)
    print(f"[ref.wav] median F0 = {ref_f0:.1f}Hz\n")
    for model_dir in sorted(OUT.iterdir()):
        if not model_dir.is_dir() or model_dir.name == "cosyvoice3_probe":
            continue
        print(f"## {model_dir.name}")
        for wav in sorted(model_dir.glob("*.wav")):
            f0 = median_f0(wav)
            if f0 is None:
                print(f"  [{wav.stem}] no voiced frames")
                continue
            diff = f0 - ref_f0
            tag = " ★" if abs(diff) < 20 else " ⚠女性化" if diff > 50 else ""
            print(f"  [{wav.stem:4s}] F0 = {f0:6.1f}Hz (差 {diff:+6.1f}Hz){tag}")
        print()


if __name__ == "__main__":
    main()
