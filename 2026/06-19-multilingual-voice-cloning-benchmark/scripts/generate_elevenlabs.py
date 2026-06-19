"""ElevenLabs API で 7 言語生成。

事前:
- envs/elevenlabs venv で `pip install elevenlabs python-dotenv`
- ダッシュボードで Instant Voice Cloning から参照音声をアップロードし voice_id を取得
- .env に ELEVENLABS_API_KEY と ELEVENLABS_VOICE_ID を設定

モデル: eleven_multilingual_v2 (or eleven_v3 if available)
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

OUT = ROOT / "output" / "elevenlabs"
OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

API_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]
MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")


def main() -> None:
    client = ElevenLabs(api_key=API_KEY)
    print(f"[init] voice_id={VOICE_ID[:6]}... model={MODEL_ID}", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.mp3"
        t0 = time.time()
        audio = client.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=text,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        with open(out, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
