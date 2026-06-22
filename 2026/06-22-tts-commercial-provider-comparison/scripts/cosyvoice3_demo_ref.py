"""demo の prompt audio をそのまま ref として使って、同じ target を生成。

これで demo c3_base に近い品質が出れば、犯人は参照音声 (私たちの ref.wav が
モデルにとって相性悪い) ということになる。

demo prompt: /tmp/demo_check/prompt/ja.wav (来週、美容院で...)
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

DEMO_REF = Path("/tmp/demo_check/prompt/ja.wav")
DEMO_REF_TEXT = "来週、美容院で髪を切ろうと思っています。"
TARGET = "結合することができないから矛盾するというのである。"

OUT = ROOT / "output" / "cosyvoice3_demo_text"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    prompt_text = f"<|endofprompt|>{DEMO_REF_TEXT}"
    for run in range(3):  # サンプリング揺れを見るため 3 回
        out = OUT / f"f_demo_ref_run{run}.wav"
        t0 = time.time()
        it = cosy.inference_zero_shot(TARGET, prompt_text, str(DEMO_REF), stream=False)
        chunks = [r["tts_speech"] for r in it]
        audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
        torchaudio.save(str(out), audio, cosy.sample_rate)
        print(f"[f_demo_ref_run{run}] {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
