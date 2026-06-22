"""CosyVoice 3 JA の劣化原因を切り分ける実験スクリプト。

公式 WER 表 (paper) で JA は EN/ZH より 5-6 倍劣るが、本ベンチの CER 0.25 は
それより明らかに悪い。prompt_text の構造を変えて改善するか試す。
"""

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

TARGET = "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。"

VARIANTS = [
    ("A_zeroshot_no_sysprompt", "zero_shot", f"<|endofprompt|>{REF_TEXT}"),
    ("B_cross_lingual", "cross_lingual", None),
    ("C_zeroshot_ja_sysprompt", "zero_shot",
     f"あなたは日本語の音声合成アシスタントです。次の話者の声で日本語を読んでください。<|endofprompt|>{REF_TEXT}"),
    ("D_zeroshot_en_sysprompt", "zero_shot",
     f"You are a helpful assistant.<|endofprompt|>{REF_TEXT}"),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    ref_path = str(REF)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, mode, prompt_text in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        if mode == "zero_shot":
            it = cosy.inference_zero_shot(TARGET, prompt_text, ref_path, stream=False)
        elif mode == "cross_lingual":
            # cross_lingual は text に <|endofprompt|> を含める必要がある
            text = f"You are a helpful assistant.<|endofprompt|>{TARGET}"
            it = cosy.inference_cross_lingual(text, ref_path, stream=False)
        else:
            raise ValueError(mode)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{name}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
