import re
import sys
from pathlib import Path

import librosa
import numpy as np
from faster_whisper import WhisperModel
from jiwer import cer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "cosyvoice3_patched"
REF = ROOT / "reference" / "ref.wav"

EXPECTED = {
    "ja_ours": "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。",
    "ja_demo": "結合することができないから矛盾するというのである。",
}


def normalize(s: str) -> str:
    return re.sub(r"[\s　、。．，,\.!?!?・…\-—\"'""''`]+", " ", s.lower()).strip()


def median_f0(path: Path) -> float | None:
    y, sr = librosa.load(str(path), sr=None)
    f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    voiced = f0[vflag]
    return float(np.median(voiced)) if len(voiced) > 0 else None


def main() -> None:
    ref_f0 = median_f0(REF)
    print(f"ref.wav F0 = {ref_f0:.1f}Hz\n")
    w = WhisperModel("large-v3", device="cpu", compute_type="int8")
    for wav in sorted(OUT.glob("*.wav")):
        prefix = "_".join(wav.stem.rsplit("_", 1)[:-1])
        exp = EXPECTED[prefix]
        segs, _ = w.transcribe(str(wav), language="ja", beam_size=5)
        got = "".join(s.text for s in segs).strip()
        c = cer(normalize(exp), normalize(got))
        f0 = median_f0(wav)
        if f0 is None:
            print(f"[{wav.stem}] cer={c:.3f} F0=NaN")
        else:
            print(f"[{wav.stem}] cer={c:.3f} F0={f0:.1f} (差 {f0 - ref_f0:+.1f})")
        print(f"  expected: {exp}")
        print(f"  got:      {got}\n")


if __name__ == "__main__":
    main()
