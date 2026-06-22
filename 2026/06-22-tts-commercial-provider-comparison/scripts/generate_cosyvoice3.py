"""Fun-CosyVoice 3.0 (Apache 2.0) で 7 言語生成。

公式に 9 言語 (zh/en/ja/ko/de/es/fr/it/ru) サポート + Chinese dialects。
inference_zero_shot API。

事前: envs/cosyvoice3.md の手順で venv + git clone + モデル DL を済ませる。
参照音声: reference/ref.wav
"""

import os
import sys
import time
from pathlib import Path

import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS, REF_TEXT  # noqa: E402

COSYVOICE_ROOT = Path(os.environ.get("COSYVOICE_ROOT", ROOT / "envs" / "CosyVoice"))
sys.path.insert(0, str(COSYVOICE_ROOT))
sys.path.insert(0, str(COSYVOICE_ROOT / "third_party" / "Matcha-TTS"))

from cosyvoice.cli.cosyvoice import CosyVoice3  # noqa: E402
from cosyvoice.utils.file_utils import load_wav  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice3"
OUT.mkdir(parents=True, exist_ok=True)

MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")
    if not MODEL_DIR.exists():
        raise SystemExit(f"missing model: {MODEL_DIR} (see docstring)")

    cosy = CosyVoice3(
        str(MODEL_DIR),
        load_trt=False,
        load_vllm=False,
        fp16=False,
    )
    prompt_speech = load_wav(str(REF), 16000)
    print(f"[init] model={MODEL_DIR.name} sr={cosy.sample_rate}", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        chunks = []
        for r in cosy.inference_zero_shot(text, REF_TEXT, prompt_speech, stream=False):
            chunks.append(r["tts_speech"])
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
