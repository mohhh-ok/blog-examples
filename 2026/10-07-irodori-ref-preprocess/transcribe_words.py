"""第1弾の生成音声を gpt-4o-transcribe でカタカナ書き起こしし、transcripts.jsonl と result.md を書く。
書き起こし方法は前編 10-07-irodori-tts-japanese/transcribe.py と同じ (16kHz mono mp3、同じ prompt、language=ja)。
usage: OPENAI_API_KEY=... python transcribe_words.py <wav_dir> <out_dir>
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ASR_MODEL = "gpt-4o-transcribe"
PROMPT = (
    "日本語の音声です。聞こえたとおりの音を、すべてカタカナで書いてください。"
    "漢字・ひらがな・アルファベット・数字は使わず、数字や英字も読まれた音のとおりカタカナで書いてください。"
    "助詞の「は」「へ」は発音どおり「ワ」「エ」と書いてください。"
    "言い間違いや不自然な読みに聞こえても直さず、聞こえた音のまま書いてください。"
)
TEXTS = {
    "w1": "清水寺",
    "w2": "鹿苑寺",
    "s1": "京都の清水寺を訪れました。",
    "s2": "清水寺の舞台から、京都の街を見渡せます。",
    "s3": "鹿苑寺は、金閣寺の名前で知られています。",
    "s4": "次は鹿苑寺へ向かいましょう。",
}
TARGET = {"w1": "清水寺", "s1": "清水寺", "s2": "清水寺", "w2": "鹿苑寺", "s3": "鹿苑寺", "s4": "鹿苑寺"}
READING = {"清水寺": "キヨミズデラ", "鹿苑寺": "ロクオンジ"}


def transcribe(client: httpx.Client, wav: Path, tmp: Path) -> str:
    mp3 = tmp / f"{wav.stem}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", "16000", "-b:a", "64k", str(mp3)], check=True)
    for attempt in range(3):
        response = client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            data={"model": ASR_MODEL, "language": "ja", "prompt": PROMPT, "response_format": "json"},
            files={"file": (mp3.name, mp3.read_bytes(), "audio/mpeg")},
        )
        if response.status_code < 500 and response.status_code != 429:
            break
        time.sleep(5 * (attempt + 1))
    response.raise_for_status()
    return response.json()["text"]


def main() -> None:
    wav_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    with httpx.Client(timeout=120) as client, tempfile.TemporaryDirectory() as tmp:
        for tid in TEXTS:
            for seed in (1, 2, 3):
                wav = wav_dir / f"{tid}-s{seed}.wav"
                text = transcribe(client, wav, Path(tmp))
                reading = READING[TARGET[tid]]
                ok = reading in text.replace(" ", "").replace("　", "")
                rows.append({"id": tid, "seed": seed, "text": TEXTS[tid], "target": TARGET[tid], "expected": reading, "katakana": text, "ok": ok})
                print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    (out_dir / "transcripts.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    lines = [
        "# Irodori-TTS v4.1-Small: 清水寺 / 鹿苑寺 の読み",
        "",
        "正誤は、書き起こし (空白除去後) に正解の読み (清水寺=キヨミズデラ、鹿苑寺=ロクオンジ) が含まれるかで判定した。",
        "",
        "| 文id | seed | 入力文 | 書き起こし (生) | 正誤 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {r['seed']} | {r['text']} | {r['katakana']} | {'正' if r['ok'] else '誤'} |")
    lines.append("")
    for word in READING:
        sub = [r for r in rows if r["target"] == word]
        lines.append(f"- {word} ({READING[word]}): {sum(r['ok'] for r in sub)} / {len(sub)} 正")
    (out_dir / "result.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
