"""demo と同じ target text を私たちの環境で生成。

demo c3_base が完全一致を出せる以上、生 kanji の正解パスが存在するはず。
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
OUT = ROOT / "output" / "cosyvoice3_demo_text"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR = COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"

# demo と同じ target
TARGET = "結合することができないから矛盾するというのである。"
DEMO_PROMPT_TEXT = "来週、美容院で髪を切ろうと思っています。"

VARIANTS = [
    # 私の元のレシピ: prompt_text 先頭に endofprompt + 私たちの REF_TEXT
    ("a_mine_kanji", "zero_shot", TARGET, f"<|endofprompt|>{REF_TEXT}"),
    # demo を真似て prompt_text を demo の prompt 書き起こしに置換
    ("b_demo_prompt", "zero_shot", TARGET, f"<|endofprompt|>{DEMO_PROMPT_TEXT}"),
    # demo prompt 書き起こしを生で渡す (endofprompt なし → CosyVoice3 では assert 通らないはず)
    # 試しに endofprompt を target 末尾に
    ("c_endofprompt_at_end", "zero_shot", f"{TARGET}<|endofprompt|>", DEMO_PROMPT_TEXT),
    # システム文書 + demo prompt
    ("d_sys_demo", "zero_shot", TARGET, f"You are a helpful assistant.<|endofprompt|>{DEMO_PROMPT_TEXT}"),
    # cross_lingual 単純呼び
    ("e_xl_simple", "cross_lingual", f"<|endofprompt|>{TARGET}", None),
]


def main() -> None:
    cosy = CosyVoice3(str(MODEL_DIR), load_trt=False, load_vllm=False, fp16=False)
    print(f"[init] sr={cosy.sample_rate}", flush=True)

    for name, mode, target, prompt_text in VARIANTS:
        out = OUT / f"{name}.wav"
        t0 = time.time()
        try:
            if mode == "zero_shot":
                it = cosy.inference_zero_shot(target, prompt_text, str(REF), stream=False)
            else:
                it = cosy.inference_cross_lingual(target, str(REF), stream=False)
            chunks = [r["tts_speech"] for r in it]
            audio = chunks[0] if len(chunks) == 1 else torchaudio.functional.concat(chunks, dim=1)
            torchaudio.save(str(out), audio, cosy.sample_rate)
            print(f"[{name}] {time.time() - t0:.1f}s", flush=True)
        except Exception as e:
            print(f"[{name}] FAILED: {e}", flush=True)


if __name__ == "__main__":
    main()
