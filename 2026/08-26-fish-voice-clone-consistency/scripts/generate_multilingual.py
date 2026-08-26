"""Fish Audio voice clone multilingual test — generation step (第 5 弾).

同一の日本語 reference audio から 7 言語 (ja / en / zh / ko / fr / es / de) の
テキストを各 1 回 TTS し、output/multilingual/<lang>.wav とレイテンシ記録を残す。
生成テキストは 06-19 multilingual-voice-cloning-benchmark の prompts.py と同一
(過去記事との継続性のため)。

- model: s2.1-pro (SDK の backend 引数 → `model` ヘッダ)
- reference: inline zero-shot clone (references に wav バイナリ + 書き起こし)。
  条件は第 1・2 弾と同じ標準形 (ref_text あり)
- API key: 環境変数 FISH_AUDIO_API_KEY

usage: python scripts/generate_multilingual.py
"""

import json
import os
import sys
import time
from pathlib import Path

import soundfile as sf
from fish_audio_sdk import ReferenceAudio, Session, TTSRequest

ROOT = Path(__file__).resolve().parents[1]
REF_WAV = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "multilingual"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = "s2.1-pro"
SLEEP_BETWEEN_SEC = 2

# ref.wav の書き起こし (人手確認済み。第 1・2 弾と同一)
REF_TEXT = (
    "本日はお忙しい中お越しいただき、誠にありがとうございます。"
    "それでは、プロジェクトの進捗状況について、簡単にご説明させていただきます。"
)

# 生成テキスト 7 言語 (06-19 multilingual-voice-cloning-benchmark の prompts.py と同一)
GEN_TEXTS = {
    "ja": "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。",
    "en": "Hello everyone. Today, I'd like to introduce a new feature. Thank you for joining us.",
    "zh": "大家好，今天我将为大家介绍一项新功能，感谢您的参与。",
    "ko": "여러분 안녕하세요. 오늘은 새로운 기능을 소개해 드리겠습니다. 잘 부탁드립니다.",
    "fr": "Bonjour à tous. Aujourd'hui, je vais vous présenter une nouvelle fonctionnalité. Merci de votre attention.",
    "es": "Hola a todos. Hoy les voy a presentar una nueva función. Muchas gracias por su atención.",
    "de": "Hallo zusammen. Heute stelle ich Ihnen eine neue Funktion vor. Vielen Dank für Ihre Aufmerksamkeit.",
}


def main() -> None:
    api_key = os.environ.get("FISH_AUDIO_API_KEY")
    if not api_key:
        print("error: FISH_AUDIO_API_KEY is not set", file=sys.stderr)
        sys.exit(2)

    session = Session(api_key)
    ref_audio = REF_WAV.read_bytes()
    print(f"[init] model={MODEL} ref={REF_WAV.name} ({len(ref_audio)} bytes)", flush=True)

    records = []
    consecutive_failures = 0
    langs = list(GEN_TEXTS)

    for n, lang in enumerate(langs, start=1):
        gen_text = GEN_TEXTS[lang]
        out_path = OUT / f"{lang}.wav"
        req = TTSRequest(
            text=gen_text,
            references=[ReferenceAudio(audio=ref_audio, text=REF_TEXT)],
            format="wav",
        )
        t0 = time.time()
        try:
            with open(out_path, "wb") as f:
                for chunk in session.tts(req, backend=MODEL):
                    f.write(chunk)
        except Exception as e:  # noqa: BLE001
            consecutive_failures += 1
            print(f"[{lang}] FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            out_path.unlink(missing_ok=True)
            if consecutive_failures >= 3:
                print("error: 3 consecutive failures — aborting", file=sys.stderr)
                sys.exit(1)
            time.sleep(SLEEP_BETWEEN_SEC)
            continue

        consecutive_failures = 0
        latency = time.time() - t0
        info = sf.info(str(out_path))
        duration = info.frames / info.samplerate
        records.append(
            {
                "lang": lang,
                "file": out_path.name,
                "text": gen_text,
                "text_chars": len(gen_text),
                "latency_sec": round(latency, 3),
                "duration_sec": round(duration, 3),
                "samplerate": info.samplerate,
                "channels": info.channels,
                "bytes": out_path.stat().st_size,
            }
        )
        print(
            f"[{lang}] {out_path.name} latency={latency:.2f}s "
            f"duration={duration:.3f}s sr={info.samplerate}",
            flush=True,
        )
        if n < len(langs):
            time.sleep(SLEEP_BETWEEN_SEC)

    meta = {
        "model": MODEL,
        "ref_file": REF_WAV.name,
        "ref_text": REF_TEXT,
        "num_langs_requested": len(GEN_TEXTS),
        "num_langs_succeeded": len(records),
        "langs": records,
    }
    (OUT / "generation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {len(records)}/{len(GEN_TEXTS)} langs -> {OUT / 'generation.json'}", flush=True)
    if len(records) < len(GEN_TEXTS):
        sys.exit(1)


if __name__ == "__main__":
    main()
