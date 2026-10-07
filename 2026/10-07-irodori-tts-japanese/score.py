"""カタカナ書き起こしを JKYB-Parakeet 公式評価ツールキットの score_row で採点する。

正規化 (長音・オ段+ウ 等の吸収) と、対象漢字の範囲を前後の文脈でアライメントする処理は公式実装をそのまま使う。
ASR は公式の kana-whisper ではなく gpt-4o-transcribe なので、数値はモデルカードの値と互換ではない。

PYTHONPATH に jkyb-toolkit の src を通して実行する:
  git clone https://github.com/Parakeet-Inc/Joyo-Kanji-Yomi-Benchmark-Parakeet-Edition.git
  PYTHONPATH=Joyo-Kanji-Yomi-Benchmark-Parakeet-Edition/src python score.py

env: OUT_ROOT (既定 /tmp/billionclips/irodori-eval/out)
入力: {OUT_ROOT}/transcripts.jsonl、任意で {OUT_ROOT}/transcripts-pass2.jsonl (不正解行の 2 回目の書き起こし)
出力: {OUT_ROOT}/scores.json
"""

import json
import os
from pathlib import Path

from jkyb_eval.metrics import score_row
from jkyb_eval.models import BenchmarkRow

import texts

OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/tmp/billionclips/irodori-eval/out"))
MODELS = ("irodori", "fish")
CONTEXT_ERROR_SUSPECT = 0.2


def load_transcripts(name: str) -> dict:
    path = OUT_ROOT / name
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        out[(r["model"], r["tag"])] = r
    return out


def benchmark_rows() -> list[tuple[str, str, BenchmarkRow]]:
    """(exp, tag, row)。N の行は常用漢字の区分に当てはまらないので、判定時だけ区分を on_yomi に置く (集計に区分は使わない)。"""
    tag_by_key = {j["key"]: j["tag"] for j in texts.jobs() if "key" in j}
    out = []
    for exp, name in (("R", "r100"), ("N", "n10")):
        for raw in texts.load_rows(name):
            fixed = raw if exp == "R" else {**raw, "reading_category": "on_yomi"}
            out.append((exp, tag_by_key[raw["key"]], BenchmarkRow.from_dict(fixed, location=raw["key"])))
    return out


def main() -> None:
    pass1 = load_transcripts("transcripts.jsonl")
    pass2 = load_transcripts("transcripts-pass2.jsonl")
    rows = []
    for exp, tag, row in benchmark_rows():
        for model in MODELS:
            t = pass1.get((model, tag))
            s = score_row(row, None if t is None else t["katakana"])
            rec = {
                "exp": exp,
                "model": model,
                "tag": tag,
                "key": row.key,
                "text": row.text,
                "tagged_text": row.tagged_text,
                "reading_category": row.reading_category,
                "accepted": [a["reading"] for a in s["accepted_readings"]],
                "katakana": s["prediction_yomi"],
                "mapped_target": s["mapped_target"],
                "correct": s["target_exact"],
                "relaxed_correct": s["relaxed_target_exact"],
                "target_kana_cer": round(s["target_kana_cer"], 4),
                "sentence_kana_cer": round(s["sentence_kana_cer"], 4),
                "context_error_rate": round(s["alignment_context_error_rate"], 4),
                "alignment_ambiguous": s["alignment_ambiguous"],
                "non_katakana_chars": "" if t is None else t["non_katakana_chars"],
            }
            p2 = pass2.get((model, tag))
            if p2 is not None:
                s2 = score_row(row, p2["katakana"])
                rec |= {"pass2_katakana": p2["katakana"], "pass2_mapped_target": s2["mapped_target"], "pass2_correct": s2["target_exact"]}
            reasons = []
            if rec["non_katakana_chars"]:
                reasons.append(f"カタカナ以外の文字: {rec['non_katakana_chars']}")
            if rec["context_error_rate"] >= CONTEXT_ERROR_SUSPECT:
                reasons.append(f"対象の前後の文脈がずれている (context_error_rate={rec['context_error_rate']})")
            if rec["alignment_ambiguous"]:
                reasons.append("対象範囲のアライメントが曖昧")
            if p2 is not None and rec["pass2_correct"] != rec["correct"]:
                reasons.append("2 回目の書き起こしで判定が変わる")
            rec["asr_suspect"] = reasons
            rows.append(rec)

    summary = {}
    for exp in ("R", "N"):
        for model in MODELS:
            sel = [r for r in rows if r["exp"] == exp and r["model"] == model]
            n = len(sel)
            summary[f"{exp}:{model}"] = {
                "n": n,
                "correct": sum(r["correct"] for r in sel),
                "relaxed_correct": sum(r["relaxed_correct"] for r in sel),
                "accuracy": round(sum(r["correct"] for r in sel) / n, 4),
                "relaxed_accuracy": round(sum(r["relaxed_correct"] for r in sel) / n, 4),
                "mean_target_kana_cer": round(sum(r["target_kana_cer"] for r in sel) / n, 4),
                "mean_sentence_kana_cer": round(sum(r["sentence_kana_cer"] for r in sel) / n, 4),
                "asr_suspect_rows": sum(1 for r in sel if r["asr_suspect"]),
                "correct_excluding_suspect": sum(r["correct"] for r in sel if not r["asr_suspect"]),
                "n_excluding_suspect": sum(1 for r in sel if not r["asr_suspect"]),
            }
    (OUT_ROOT / "scores.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
