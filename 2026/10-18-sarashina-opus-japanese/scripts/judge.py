# /// script
# dependencies = ["openai<3.35.1"]  # 3.35.1 は計測日に公開 48 時間未満で手元の Safe-chain が止めたため
# ///
"""GPT にモデル名を伏せて一対比較させる。左右を入れ替えて 2 回判定し、output/judge/<id>_<先に置いたモデル>-first.json に保存する。

判定プロンプトの全文は prompts/judge_rewrite.txt（書き直し）と prompts/judge_general.txt（それ以外）。
書き直しは回答ごとの「意味が保たれているか」と読みやすさの比較だけを答えさせ、勝敗は aggregate.py で決める。
"""
import json
import sys
from datetime import datetime, timezone

from openai import OpenAI

from common import JUDGE, JUDGE_MODEL, ROOT, answer_text, load_problems

CRITERIA = {
    "敬語": "敬語が正しく使われているか、場面と相手にふさわしいか、タスクで指示された内容がすべて含まれているか",
    "自由作文": "日本語として自然か、タスクの指示（字数・読み手・用途）に合っているか、表現の質",
    "要約": "原文の要点を正確に押さえているか（原文にない内容や事実の誤りがないか）、字数の指示に合っているか、日本語として自然か",
    "ニュアンス": "発言の意図の読み取りが日本語話者の一般的な感覚に合っているか、根拠の説明が適切か",
    "漢字の読み": "読みが正しいか、タスクの指示（ひらがなだけ・答えのみ）に従っているか",
}

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer1": {"type": "object", "properties": {"meaning_preserved": {"type": "boolean"}, "issues": {"type": "string"}},
                    "required": ["meaning_preserved", "issues"], "additionalProperties": False},
        "answer2": {"type": "object", "properties": {"meaning_preserved": {"type": "boolean"}, "issues": {"type": "string"}},
                    "required": ["meaning_preserved", "issues"], "additionalProperties": False},
        "readability_better": {"type": "string", "enum": ["1", "2", "tie"]},
        "readability_reason": {"type": "string"},
    },
    "required": ["answer1", "answer2", "readability_better", "readability_reason"],
    "additionalProperties": False,
}
GENERAL_SCHEMA = {
    "type": "object",
    "properties": {"winner": {"type": "string", "enum": ["1", "2", "tie"]}, "reason": {"type": "string"}},
    "required": ["winner", "reason"],
    "additionalProperties": False,
}

ORDERS = [("sarashina", "opus"), ("opus", "sarashina")]


def main():
    only = set(sys.argv[1:])
    client = OpenAI()
    rewrite_tmpl = (ROOT / "prompts" / "judge_rewrite.txt").read_text()
    general_tmpl = (ROOT / "prompts" / "judge_general.txt").read_text()
    JUDGE.mkdir(parents=True, exist_ok=True)
    for p in load_problems():
        if only and p["id"] not in only:
            continue
        for first, second in ORDERS:
            path = JUDGE / f"{p['id']}_{first}-first.json"
            if path.exists():
                continue
            a1, a2 = answer_text(first, p["id"]), answer_text(second, p["id"])
            if p["category"] == "書き直し":
                prompt = rewrite_tmpl.format(task=p["prompt"], answer1=a1, answer2=a2)
                schema = REWRITE_SCHEMA
            else:
                prompt = general_tmpl.format(criteria=CRITERIA[p["category"]], task=p["prompt"], answer1=a1, answer2=a2)
                schema = GENERAL_SCHEMA
            started = datetime.now(timezone.utc).isoformat()
            resp = client.responses.create(
                model=JUDGE_MODEL,
                input=prompt,
                text={"format": {"type": "json_schema", "name": "judgement", "schema": schema, "strict": True}},
            )
            rec = {"id": p["id"], "category": p["category"], "answer1_model": first, "answer2_model": second,
                   "requested_at": started, "judge_model": JUDGE_MODEL, "prompt": prompt,
                   "judgement": json.loads(resp.output_text), "response": resp.model_dump(mode="json")}
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
            print(f"{p['id']} {first}-first judged", flush=True)


if __name__ == "__main__":
    main()
