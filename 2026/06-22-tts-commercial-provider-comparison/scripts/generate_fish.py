"""Fish Audio S2-Pro で 7 言語生成。

事前:
- https://fish.audio/voice-cloning/ で reference/ref.wav をアップロード → model_id 取得
  (登録に $0.1/voice。consent text 録音も必要)
- envs/fish venv で `pip install fish-audio-sdk python-dotenv`
- .env に FISH_API_KEY と FISH_MODEL_ID を設定

backend: s2-pro (推奨) / s1 / s1-mini
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

OUT = ROOT / "output" / "fish"
OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

API_KEY = os.environ["FISH_API_KEY"]
MODEL_ID = os.environ["FISH_MODEL_ID"]
BACKEND = os.environ.get("FISH_BACKEND", "s2-pro")


def main() -> None:
    session = Session(API_KEY)
    print(f"[init] model_id={MODEL_ID[:8]}... backend={BACKEND}", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.mp3"
        t0 = time.time()
        # Fish の TTSRequest は reference_id (voice clone model) + text。
        # 言語は自動判定。format=mp3 がデフォルト。
        req = TTSRequest(
            reference_id=MODEL_ID,
            text=text,
            format="mp3",
        )
        with open(out, "wb") as f:
            for chunk in session.tts(req, backend=BACKEND):
                f.write(chunk)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
