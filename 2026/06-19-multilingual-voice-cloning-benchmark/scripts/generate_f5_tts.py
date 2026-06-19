"""F5-TTS で 7 言語生成。

事前: envs/f5-tts venv で `pip install f5-tts torch torchaudio soundfile`
参照音声: reference/ref.wav

注: F5-TTS_v1_Base は学習が英中ベース。ja/ko は破綻しやすい。
"""

import sys
import time
from pathlib import Path

import torch
from f5_tts.api import F5TTS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import REF_TEXT, PROMPTS  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "f5_tts"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[init] device={device}", flush=True)
    model = F5TTS(model="F5TTS_v1_Base", device=device)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        model.infer(
            ref_file=str(REF),
            ref_text=REF_TEXT,
            gen_text=text,
            nfe_step=32,
            file_wave=str(out),
            show_info=lambda *_: None,
        )
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
