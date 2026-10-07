"""生成音声を gpt-4o-transcribe で「聞こえたとおりのカタカナ」に書き起こす。

通常の書き起こしは誤読を正しい漢字に直してしまうので、読みの判定には使えない (09-24 記事と同じ方針)。
音声は 16kHz mono mp3 に変換してから送る。書き起こし済みの (model, tag) は飛ばす。

env:
  OPENAI_API_KEY (必須)
  OUT_ROOT: 生成音声の置き場 (既定 /tmp/irodori-eval/out)。{OUT_ROOT}/{irodori,fish}/*.wav と ref を読む
  MODELS: カンマ区切り (既定 irodori,fish)
  ONLY: カンマ区切りの model:tag に絞る (不正解行の 2 回目の書き起こし用)
  OUT_NAME: 出力ファイル名 (既定 transcripts.jsonl。2 回目は transcripts-pass2.jsonl)

出力: {OUT_ROOT}/{OUT_NAME} (1 行 1 音声)

usage: python transcribe.py
"""

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/tmp/irodori-eval/out"))
REF_DIR = Path(os.environ.get("REF_DIR", "/tmp/irodori-eval/ref"))
MODELS = os.environ.get("MODELS", "irodori,fish").split(",")
ONLY = set(os.environ["ONLY"].split(",")) if os.environ.get("ONLY") else None
OUT_NAME = os.environ.get("OUT_NAME", "transcripts.jsonl")
ASR_MODEL = "gpt-4o-transcribe"
PROMPT = (
    "日本語の音声です。聞こえたとおりの音を、すべてカタカナで書いてください。"
    "漢字・ひらがな・アルファベット・数字は使わず、数字や英字も読まれた音のとおりカタカナで書いてください。"
    "助詞の「は」「へ」は発音どおり「ワ」「エ」と書いてください。"
    "言い間違いや不自然な読みに聞こえても直さず、聞こえた音のまま書いてください。"
)
NON_KATAKANA = re.compile(r"[^゠-ヿ、。，．・！？\s]")


def to_mp3(wav: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", "16000", "-b:a", "64k", str(dst)],
        check=True,
    )


def main() -> None:
    out_path = OUT_ROOT / OUT_NAME
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["model"], r["tag"]))
    targets = [("ref", p) for p in sorted(REF_DIR.glob("*.wav"))]
    for model in MODELS:
        targets += [(model, p) for p in sorted((OUT_ROOT / model).glob("*.wav"))]
    if ONLY is not None:
        targets = [(m, p) for m, p in targets if f"{m}:{p.stem}" in ONLY]
    headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    with httpx.Client(timeout=120) as client, tempfile.TemporaryDirectory() as tmp, out_path.open("a") as log:
        for model, wav in targets:
            if (model, wav.stem) in done:
                continue
            mp3 = Path(tmp) / f"{model}-{wav.stem}.mp3"
            to_mp3(wav, mp3)
            for attempt in range(3):
                t0 = time.time()
                response = client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    data={"model": ASR_MODEL, "language": "ja", "prompt": PROMPT, "response_format": "json"},
                    files={"file": (mp3.name, mp3.read_bytes(), "audio/mpeg")},
                )
                if response.status_code < 500 and response.status_code != 429:
                    break
                time.sleep(5 * (attempt + 1))
            if response.is_error:
                print(json.dumps({"model": model, "tag": wav.stem, "status": response.status_code, "error": response.text[:300]}), flush=True)
                continue
            text = response.json()["text"]
            rec = {
                "model": model,
                "tag": wav.stem,
                "asr_model": ASR_MODEL,
                "katakana": text,
                "non_katakana_chars": "".join(sorted(set(NON_KATAKANA.findall(text)))),
                "elapsed_s": round(time.time() - t0, 2),
            }
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            print(json.dumps(rec, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
