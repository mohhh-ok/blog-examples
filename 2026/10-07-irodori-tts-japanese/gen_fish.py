"""Fish Audio s2.1-pro で全実験の文を生成する (inline zero-shot clone、参照の書き起こしあり)。

09-24 記事と同じく MessagePack で /v1/tts を直接叩く。生成済みの wav は飛ばすので、途中で止まっても再実行で続きから回る。

env:
  FISH_API_KEY (必須)
  REF_DIR: r10.wav / r26.wav の置き場 (既定 /tmp/billionclips/irodori-eval/ref)
  OUT_DIR: 出力先 (既定 /tmp/billionclips/irodori-eval/out/fish)
  EXPS: カンマ区切りで実験を絞る (既定 B,C,R,N)

usage: python gen_fish.py
"""

import io
import json
import os
import time
import wave
from pathlib import Path

import httpx
import ormsgpack

import texts

MODEL = "s2.1-pro"
REF_DIR = Path(os.environ.get("REF_DIR", "/tmp/billionclips/irodori-eval/ref"))
OUT_DIR = Path(os.environ.get("OUT_DIR", "/tmp/billionclips/irodori-eval/out/fish"))
EXPS = os.environ.get("EXPS", "B,C,R,N").split(",")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "gen_fish.jsonl"
    refs = {name: (REF_DIR / f"{name}.wav").read_bytes() for name in texts.REF_TEXTS}
    todo = [j for j in texts.jobs() if j["exp"] in EXPS]
    failures = 0
    with httpx.Client(timeout=300) as client:
        for job in todo:
            out = OUT_DIR / f"{job['tag']}.wav"
            if out.exists():
                continue
            t0 = time.time()
            response = client.post(
                "https://api.fish.audio/v1/tts",
                content=ormsgpack.packb(
                    {
                        "text": job["text"],
                        # inline zero-shot clone は MessagePack 必須 (JSON 不可)
                        "references": [{"audio": refs[job["ref"]], "text": texts.REF_TEXTS[job["ref"]]}],
                        "format": "wav",
                        "temperature": 0.7,
                        "top_p": 0.7,
                    }
                ),
                headers={
                    "Authorization": f"Bearer {os.environ['FISH_API_KEY']}",
                    "Content-Type": "application/msgpack",
                    "model": MODEL,
                },
            )
            elapsed = time.time() - t0
            record = {**job, "model": MODEL, "elapsed_s": round(elapsed, 2)}
            if response.is_error:
                failures += 1
                record |= {"ok": False, "status": response.status_code, "error": response.text[:500]}
                print(json.dumps(record, ensure_ascii=False), flush=True)
                if failures >= 3:
                    raise SystemExit("3 failures — aborting")
                time.sleep(5)
                continue
            seconds = write_wav(out, response.content)
            record |= {"ok": True, "audio_s": round(seconds, 2), "bytes": len(response.content)}
            with log_path.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(json.dumps(record, ensure_ascii=False), flush=True)
            time.sleep(0.5)


def write_wav(path: Path, body: bytes) -> float:
    """ストリーミング応答の wav はヘッダのフレーム数が仮の最大値なので、data チャンクの実長で書き直す。"""
    header_end = body.find(b"data") + 8
    with wave.open(io.BytesIO(body[:header_end]), "rb") as w:
        params = w.getparams()
    frames = body[header_end:]
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(frames)
    return len(frames) / (params.framerate * params.sampwidth * params.nchannels)


if __name__ == "__main__":
    main()
