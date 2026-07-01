"""Chatterbox Multilingual v3 (MIT, Resemble AI) で 7 言語生成。

06-22 ベンチの `generate_qwen3_tts.py` と同じインターフェース:
  - 参照: reference/ref.wav (男性、24kHz mono、~10 秒)
  - 出力: output/chatterbox/<lang>.wav

事前: `uv sync` で env 用意。モデル (~2GB) は HF hub から DL、以降 `~/.cache/huggingface` に cache。
"""

import sys
import time
from pathlib import Path

import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "chatterbox"
OUT.mkdir(parents=True, exist_ok=True)

# prompts.py の 7 言語キー → Chatterbox の language_id
LANG_MAP = {
    "ja": "ja",
    "en": "en",
    "zh": "zh",
    "ko": "ko",
    "fr": "fr",
    "es": "es",
    "de": "de",
}

SEED = 42


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")

    torch.manual_seed(SEED)
    device = pick_device()
    print(f"[init] device={device}", flush=True)

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    print(f"[init] model loaded in {time.time() - t0:.1f}s", flush=True)

    ref_path = str(REF)
    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t = time.time()
        wav = model.generate(text, language_id=LANG_MAP[lang], audio_prompt_path=ref_path)
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)
        torchaudio.save(str(out), wav.cpu(), model.sr)
        print(f"[{lang}] {out.name} ({time.time() - t:.1f}s, {wav.shape[-1] / model.sr:.2f}s @ {model.sr}Hz)", flush=True)


if __name__ == "__main__":
    main()
