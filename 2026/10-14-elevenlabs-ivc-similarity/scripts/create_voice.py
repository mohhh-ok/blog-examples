"""ref.wav から Instant Voice Clone を 1 つ作り、voice_id を output/voice.json に控える。

- POST /v1/voices/add (multipart: name, files, remove_background_noise=false)
- name は blogtest- で始める (delete_voice.py はこの name と控えた id の両方を照合して消す)

usage: ELEVENLABS_API_KEY=... python scripts/create_voice.py
"""

import json
import time

import requests

from common import API, OUT, REF_WAV, VOICE_JSON, VOICE_NAME, api_key


def main() -> None:
    if VOICE_JSON.exists():
        raise SystemExit(f"error: {VOICE_JSON} already exists (delete the old voice first)")
    OUT.mkdir(parents=True, exist_ok=True)
    r = requests.post(
        f"{API}/v1/voices/add",
        headers={"xi-api-key": api_key()},
        data={
            "name": VOICE_NAME,
            "remove_background_noise": "false",
            "description": "blog test: IVC similarity measurement (temporary)",
        },
        files=[("files", (REF_WAV.name, REF_WAV.read_bytes(), "audio/wav"))],
        timeout=120,
    )
    if r.status_code != 200:
        raise SystemExit(f"error: {r.status_code} {r.text[:300]}")
    res = r.json()
    meta = {
        "voice_id": res["voice_id"],
        "name": VOICE_NAME,
        "requires_verification": res.get("requires_verification"),
        "ref_file": str(REF_WAV.name),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    VOICE_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
