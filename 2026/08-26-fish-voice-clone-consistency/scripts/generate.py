"""Fish Audio voice clone consistency test — generation step.

同一の reference audio + 同一テキストで 5 回 TTS を実行し、
output/trial1.wav .. trial5.wav とレイテンシ記録を残す。

- model: s2.1-pro (SDK の backend 引数 → `model` ヘッダ)
- reference: inline zero-shot clone (references に wav バイナリ + 書き起こし)
- API key: 環境変数 FISH_AUDIO_API_KEY

usage: python scripts/generate.py
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
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

MODEL = "s2.1-pro"
NUM_TRIALS = 5
SLEEP_BETWEEN_SEC = 2

# ref.wav の書き起こし (人手確認済み)
REF_TEXT = (
    "本日はお忙しい中お越しいただき、誠にありがとうございます。"
    "それでは、プロジェクトの進捗状況について、簡単にご説明させていただきます。"
)

# 生成テキスト (5 回とも完全に同一・固有名詞なし)
GEN_TEXT = (
    "本日は晴天に恵まれ、公園には多くの家族連れが訪れています。"
    "午後からは気温が上がり、木陰で休む人の姿も見られました。"
    "明日も同じような穏やかな天気が続く見込みです。"
)


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

    for i in range(1, NUM_TRIALS + 1):
        out_path = OUT / f"trial{i}.wav"
        req = TTSRequest(
            text=GEN_TEXT,
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
            print(f"[trial{i}] FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
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
                "trial": i,
                "file": out_path.name,
                "latency_sec": round(latency, 3),
                "duration_sec": round(duration, 3),
                "samplerate": info.samplerate,
                "channels": info.channels,
                "bytes": out_path.stat().st_size,
            }
        )
        print(
            f"[trial{i}] {out_path.name} latency={latency:.2f}s "
            f"duration={duration:.3f}s sr={info.samplerate}",
            flush=True,
        )
        if i < NUM_TRIALS:
            time.sleep(SLEEP_BETWEEN_SEC)

    meta = {
        "model": MODEL,
        "ref_file": REF_WAV.name,
        "ref_text": REF_TEXT,
        "gen_text": GEN_TEXT,
        "num_trials_requested": NUM_TRIALS,
        "num_trials_succeeded": len(records),
        "trials": records,
    }
    (OUT / "generation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {len(records)}/{NUM_TRIALS} trials -> {OUT / 'generation.json'}", flush=True)
    if len(records) < NUM_TRIALS:
        sys.exit(1)


if __name__ == "__main__":
    main()
