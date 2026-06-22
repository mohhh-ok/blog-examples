"""生成された wav/mp3 を Whisper large-v3 で書き起こし、期待テキストと比較。

事前: `pip install faster-whisper jiwer`

出力: results/<model>.json に [{lang, expected, got, detected, prob, bigram_sim, wer, cer, elapsed}, ...]
"""

import json
import re
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel
from jiwer import cer, wer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

OUT = ROOT / "output"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

MODELS = ["cartesia", "fish", "azure_personal", "cosyvoice2", "cosyvoice3", "openvoice_v2", "elevenlabs"]


def normalize(s: str) -> str:
    s = s.lower()
    return re.sub(r"[\s　、。．，,\.!?!?・…\-—\"'""''`]+", " ", s).strip()


def bigram_sim(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    A = {a[i : i + 2] for i in range(len(a) - 1)}
    B = {b[i : i + 2] for i in range(len(b) - 1)}
    return len(A & B) / len(A | B)


def find_audio(model: str, lang: str) -> Path | None:
    for ext in ("wav", "mp3", "flac"):
        f = OUT / model / f"{lang}.{ext}"
        if f.exists():
            return f
    return None


def main() -> None:
    print("[init] loading whisper large-v3 (int8/cpu)...", flush=True)
    t0 = time.time()
    whisper = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print(f"[init] loaded in {time.time() - t0:.1f}s", flush=True)

    for model in MODELS:
        rows = []
        for lang, expected in PROMPTS.items():
            f = find_audio(model, lang)
            if f is None:
                continue
            t1 = time.time()
            segs, info = whisper.transcribe(str(f), language=lang, beam_size=5)
            got = "".join(s.text for s in segs).strip()
            sim = bigram_sim(expected, got)

            exp_n = normalize(expected)
            got_n = normalize(got)
            row = {
                "lang": lang,
                "expected": expected,
                "got": got,
                "detected": info.language,
                "prob": round(info.language_probability, 3),
                "bigram_sim": round(sim, 3),
                "wer": round(wer(exp_n, got_n), 3) if got_n else None,
                "cer": round(cer(exp_n, got_n), 3) if got_n else None,
                "elapsed": round(time.time() - t1, 2),
            }
            rows.append(row)
            print(f"[{model}/{lang}] sim={sim:.2f} cer={row['cer']} got={got[:60]}", flush=True)

        if rows:
            (RESULTS / f"{model}.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2)
            )


if __name__ == "__main__":
    main()
