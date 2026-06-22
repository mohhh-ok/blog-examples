"""Qwen3-TTS (Apache 2.0) で 7 言語生成。

公式に 10 言語サポート (zh/en/ja/ko/de/fr/ru/pt/es/it)。
voice clone は ref_audio + ref_text の ICL モード。

事前: envs/qwen3_tts.md の手順で venv + qwen-tts インストール + 0.6B-Base DL を済ませる。
参照音声: reference/ref.wav
"""

import os
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS, REF_TEXT  # noqa: E402

from qwen_tts import Qwen3TTSModel  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "qwen3_tts"
OUT.mkdir(parents=True, exist_ok=True)

MODEL_DIR = ROOT / "envs" / "pretrained_models" / "Qwen3-TTS-12Hz-0.6B-Base"

# prompts.py の 7 言語キー → Qwen3-TTS の language id
LANG_MAP = {
    "ja": "japanese",
    "en": "english",
    "zh": "chinese",
    "ko": "korean",
    "fr": "french",
    "es": "spanish",
    "de": "german",
}


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")
    if not MODEL_DIR.exists():
        raise SystemExit(f"missing model: {MODEL_DIR} (see envs/qwen3_tts.md)")

    # Mac MPS は float32 必須 (float16/bfloat16 で NaN logits、issue #333)。
    # FlashAttention 2 は CUDA 専用なので SDPA fallback。
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[init] device={device} model={MODEL_DIR.name}", flush=True)

    model = Qwen3TTSModel.from_pretrained(
        str(MODEL_DIR),
        device_map=device,
        dtype=torch.float32,
        attn_implementation="sdpa",
    )

    ref_path = str(REF)
    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=LANG_MAP[lang],
            ref_audio=ref_path,
            ref_text=REF_TEXT,
            non_streaming_mode=True,
        )
        sf.write(str(out), wavs[0], sr)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
