"""声質を保つには zero_shot vs cross_lingual どちらが良いか、kana 修正版で比較。"""
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

KATAKANA_FIXED = "ミナサン、コンニチワ。ホンジツワアタラシイキノウニツイテゴショウカイシマス。ドウゾヨロシクオネガイイタシマス。"
# REF_TEXT 側にも は → わ を当てる
REF_TEXT_KANA = "ホンジツワオイソガシイナカオコシイタダキ、マコトニアリガトウゴザイマス。ソレデワ、プロジェクトノシンチョクジョウキョウニツイテ、カンタンニゴセツメイサセテイタダキマス。"

VARIANTS = [
    # ref_text kanji 入力 (生)
    ("K_zs_katakana_kanjiref", "zero_shot", KATAKANA_FIXED, REF_TEXT),
    # ref_text も katakana 修正版
    ("L_zs_katakana_katakanaref", "zero_shot", KATAKANA_FIXED, REF_TEXT_KANA),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, mode, target, ref_text in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        prompt_text = f"<|endofprompt|>{ref_text}"
        it = cosy.inference_zero_shot(target, prompt_text, str(REF), stream=False)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[{name}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
