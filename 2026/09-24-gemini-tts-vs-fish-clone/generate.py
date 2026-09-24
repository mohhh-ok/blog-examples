# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "ormsgpack"]
# ///
"""Gemini 3.8 Flash TTS と Fish Audio s2.1-pro の比較生成。

参照音声は筆者本人の録音 (ref-source.wav 25.7s / ref-consent.wav 12.8s、24kHz mono s16)。
条件:
  fish-text   : Fish s2.1-pro、references.text に書き起こしを送る
  fish-notext : Fish s2.1-pro、references.text を空文字で送る (スキーマ上は必須。通るかを確認する)
  gemini-flash: gemini-3.8-flash-tts、voice replication (store=False の voicekey)
読み上げ文 S1 は漢字の読み分け、S2 は数字・英字の読みを見る。

env:
  FISH_API_KEY, GEMINI_API_KEY (必須)
  RUNS: 各条件×文の生成回数 (既定 1)
  CONDITIONS: カンマ区切りで条件を絞る (既定 全部)
  OUT_DIR: 出力先 (既定 ~/Downloads/gemini-tts-eval)

使い方: uv run generate.py
"""

import base64
import json
import os
import pathlib
import time

import httpx
import ormsgpack

HERE = pathlib.Path(__file__).parent
REF_SOURCE = HERE / "ref-source.wav"
REF_CONSENT = HERE / "ref-consent.wav"
# gpt-4o-transcribe の書き起こし (言いよどみは書き起こしに出ていない)
REF_TEXT = (
    "こんにちは。音声合成の聞き比べに使う声を録音しています。"
    "朝から少し雨が降っていましたが、午後になって晴れてきました。"
    "駅前の喫茶店で温かいコーヒーを飲みながら、のんびり本を読むのが好きです。"
)
TEXTS = {
    "s1": (
        "市立図書館は日本橋の橋の端に近く、私立大学に通う田中さんたち大人も明日そこへ行き、"
        "東雲の空を静かに眺めながら熟語の勉強をする予定を立てて、夕方には橋を渡って帰った。"
    ),
    "s2": (
        "会議は14時30分に開始し、参加費は4980円、満足度は96.5パーセントでした。"
        "APIとAIを使ったプロジェクトについてミーティングでレビューし、scheduleを確認しました。"
    ),
}
FISH_MODEL = "s2.1-pro"
GEMINI_MODELS = {
    "gemini-flash": "gemini-3.8-flash-tts",
}
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_USAGE: list[dict] = []
ALL_CONDITIONS = ["fish-text", "fish-notext", *GEMINI_MODELS]

RUNS = int(os.environ.get("RUNS", "1"))
CONDITIONS = os.environ.get("CONDITIONS", ",".join(ALL_CONDITIONS)).split(",")
OUT_DIR = pathlib.Path(os.environ.get("OUT_DIR", str(pathlib.Path.home() / "Downloads" / "gemini-tts-eval")))


def main() -> None:
    unknown = set(CONDITIONS) - set(ALL_CONDITIONS)
    if unknown:
        raise SystemExit(f"unknown CONDITIONS: {sorted(unknown)}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    with httpx.Client(timeout=300) as client:
        for condition in CONDITIONS:
            generate = build_generator(client=client, condition=condition)
            for text_id, text in TEXTS.items():
                for run in range(1, RUNS + 1):
                    name = f"{condition}-{text_id}-r{run}.wav"
                    record = {"condition": condition, "text": text_id, "run": run, "file": name}
                    t0 = time.time()
                    try:
                        audio = generate(text)
                    except httpx.HTTPStatusError as error:
                        record |= {"ok": False, "status": error.response.status_code, "error": error.response.text[:2000]}
                    else:
                        (OUT_DIR / name).write_bytes(audio)
                        record |= {"ok": True, "bytes": len(audio)}
                    record["elapsed_s"] = round(time.time() - t0, 2)
                    print(json.dumps(record, ensure_ascii=False), flush=True)
                    results.append(record)
    (OUT_DIR / f"results-{'_'.join(CONDITIONS)}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    if GEMINI_USAGE:
        (OUT_DIR / f"gemini-usage-{'_'.join(CONDITIONS)}.json").write_text(json.dumps(GEMINI_USAGE, ensure_ascii=False, indent=2))


def build_generator(*, client: httpx.Client, condition: str):
    if condition in ("fish-text", "fish-notext"):
        ref_text = REF_TEXT if condition == "fish-text" else ""
        return lambda text: fish_tts(client=client, text=text, ref_text=ref_text)
    model = GEMINI_MODELS[condition]
    t0 = time.time()
    voice_key = gemini_create_voice_key(client=client, model=model)
    print(json.dumps({"condition": condition, "voice_create_s": round(time.time() - t0, 2)}), flush=True)
    return lambda text: gemini_tts(client=client, model=model, voice=voice_key, text=text)


def fish_tts(*, client: httpx.Client, text: str, ref_text: str) -> bytes:
    payload = {
        "text": text,
        # inline zero-shot clone は MessagePack 必須 (JSON 不可)
        "references": [{"audio": REF_SOURCE.read_bytes(), "text": ref_text}],
        "format": "wav",
        "temperature": 0.7,
        "top_p": 0.7,
    }
    response = client.post(
        "https://api.fish.audio/v1/tts",
        content=ormsgpack.packb(payload),
        headers={
            "Authorization": f"Bearer {os.environ['FISH_API_KEY']}",
            "Content-Type": "application/msgpack",
            "model": FISH_MODEL,
        },
    )
    response.raise_for_status()
    return response.content


def gemini_create_voice_key(*, client: httpx.Client, model: str) -> str:
    # store=False: Google 側に voice を保存せず、stateless な voicekey_... を返させる
    body = {
        "store": False,
        "voice": {
            "model": model,
            "type": "replicated",
            "replicated": {
                "source_audio": {"mime_type": "audio/wav", "data": b64(REF_SOURCE)},
                "consent_audio": {"mime_type": "audio/wav", "data": b64(REF_CONSENT)},
            },
        },
    }
    response = client.post(f"{GEMINI_BASE}/voices", json=body, headers=gemini_headers())
    if response.is_error:
        raise SystemExit(f"voice create failed ({model}): {response.status_code} {response.text[:2000]}")
    data = response.json()
    (OUT_DIR / f"voice-create-{model}.json").write_text(
        json.dumps({k: v for k, v in data.items() if k != "key"}, ensure_ascii=False, indent=2)
    )
    return data["key"]


def gemini_tts(*, client: httpx.Client, model: str, voice: str, text: str) -> bytes:
    body = {
        "model": model,
        "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    response = client.post(f"{GEMINI_BASE}/interactions", json=body, headers=gemini_headers())
    response.raise_for_status()
    data = response.json()
    # REST の応答では音声は steps[].content[] の type=audio に入る (SDK の output_audio は SDK 側の便宜プロパティ)
    audios = [
        content["data"]
        for step in data.get("steps", [])
        if step.get("type") == "model_output"
        for content in step.get("content", [])
        if content.get("type") == "audio"
    ]
    if len(audios) != 1:
        raise SystemExit(f"expected 1 audio, got {len(audios)}. skeleton: {json.dumps(skeleton(data), ensure_ascii=False)[:3000]}")
    GEMINI_USAGE.append({"model": model, "text": text[:10], "usage": data.get("usage")})
    return base64.b64decode(audios[0])


def skeleton(value):
    # 音声の base64 などの長い文字列を伏せて、レスポンスの形だけを見る
    if isinstance(value, dict):
        return {key: skeleton(item) for key, item in value.items()}
    if isinstance(value, list):
        return [skeleton(item) for item in value]
    if isinstance(value, str) and len(value) > 200:
        return f"<str len={len(value)}>"
    return value


def gemini_headers() -> dict[str, str]:
    return {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}


def b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


if __name__ == "__main__":
    main()
