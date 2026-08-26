"""第 6 弾 A/B 生成: inline references (A) vs reference_id (B)。

- 同一文 SAME_TEXT × 5 回 + 異文 VARIED_TEXTS 10 本を、テキストごとに
  A → B の対で生成 (時間帯ドリフトを条件間で均す)
- model=s2.1-pro (backend 引数)、format=wav、temperature/top_p は SDK 既定値
  (0.7/0.7) のまま両条件共通 — 第 1〜5 弾と同値
- 出力: output/voiceid_ab/{a,b}_same{1..5}.wav, {a,b}_text{1..10}.wav, generation.json

usage: python generate_voiceid_ab.py <model_id>
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common_voiceid_ab import (
    MODEL,
    REF_TEXT,
    REF_WAV,
    RESULTS_DIR,
    SAME_TEXT,
    SLEEP_BETWEEN_SEC,
    VARIED_TEXTS,
    WAV_DIR,
    get_api_key,
)

import soundfile as sf
from fish_audio_sdk import ReferenceAudio, Session, TTSRequest


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: generate_voiceid_ab.py <model_id>", file=sys.stderr)
        sys.exit(2)
    model_id = sys.argv[1]
    api_key = get_api_key()
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    session = Session(api_key)
    ref_audio = REF_WAV.read_bytes()
    print(
        f"[init] model={MODEL} ref={REF_WAV.name} ({len(ref_audio)} bytes) "
        f"reference_id={model_id}",
        flush=True,
    )

    # (condition, name, text) の生成計画。対 (A→B) で回す
    plan: list[tuple[str, str, str]] = []
    for i in range(1, 6):
        plan.append(("a", f"a_same{i}", SAME_TEXT))
        plan.append(("b", f"b_same{i}", SAME_TEXT))
    for i, text in enumerate(VARIED_TEXTS, start=1):
        plan.append(("a", f"a_text{i}", text))
        plan.append(("b", f"b_text{i}", text))

    records = []
    consecutive_failures = 0

    for idx, (cond, name, text) in enumerate(plan):
        out_path = WAV_DIR / f"{name}.wav"
        if out_path.exists():
            print(f"[{name}] exists — skip", flush=True)
            continue
        if cond == "a":
            req = TTSRequest(
                text=text,
                references=[ReferenceAudio(audio=ref_audio, text=REF_TEXT)],
                format="wav",
            )
        else:
            req = TTSRequest(
                text=text,
                reference_id=model_id,
                format="wav",
            )
        t0 = time.time()
        try:
            with open(out_path, "wb") as f:
                for chunk in session.tts(req, backend=MODEL):
                    f.write(chunk)
        except Exception as e:  # noqa: BLE001
            consecutive_failures += 1
            print(f"[{name}] FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            out_path.unlink(missing_ok=True)
            if consecutive_failures >= 3:
                print("error: 3 consecutive failures — aborting", file=sys.stderr)
                _write_meta(model_id, records)
                sys.exit(1)
            time.sleep(SLEEP_BETWEEN_SEC)
            continue

        consecutive_failures = 0
        latency = time.time() - t0
        info = sf.info(str(out_path))
        duration = info.frames / info.samplerate
        records.append(
            {
                "name": name,
                "condition": cond,
                "text_chars": len(text),
                "latency_sec": round(latency, 3),
                "duration_sec": round(duration, 3),
                "samplerate": info.samplerate,
                "bytes": out_path.stat().st_size,
            }
        )
        print(
            f"[{name}] latency={latency:.2f}s duration={duration:.3f}s",
            flush=True,
        )
        if idx < len(plan) - 1:
            time.sleep(SLEEP_BETWEEN_SEC)

    _write_meta(model_id, records)
    print(f"[done] {len(records)}/{len(plan)} -> {RESULTS_DIR / 'generation.json'}", flush=True)


def _write_meta(model_id: str, records: list[dict]) -> None:
    meta = {
        "model": MODEL,
        "reference_id": model_id,
        "ref_file": REF_WAV.name,
        "ref_text": REF_TEXT,
        "same_text": SAME_TEXT,
        "varied_texts": VARIED_TEXTS,
        "tts_params": {"temperature": 0.7, "top_p": 0.7, "note": "SDK defaults, 両条件共通"},
        "records": records,
    }
    (RESULTS_DIR / "generation.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
