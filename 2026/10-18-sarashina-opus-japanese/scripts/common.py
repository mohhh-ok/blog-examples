import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = ROOT / "data" / "problems.jsonl"
OUTPUT = ROOT / "output"
RAW = OUTPUT / "raw"
JUDGE = OUTPUT / "judge"

# 出力のディレクトリ名 → API に送るモデル名
MODELS = {"sarashina": "sarashina3-mini", "opus": "claude-opus-5-5"}
MAX_TOKENS = 8000  # Sarashina の max_completion_tokens の上限。両モデルで揃える
OPUS_EFFORT = "low"
JUDGE_MODEL = "gpt-6.1-sol"


def load_problems():
    return [json.loads(line) for line in PROBLEMS.read_text().splitlines()]


def answer_text(model_key, pid):
    rec = json.loads((RAW / model_key / f"{pid}.json").read_text())
    body = rec["response"]
    if model_key == "sarashina":
        return body["choices"][0]["message"]["content"]
    return "".join(b["text"] for b in body["content"] if b["type"] == "text")
