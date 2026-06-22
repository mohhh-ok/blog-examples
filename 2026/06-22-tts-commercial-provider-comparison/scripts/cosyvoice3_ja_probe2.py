"""kanji を kana 化して CosyVoice 3 JA の劣化が解消するか試す。"""
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

# 原文 (kanji 含む)
KANJI = "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。"

# 全部ひらがなにしたもの
HIRAGANA = "みなさん、こんにちは。ほんじつはあたらしいきのうについてごしょうかいします。どうぞよろしくおねがいいたします。"

# 全部カタカナにしたもの
KATAKANA = "ミナサン、コンニチハ。ホンジツハアタラシイキノウニツイテゴショウカイシマス。ドウゾヨロシクオネガイイタシマス。"

# prompt_text も kana 化したバリエーション
REF_HIRAGANA = "ほんじつはおいそがしいなかおこしいただき、まことにありがとうございます。それでは、ぷろじぇくとのしんちょくじょうきょうについて、かんたんにごせつめいさせていただきます。"

VARIANTS = [
    # cross_lingual + kana
    ("E_xl_hiragana", "cross_lingual", HIRAGANA, None),
    ("F_xl_katakana", "cross_lingual", KATAKANA, None),
    # zero_shot + kana target / kanji ref
    ("G_zs_hiragana_kanjiref", "zero_shot", HIRAGANA, REF_TEXT),
    # zero_shot + kana target + kana ref
    ("H_zs_hiragana_hiraganaref", "zero_shot", HIRAGANA, REF_HIRAGANA),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, mode, target, ref_text in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        if mode == "zero_shot":
            prompt_text = f"<|endofprompt|>{ref_text}"
            it = cosy.inference_zero_shot(target, prompt_text, str(REF), stream=False)
        elif mode == "cross_lingual":
            text = f"<|endofprompt|>{target}"
            it = cosy.inference_cross_lingual(text, str(REF), stream=False)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{name}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
