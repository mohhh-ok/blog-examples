"""XTTS-v2 (Coqui) で 7 言語生成。

事前: envs/xtts venv で `pip install TTS`
参照音声: reference/ref.wav

注: XTTS-v2 は 13 言語サポート。今回の 7 言語すべて対応。
"""

import os
import sys
import time
from pathlib import Path

# PyTorch 2.6+ で torch.load の weights_only=True がデフォルト化。
# XTTS-v2 (TTS 0.22.0) は古い pickle 形式の checkpoint を読むため、安全な
# グローバルとして XTTS 関連 config を明示許可しないとロードできない。
import torch  # noqa: E402

from TTS.config.shared_configs import BaseDatasetConfig  # noqa: E402
from TTS.tts.configs.xtts_config import XttsConfig  # noqa: E402
from TTS.tts.models.xtts import XttsArgs, XttsAudioConfig  # noqa: E402

torch.serialization.add_safe_globals(
    [XttsConfig, XttsAudioConfig, XttsArgs, BaseDatasetConfig]
)

from TTS.api import TTS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "xtts"
OUT.mkdir(parents=True, exist_ok=True)

# Coqui ライセンスに同意する環境変数。一度同意済みでも明示しておくと安全
os.environ.setdefault("COQUI_TOS_AGREED", "1")


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")

    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        tts.tts_to_file(
            text=text,
            speaker_wav=str(REF),
            language=lang,
            file_path=str(out),
        )
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
