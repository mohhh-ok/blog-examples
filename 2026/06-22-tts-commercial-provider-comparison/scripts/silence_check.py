"""各 wav の長さ・無音割合・最長無音区間を測る。"""
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def analyze(path: Path, top_db: int = 30):
    y, sr = librosa.load(str(path), sr=None)
    total = len(y) / sr
    # RMS で voiced 区間を抽出
    intervals = librosa.effects.split(y, top_db=top_db)
    voiced_sec = sum((e - s) for s, e in intervals) / sr
    silence_sec = total - voiced_sec
    # 連続無音の最長を計算
    if len(intervals) <= 1:
        max_gap = total - voiced_sec if voiced_sec > 0 else total
    else:
        gaps = [(intervals[i + 1][0] - intervals[i][1]) / sr for i in range(len(intervals) - 1)]
        max_gap = max(gaps) if gaps else 0.0
    return total, silence_sec, max_gap, voiced_sec


def main() -> None:
    for model_dir in sorted(OUT.iterdir()):
        if not model_dir.is_dir() or "probe" in model_dir.name or "demo_text" in model_dir.name or "patched" in model_dir.name:
            continue
        print(f"## {model_dir.name}")
        for wav in sorted(model_dir.glob("*.wav")):
            total, silence, max_gap, voiced = analyze(wav)
            sr_tag = " ⚠長尺" if total > 15 else ""
            gap_tag = " ⚠長無音" if max_gap > 2 else ""
            print(f"  [{wav.stem:4s}] 全長 {total:5.1f}s / 発話 {voiced:5.1f}s / 無音 {silence:5.1f}s / 最長無音 {max_gap:4.1f}s{sr_tag}{gap_tag}")
        print()


if __name__ == "__main__":
    main()
