"""公式 demo の JA wav (c2_base / c3_base / c3_large / prompt) を Whisper で書き起こし。
demo 表 (来週、美容院で髪を切ろうと思っています / 結合することができないから矛盾するというのである) と比較。
"""
import sys
from pathlib import Path

from faster_whisper import WhisperModel

DEMO = Path("/tmp/demo_check")

EXPECTED_PROMPT = "来週、美容院で髪を切ろうと思っています。"
EXPECTED_TARGET = "結合することができないから矛盾するというのである。"


def main() -> None:
    w = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print(f"expected prompt: {EXPECTED_PROMPT}")
    print(f"expected target: {EXPECTED_TARGET}\n")
    for variant in ("prompt", "c2_base", "c3_base", "c3_large"):
        f = DEMO / variant / "ja.wav"
        segs, info = w.transcribe(str(f), language="ja", beam_size=5)
        got = "".join(s.text for s in segs).strip()
        print(f"[{variant}] {got}")


if __name__ == "__main__":
    main()
