"""Cartesia Sonic-3 で 7 言語生成。

事前:
- ダッシュボードの Voice Library で Pro Voice Cloning から reference/ref.wav を登録 → voice_id 取得
  https://www.cartesia.ai/blog/pro-voice-cloning/
- envs/cartesia venv で `pip install cartesia python-dotenv`
- .env に CARTESIA_API_KEY と CARTESIA_VOICE_ID を設定

モデル: sonic-3 (multilingual)
"""

import os
import sys
import time
from pathlib import Path

from cartesia import Cartesia
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

OUT = ROOT / "output" / "cartesia"
OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

API_KEY = os.environ["CARTESIA_API_KEY"]
VOICE_ID = os.environ["CARTESIA_VOICE_ID"]
MODEL_ID = os.environ.get("CARTESIA_MODEL_ID", "sonic-3")

# Cartesia の language code は ISO 2 文字。zh は "zh", ja は "ja" でそのまま渡せる。
CARTESIA_LANG = {
    "ja": "ja", "en": "en", "zh": "zh", "ko": "ko",
    "fr": "fr", "es": "es", "de": "de",
}


def main() -> None:
    client = Cartesia(api_key=API_KEY)
    print(f"[init] voice_id={VOICE_ID[:8]}... model={MODEL_ID}", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        chunks = client.tts.bytes(
            model_id=MODEL_ID,
            transcript=text,
            voice={"mode": "id", "id": VOICE_ID},
            language=CARTESIA_LANG[lang],
            output_format={
                "container": "wav",
                "encoding": "pcm_s16le",
                "sample_rate": 24000,
            },
        )
        with open(out, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
