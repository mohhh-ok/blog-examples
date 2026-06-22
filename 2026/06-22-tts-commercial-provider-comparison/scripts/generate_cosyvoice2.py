"""CosyVoice 2 (Apache 2.0) で 7 言語生成。

v3 の `<|endofprompt|>` 必須制約がない (v2 LLM クラスにアサーションがない)。
Qiita 記事 (https://qiita.com/GeneLab_999/items/f08c41121e3156ed22d2) によれば
v2 は素の kanji 入力でも JA を読めるらしい。本ベンチで実測する。

事前: envs/cosyvoice3.md の venv 流用 (依存は同じ)
モデル: iic/CosyVoice2-0.5B (HF: FunAudioLLM/CosyVoice2-0.5B)
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

from cosyvoice.cli.cosyvoice import CosyVoice2  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice2"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "CosyVoice2-0.5B"


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")
    if not MODEL_DIR.exists():
        raise SystemExit(f"missing model: {MODEL_DIR}")

    cosy = CosyVoice2(
        str(MODEL_DIR),
        load_jit=False,
        load_trt=False,
        load_vllm=False,
        fp16=False,
    )
    print(f"[init] model={MODEL_DIR.name} sr={cosy.sample_rate}", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        chunks = []
        for r in cosy.inference_zero_shot(text, REF_TEXT, str(REF), stream=False):
            chunks.append(r["tts_speech"])
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
