"""IVC の声で、eleven_v4 で 同一文 x 5 / 異文 x 5 / 7 言語 x 1 を生成する。

- POST /v1/text-to-speech/{voice_id}?output_format=wav_24000
- voice_settings・seed・language_code は送らない (既定値のまま。試行間のばらつきも測るため seed なし)
- 出力: output/eleven_v4/{same/trial1..5.wav, varied/text1..5.wav, multilingual/<lang>.wav, generation.json}

usage: ELEVENLABS_API_KEY=... python scripts/generate.py
"""

import json
import sys
import time

import requests
import soundfile as sf

from common import (
    API,
    LANGS,
    ML_TEXTS,
    MODEL,
    OUT,
    SAME_N,
    SAME_TEXT,
    VARIED_TEXTS,
    VOICE_JSON,
    api_key,
)

OUTPUT_FORMAT = "wav_24000"
SLEEP_BETWEEN_SEC = 1


def tts(voice_id: str, model_id: str, text: str, out_path) -> dict:
    t0 = time.time()
    r = requests.post(
        f"{API}/v1/text-to-speech/{voice_id}",
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": api_key()},
        json={"text": text, "model_id": model_id},
        timeout=180,
    )
    latency = time.time() - t0
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    data = r.content
    request_id = r.headers.get("request-id")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    info = sf.info(str(out_path))
    return {
        "file": str(out_path.relative_to(OUT)),
        "text": text,
        "latency_sec": round(latency, 3),
        "duration_sec": round(info.frames / info.samplerate, 3),
        "samplerate": info.samplerate,
        "request_id": request_id,
    }


def main() -> None:
    voice = json.loads(VOICE_JSON.read_text())
    voice_id = voice["voice_id"]
    d = OUT / MODEL
    jobs = [(d / "same" / f"trial{i}.wav", SAME_TEXT) for i in range(1, SAME_N + 1)]
    jobs += [(d / "varied" / f"text{i}.wav", t) for i, t in enumerate(VARIED_TEXTS, 1)]
    jobs += [(d / "multilingual" / f"{lang}.wav", ML_TEXTS[lang]) for lang in LANGS]
    records = []
    for out_path, text in jobs:
        try:
            rec = tts(voice_id, MODEL, text, out_path)
        except RuntimeError as e:
            print(f"[{MODEL}] {out_path.name} FAILED {e}", file=sys.stderr)
            raise SystemExit(1)
        records.append(rec)
        print(f"[{MODEL}] {rec['file']} latency={rec['latency_sec']}s dur={rec['duration_sec']}s", flush=True)
        time.sleep(SLEEP_BETWEEN_SEC)
    meta = {
        "model_id": MODEL,
        "voice_name": voice["name"],
        "output_format": OUTPUT_FORMAT,
        "voice_settings": "not sent (API defaults)",
        "seed": None,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "records": records,
    }
    (d / "generation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {MODEL}: {len(records)} files", flush=True)

if __name__ == "__main__":
    main()
