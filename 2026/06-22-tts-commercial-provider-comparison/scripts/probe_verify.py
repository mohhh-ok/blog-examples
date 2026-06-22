"""probe 出力を Whisper で書き起こして比較。"""
import re
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel
from jiwer import cer, wer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "cosyvoice3_probe"

EXPECTED = "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。"


def normalize(s: str) -> str:
    s = s.lower()
    return re.sub(r"[\s　、。．，,\.!?!?・…\-—\"'""''`]+", " ", s).strip()


def main() -> None:
    whisper = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print(f"expected: {EXPECTED}\n")
    for wav in sorted(OUT.glob("*.wav")):
        t0 = time.time()
        segs, _ = whisper.transcribe(str(wav), language="ja", beam_size=5)
        got = "".join(s.text for s in segs).strip()
        exp_n, got_n = normalize(EXPECTED), normalize(got)
        c = cer(exp_n, got_n) if got_n else None
        print(f"[{wav.stem}] cer={c:.3f} ({time.time() - t0:.1f}s)")
        print(f"  got: {got}\n")


if __name__ == "__main__":
    main()
