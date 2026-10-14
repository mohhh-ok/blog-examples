"""create_voice.py で作った声だけを削除し、一覧から消えたことを確かめる。

- output/voice.json の voice_id と、一覧上の name (blogtest- で始まる) の両方が一致するときだけ消す

usage: ELEVENLABS_API_KEY=... python scripts/delete_voice.py
"""

import json

import requests

from common import API, VOICE_JSON, api_key


def get(path: str) -> dict:
    r = requests.get(f"{API}{path}", headers={"xi-api-key": api_key()}, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> None:
    meta = json.loads(VOICE_JSON.read_text())
    vid, name = meta["voice_id"], meta["name"]
    assert name.startswith("blogtest-"), name
    voice = get(f"/v1/voices/{vid}")
    if voice.get("name") != name:
        raise SystemExit(f"error: name mismatch for {vid}: {voice.get('name')!r} != {name!r}")
    r = requests.delete(f"{API}/v1/voices/{vid}", headers={"xi-api-key": api_key()}, timeout=60)
    print(f"[delete] {vid} {name} -> {r.status_code} {r.text}")
    voices = get("/v2/voices?page_size=100")["voices"]
    remaining = [v["voice_id"] for v in voices]
    print(f"[check] {vid} in list: {vid in remaining}")


if __name__ == "__main__":
    main()
