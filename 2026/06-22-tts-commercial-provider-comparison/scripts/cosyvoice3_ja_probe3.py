"""は → わ の音節置換を入れた正しい kana で CosyVoice 3 を比較。

日本語の は は主題助詞・挨拶語尾では音節 "wa" として読む。kana を TTS に
直接渡す場合、音節レベルで正しく書き換えないと "ha" で読まれて不自然になる。
"""
import os
import sys
import time
from pathlib import Path

import torchaudio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COSYVOICE_ROOT = Path(os.environ.get("COSYVOICE_ROOT", ROOT / "envs" / "CosyVoice"))
sys.path.insert(0, str(COSYVOICE_ROOT))
sys.path.insert(0, str(COSYVOICE_ROOT / "third_party" / "Matcha-TTS"))

from cosyvoice.cli.cosyvoice import CosyVoice3  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice3_probe"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"

# は → わ を当てはめた "音節として正しい" kana
HIRAGANA_FIXED = "みなさん、こんにちわ。ほんじつわあたらしいきのうについてごしょうかいします。どうぞよろしくおねがいいたします。"
KATAKANA_FIXED = "ミナサン、コンニチワ。ホンジツワアタラシイキノウニツイテゴショウカイシマス。ドウゾヨロシクオネガイイタシマス。"

VARIANTS = [
    ("I_xl_hiragana_fixed", "cross_lingual", HIRAGANA_FIXED),
    ("J_xl_katakana_fixed", "cross_lingual", KATAKANA_FIXED),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, mode, target in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        text = f"<|endofprompt|>{target}"
        it = cosy.inference_cross_lingual(text, str(REF), stream=False)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{name}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
