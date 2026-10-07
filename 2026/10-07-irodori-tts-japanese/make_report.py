"""計測結果を results/ にまとめ、report.md の数値の節を書く。

入力 (OUT_ROOT 既定 /tmp/irodori-eval):
  results/{gen_irodori.json, similarity.json, seed_md5.json}  … Pod (eval_irodori.py) の出力
  out/fish/gen_fish.jsonl, out/transcripts.jsonl, out/transcripts-pass2.jsonl, out/scores.json
出力:
  results/*.json (公開用のコピー。Irodori の生成記録から冗長な messages を落とす)
  report-numbers.md (report.md に貼る数値の表)

usage: python make_report.py
"""

import json
import os
import shutil
import statistics as st
from pathlib import Path

import texts

ROOT = Path(os.environ.get("OUT_ROOT", "/tmp/irodori-eval"))
HERE = Path(__file__).parent
RES = HERE / "results"


def stats(values: list[float]) -> str:
    return f"{min(values):.4f}〜{max(values):.4f} (mean {st.mean(values):.4f} / std {st.pstdev(values):.4f}, n={len(values)})"


def main() -> None:
    RES.mkdir(exist_ok=True)
    gen = json.loads((ROOT / "results/gen_irodori.json").read_text())
    for r in gen["records"]:
        r.pop("messages", None)
    (RES / "gen_irodori.json").write_text(json.dumps(gen, ensure_ascii=False, indent=2))
    fish = [json.loads(line) for line in (ROOT / "out/fish/gen_fish.jsonl").read_text().splitlines()]
    (RES / "gen_fish.json").write_text(json.dumps(fish, ensure_ascii=False, indent=2))
    for name in ("similarity.json", "seed_md5.json"):
        shutil.copy(ROOT / "results" / name, RES / name)
    for name in ("transcripts.jsonl", "transcripts-pass2.jsonl", "scores.json"):
        shutil.copy(ROOT / "out" / name, RES / name)

    sim = json.loads((RES / "similarity.json").read_text())
    seed = json.loads((RES / "seed_md5.json").read_text())
    scores = json.loads((RES / "scores.json").read_text())
    tr = {(r["model"], r["tag"]): r["katakana"] for r in map(json.loads, (RES / "transcripts.jsonl").read_text().splitlines())}
    md = []

    md += ["## 読み精度 (R: JKYB-Parakeet 100 文 / N: 数字・英字 10 文)", ""]
    md += ["| 実験 | モデル | 正解 (natural) | 正解 (natural+marginal) | 平均 Target Kana-CER | 平均 Sentence Kana-CER | 書き起こし誤りの疑い | 疑い行を除いた正解 |", "|---|---|---|---|---|---|---|---|"]
    for key, v in scores["summary"].items():
        exp, model = key.split(":")
        md.append(
            f"| {exp} | {model} | {v['correct']}/{v['n']} ({v['accuracy']:.0%}) | {v['relaxed_correct']}/{v['n']} | {v['mean_target_kana_cer']:.4f} | {v['mean_sentence_kana_cer']:.4f} | {v['asr_suspect_rows']} | {v['correct_excluding_suspect']}/{v['n_excluding_suspect']} |"
        )
    md += ["", "### 不正解 (natural 不一致) の行と、書き起こし誤りの疑いがある行", ""]
    md += ["| 実験 | モデル | tag | 文 (<> が判定対象) | 正解の読み | 判定に使った読み | 1 回目の書き起こし | 2 回目の書き起こし | 疑いの理由 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in scores["rows"]:
        if r["correct"] and not r["asr_suspect"]:
            continue
        md.append(
            f"| {r['exp']} | {r['model']} | {r['tag']} | {r['tagged_text']} | {' / '.join(r['accepted'])} | {r['mapped_target'] or '(無し)'} | {r['katakana']} | {r.get('pass2_katakana', '')} | {'; '.join(r['asr_suspect'])} |"
        )

    md += ["", "## 声の似方 (resemblyzer、生成に使った参照音声とのコサイン類似度)", ""]
    md += ["| 対象 | Irodori | Fish |", "|---|---|---|"]
    for ref in ("r10", "r26"):
        row = []
        for model in ("irodori", "fish"):
            row.append(stats([sim["ref_vs"][f"{model}:b_{ref}_run{i}"] for i in range(1, 6)]))
        md.append(f"| B 同じ文 5 回 vs {ref} | {row[0]} | {row[1]} |")
    for exp, prefix in (("C", "c"), ("R", "r"), ("N", "n")):
        row = []
        for model in ("irodori", "fish"):
            vals = [v for k, v in sim["ref_vs"].items() if k.startswith(f"{model}:{prefix}") and k.split(":")[1][1:2].isdigit()]
            row.append(stats(vals))
        md.append(f"| {exp} vs r10 | {row[0]} | {row[1]} |")
    md += ["", "| B 試行間 (5 本の 10 ペア) | Irodori | Fish |", "|---|---|---|"]
    for ref in ("r10", "r26"):
        md.append(f"| {ref} | {stats(list(sim['b_pairwise'][f'irodori:{ref}'].values()))} | {stats(list(sim['b_pairwise'][f'fish:{ref}'].values()))} |")

    md += ["", "## seed 固定 (Irodori、seed=42 で 2 回)", "", "| 参照 | 1 回目 MD5 | 2 回目 MD5 | 一致 | ref 比類似度 | 書き起こし 1 回目 / 2 回目 |", "|---|---|---|---|---|---|"]
    for ref, v in seed.items():
        md.append(
            f"| {ref} | `{v['md5_1']}` | `{v['md5_2']}` | {v['identical']} | {sim['ref_vs'][f'irodori:seed_{ref}_1']} / {sim['ref_vs'][f'irodori:seed_{ref}_2']} | {tr[('irodori', f'seed_{ref}_1')]} / {tr[('irodori', f'seed_{ref}_2')]} |"
        )

    recs = gen["records"]
    md += ["", "## 速度 (Irodori、RTX 4090、fp32、40 RF steps)", ""]
    md.append(f"- モデル読み込み: {gen['load_s']} 秒 (重み・codec をキャッシュ済みの 2 回目。初回の動作確認ではダウンロード 10.1 秒 + 読み込み 20.1 秒)")
    md.append(f"- 透かし (SilentCipher): {gen['watermark']}")
    md.append(f"- RTF (生成秒 / 音声秒) 全 {len(recs)} 本: {stats([r['rtf'] for r in recs])}")
    for exp in ("B", "seed", "C", "R", "N"):
        sel = [r for r in recs if r["exp"] == exp]
        md.append(f"  - {exp}: RTF {stats([r['rtf'] for r in sel])}、音声 {min(r['audio_s'] for r in sel):.2f}〜{max(r['audio_s'] for r in sel):.2f} 秒")
    md.append(f"- 合計: 音声 {sum(r['audio_s'] for r in recs):.1f} 秒を {sum(r['gen_s'] for r in recs):.1f} 秒で生成")
    md.append(f"- 参考 Fish API (応答時間 / 音声秒、ネットワーク込み) 全 {len(fish)} 本: {stats([r['elapsed_s'] / r['audio_s'] for r in fish])}")

    md += ["", "## 全文の書き起こし (C と N)", "", "| tag | 文 | Irodori | Fish |", "|---|---|---|---|"]
    for j in texts.jobs():
        if j["exp"] in ("C", "N"):
            md.append(f"| {j['tag']} | {j['text']} | {tr[('irodori', j['tag'])]} | {tr[('fish', j['tag'])]} |")
    md += ["", "R の 100 文の書き起こしと判定は results/scores.json の rows にある。", ""]
    (HERE / "report-numbers.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
