"""Qiita 流: <|endofprompt|> を tts_text 末尾、prompt_text は素のままで kanji を渡す。"""
import os
import sys
import time
from pathlib import Path

import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import REF_TEXT  # noqa: E402

COSYVOICE_ROOT = Path(os.environ.get("COSYVOICE_ROOT", ROOT / "envs" / "CosyVoice"))
sys.path.insert(0, str(COSYVOICE_ROOT))
sys.path.insert(0, str(COSYVOICE_ROOT / "third_party" / "Matcha-TTS"))

from cosyvoice.cli.cosyvoice import CosyVoice3  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice3_probe"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"

KANJI = "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。"

VARIANTS = [
    # Qiita 流: tts_text 末尾に endofprompt、prompt_text は素
    ("M_zs_qiita_kanji", KANJI + "<|endofprompt|>", REF_TEXT),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, target, ref_text in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        it = cosy.inference_zero_shot(target, ref_text, str(REF), stream=False)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{name}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
