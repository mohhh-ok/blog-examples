"""判定・機械採点・リクエスト記録を集計して output/results.json と output/results.md に書く。API キー不要。

勝敗の決め方:
- 書き直し: 各判定で、意味が保たれた回答が片方だけならその回答の勝ち、両方保たれていれば読みやすいほうの勝ち、
  両方とも意味が変わっていれば引き分け
- それ以外: GPT の winner をそのまま使う
- 左右を入れ替えた 2 回の判定で勝者が同じならその勝ち、食い違えば引き分け
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

from common import JUDGE, OUTPUT, RAW, answer_text, load_problems

CATEGORIES = ["書き直し", "敬語", "自由作文", "要約", "ニュアンス", "漢字の読み"]


def run_winner(rec):
    """1 回の判定の勝者をモデル名（sarashina / opus / tie）で返す。"""
    j = rec["judgement"]
    if rec["category"] == "書き直し":
        ok1, ok2 = j["answer1"]["meaning_preserved"], j["answer2"]["meaning_preserved"]
        if ok1 and not ok2:
            slot = "1"
        elif ok2 and not ok1:
            slot = "2"
        elif not ok1 and not ok2:
            slot = "tie"
        else:
            slot = j["readability_better"]
    else:
        slot = j["winner"]
    return {"1": rec["answer1_model"], "2": rec["answer2_model"], "tie": "tie"}[slot]


def meaning_flags(rec):
    j = rec["judgement"]
    return {rec["answer1_model"]: j["answer1"]["meaning_preserved"], rec["answer2_model"]: j["answer2"]["meaning_preserved"]}


def normalize_reading(s):
    return re.sub(r"[\s。、．，・「」【】『』\"'.,!?！？]", "", s)


def max_requests_per_minute(starts):
    ts = sorted(datetime.fromisoformat(s).timestamp() for s in starts)
    best, j = 0, 0
    for i in range(len(ts)):
        while ts[i] - ts[j] >= 60:
            j += 1
        best = max(best, i - j + 1)
    return best


NAMES = {"sarashina": "Sarashina3 mini", "opus": "Claude Opus 5.5", "tie": "差なし"}


def human_section(human, key):
    """本人の読みやすさの判定（盲検シート）を、GPT の読みやすさ・意味の判定と並べる。"""
    rows = []
    for pid, h in human.items():
        if h["status"] == "excluded":
            continue
        picked = key[pid][h["readable"]]
        runs = [json.loads((JUDGE / f"{pid}_{first}-first.json").read_text()) for first in ("sarashina", "opus")]
        gpt_read = [{"1": r["answer1_model"], "2": r["answer2_model"], "tie": "tie"}[r["judgement"]["readability_better"]]
                    for r in runs]
        flags = [meaning_flags(r) for r in runs]
        rows.append({"id": pid, "status": h["status"], "line": h["line"], "human_readable": picked,
                     "gpt_readable": gpt_read, "gpt_agrees": [g == picked for g in gpt_read],
                     "gpt_meaning_preserved": {m: [f[m] for f in flags] for m in ("sarashina", "opus")},
                     "gpt_final": run_winner(runs[0]) if run_winner(runs[0]) == run_winner(runs[1]) else "tie"})
    blind = [r for r in rows if r["status"] == "blind"]
    count = Counter(r["human_readable"] for r in blind)
    agree_runs = sum(sum(r["gpt_agrees"]) for r in blind)
    agree_both = sum(all(r["gpt_agrees"]) for r in blind)
    summary = {"blind_problems": [r["id"] for r in blind], "human_readable_count": dict(count),
               "gpt_readability_agree_runs": agree_runs, "gpt_readability_agree_both_runs": agree_both, "rows": rows}

    yn = lambda b: "○" if b else "×"
    md = ["", "## 本人の判定（書き直し、読みやすさのみ）", "",
          "本人は意味の正しさは判定できないと明言したため、本人の判定は読みやすさだけ。意味は GPT の判定を使う。",
          "R06〜R08 は判定なし（対象外）。R01 は盲検でないため参考として別に載せる。", "",
          f"盲検 {len(blind)} 問（{'・'.join(r['id'] for r in blind)}）で本人が読みやすいとしたモデル:", "",
          f"- Sarashina3 mini: {count['sarashina']}", f"- Claude Opus 5.5: {count['opus']}", "",
          f"GPT の読みやすさの判定（各問 2 回、計 {2 * len(blind)} 回）が本人と一致した回数: {agree_runs}。"
          f"2 回とも一致した問題: {agree_both} / {len(blind)}", "",
          "| id | 盲検 | 本人の判定（逐語） | 本人が読みやすいとしたモデル | GPT 読みやすさ 判定1 / 判定2 | 本人と一致 | GPT 意味保持 Sarashina | GPT 意味保持 Opus | GPT の最終結果 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["status"] != "blind", r["id"])):
        md.append(f"| {r['id']} | {'○' if r['status'] == 'blind' else '×（参考）'} | {r['line']} | {NAMES[r['human_readable']]} | "
                  f"{NAMES[r['gpt_readable'][0]]} / {NAMES[r['gpt_readable'][1]]} | {' / '.join(yn(a) for a in r['gpt_agrees'])} | "
                  f"{' / '.join(yn(b) for b in r['gpt_meaning_preserved']['sarashina'])} | "
                  f"{' / '.join(yn(b) for b in r['gpt_meaning_preserved']['opus'])} | {NAMES[r['gpt_final']]} |")
    md += ["", "判定1 は Sarashina を回答 1、判定2 は Opus を回答 1 に置いた判定。GPT の最終結果は、意味の判定を優先して決めた勝敗（引き分けは「差なし」）。"]
    return summary, md


def main():
    problems = load_problems()
    per_problem = []
    tally = defaultdict(Counter)
    meaning_fail = Counter()
    for p in problems:
        runs = [json.loads((JUDGE / f"{p['id']}_{first}-first.json").read_text()) for first in ("sarashina", "opus")]
        winners = [run_winner(r) for r in runs]
        final = winners[0] if winners[0] == winners[1] else "tie"
        tally[p["category"]][final] += 1
        row = {"id": p["id"], "category": p["category"], "run_winners": winners, "final": final}
        if p["category"] == "書き直し":
            flags = [meaning_flags(r) for r in runs]
            row["meaning_preserved"] = {m: [f[m] for f in flags] for m in ("sarashina", "opus")}
            for m in ("sarashina", "opus"):
                # 2 回とも「意味が変わった」と判定されたものを数える
                if not any(row["meaning_preserved"][m]):
                    meaning_fail[m] += 1
        if p["answer"]:
            row["reading"] = {}
            for m in ("sarashina", "opus"):
                out = answer_text(m, p["id"])
                row["reading"][m] = {"output": out, "correct": normalize_reading(out) in p["answer"]}
        opus = json.loads((RAW / "opus" / f"{p['id']}.json").read_text())["response"]
        sara = json.loads((RAW / "sarashina" / f"{p['id']}.json").read_text())["response"]
        row["opus_usage"] = {"output_tokens": opus["usage"]["output_tokens"],
                             "thinking_tokens": opus["usage"].get("output_tokens_details", {}).get("thinking_tokens"),
                             "stop_reason": opus["stop_reason"]}
        row["sarashina_usage"] = {"completion_tokens": sara["usage"]["completion_tokens"],
                                  "finish_reason": sara["choices"][0]["finish_reason"]}
        per_problem.append(row)

    readings = [r for r in per_problem if "reading" in r]
    reading_score = {m: sum(r["reading"][m]["correct"] for r in readings) for m in ("sarashina", "opus")}

    log = [json.loads(line) for line in (OUTPUT / "request_log.jsonl").read_text().splitlines()]
    sara_log = [e for e in log if e["model"] == "sarashina"]
    requests_summary = {
        "sarashina_requests": len(sara_log),
        "sarashina_429": [e for e in sara_log if e["status"] == 429],
        "sarashina_max_requests_in_60s": max_requests_per_minute([e["started_at"] for e in sara_log]),
        "statuses": dict(Counter(f"{e['model']}:{e['status']}" for e in log)),
    }

    results = {
        "tally": {c: dict(tally[c]) for c in CATEGORIES},
        "rewrite_meaning_changed_both_runs": dict(meaning_fail),
        "reading_correct": reading_score,
        "reading_total": len(readings),
        "opus_thinking_tokens_total": sum(r["opus_usage"]["thinking_tokens"] or 0 for r in per_problem),
        "requests": requests_summary,
        "per_problem": per_problem,
    }
    (OUTPUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))

    md = ["# 集計", "", "## カテゴリ別（GPT 判定。左右入替の 2 回で勝者が一致したものだけを勝ちとする）", "",
          "| カテゴリ | 問題数 | Sarashina3 mini 勝ち | Claude Opus 5.5 勝ち | 引き分け |", "|---|---|---|---|---|"]
    total = Counter()
    for c in CATEGORIES:
        t = tally[c]
        n = sum(t.values())
        total.update(t)
        md.append(f"| {c} | {n} | {t['sarashina']} | {t['opus']} | {t['tie']} |")
    md.append(f"| 合計 | {sum(total.values())} | {total['sarashina']} | {total['opus']} | {total['tie']} |")
    md += ["", f"## 漢字の読み（機械採点、{len(readings)} 問）", "",
           f"- Sarashina3 mini: {reading_score['sarashina']} / {len(readings)}",
           f"- Claude Opus 5.5: {reading_score['opus']} / {len(readings)}", "",
           "| id | 正解 | Sarashina3 mini | Claude Opus 5.5 |", "|---|---|---|---|"]
    answers = {p["id"]: p["answer"] for p in problems}
    for r in readings:
        cell = lambda m: f"{r['reading'][m]['output'].strip()} {'○' if r['reading'][m]['correct'] else '×'}"
        md.append(f"| {r['id']} | {' / '.join(answers[r['id']])} | {cell('sarashina')} | {cell('opus')} |")
    md += ["", "## 書き直しで「意味が変わった」と 2 回とも判定された数", "",
           f"- Sarashina3 mini: {meaning_fail['sarashina']} / 10", f"- Claude Opus 5.5: {meaning_fail['opus']} / 10", "",
           "## 問題ごと", "", "| id | カテゴリ | 判定1（Sarashina が回答1） | 判定2（Opus が回答1） | 結果 | Opus thinking tokens |",
           "|---|---|---|---|---|---|"]
    for r in per_problem:
        md.append(f"| {r['id']} | {r['category']} | {r['run_winners'][0]} | {r['run_winners'][1]} | {r['final']} | {r['opus_usage']['thinking_tokens']} |")
    md += ["", "## リクエスト", "",
           f"- Sarashina へのリクエスト数: {requests_summary['sarashina_requests']}（429: {len(requests_summary['sarashina_429'])} 回）",
           f"- Sarashina の任意の 60 秒間の最大リクエスト数: {requests_summary['sarashina_max_requests_in_60s']}",
           f"- Opus の thinking tokens 合計: {results['opus_thinking_tokens_total']}"]
    human_path = OUTPUT / "human_judgement.json"
    if human_path.exists():
        human, md_h = human_section(json.loads(human_path.read_text()), json.loads((OUTPUT / "blind_key.json").read_text()))
        results["human"] = human
        (OUTPUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
        md += md_h
    (OUTPUT / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:14]))


if __name__ == "__main__":
    main()
