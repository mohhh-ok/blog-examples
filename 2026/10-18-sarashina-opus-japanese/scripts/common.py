import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 書き直しの追加 10 問（H01〜H10）は PROBLEMS_FILE=data/problems_h.jsonl で回す
PROBLEMS = Path(os.environ.get("PROBLEMS_FILE", ROOT / "data" / "problems.jsonl"))
PROBLEMS_H = ROOT / "data" / "problems_h.jsonl"
OUTPUT = ROOT / "output"
RAW = OUTPUT / "raw"
JUDGE = OUTPUT / "judge"

# 出力のディレクトリ名 → API に送るモデル名
MODELS = {"sarashina": "sarashina3-mini", "opus": "claude-opus-5-5"}
MAX_TOKENS = 8000  # Sarashina の max_completion_tokens の上限。両モデルで揃える
OPUS_EFFORT = "low"
JUDGE_MODEL = "gpt-6.1-sol"


def load_problems(path=None):
    return [json.loads(line) for line in (path or PROBLEMS).read_text().splitlines()]


def answer_text(model_key, pid):
    rec = json.loads((RAW / model_key / f"{pid}.json").read_text())
    body = rec["response"]
    if model_key == "sarashina":
        return body["choices"][0]["message"]["content"]
    return "".join(b["text"] for b in body["content"] if b["type"] == "text")
