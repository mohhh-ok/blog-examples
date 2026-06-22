"""contains_chinese を monkey-patch して、JA kanji が中国語ルートに乗らないようにする実験。

仮説: 中国語を使わない (JP / EN / etc のみ) と決めれば、`contains_chinese` を
常に False に倒すだけで JA kanji が正しく読まれるはず。
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

# monkey-patch BEFORE importing frontend
from cosyvoice.utils import frontend_utils  # noqa: E402
frontend_utils.contains_chinese = lambda text: False
# frontend.py が import 時に named import している場合もあるので、cli.frontend モジュールも上書き
from cosyvoice.cli import frontend as cli_frontend  # noqa: E402
cli_frontend.contains_chinese = lambda text: False

from cosyvoice.cli.cosyvoice import CosyVoice3  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "cosyvoice3_patched"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"

# 私たちの JA target + demo の JA target 両方試す
TESTS = [
    ("ja_ours", "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。"),
    ("ja_demo", "結合することができないから矛盾するというのである。"),
]


def main() -> None:
    print(f"[patch] contains_chinese -> always False")
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    prompt_text = f"<|endofprompt|>{REF_TEXT}"
    for name, target in TESTS:
        for run in range(2):
            out = OUT / f"{name}_run{run}.wav"
            t0 = time.time()
            it = cosy.inference_zero_shot(target, prompt_text, str(REF), stream=False)
            chunks = [r["tts_speech"] for r in it]
            audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
            torchaudio.save(str(out), audio, cosy.sample_rate)
            print(f"[{name}_run{run}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
