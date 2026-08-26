"""output/varied/generation.json + output/varied/results.json + 第 1 弾の
output/results.json から report-varied.md を組み立てる。

usage: python scripts/make_report_varied.py > output/report-varied.md
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
VARIED = OUT / "varied"

gen = json.loads((VARIED / "generation.json").read_text())
res = json.loads((VARIED / "results.json").read_text())
base = json.loads((OUT / "results.json").read_text())  # 第 1 弾 (同一テキスト 5 回)

lines: list[str] = []
w = lines.append

w("# Fish Audio 日本語 voice clone テキスト変動テスト 結果レポート（第 2 弾）")
w("")
w("実施日: 2026-08-26")
w("")
w("第 1 弾（同一 reference + 同一テキスト 5 回、`report.md`）に続き、"
  "「文章が変わっても声が維持されるか」を測る。同一 reference で互いに異なる"
  "日本語テキスト 5 種を各 1 回生成し、話者類似度を第 1 弾ベースラインと比較する。")
w("")
w("## 手法")
w("")
w(f'- モデル: `{gen["model"]}`（fish-audio-sdk `Session.tts(backend=...)` → `model` ヘッダ）。'
  "クローン方式・reference・実行条件は第 1 弾と完全に同一")
w("- クローン方式: inline zero-shot（`references` に reference wav バイナリ + 書き起こしテキストを渡す。事前 voice 登録なし）")
w("- reference audio: 約 10.16 秒・24kHz mono・日本語話者。書き起こし:")
w(f'  「{gen["ref_text"]}」')
w("- 生成テキスト: 互いに異なる日本語 5 種（各 3 文・同程度の長さ・固有名詞なし）を各 1 回")
w(f'- 実行: {gen["num_texts_requested"]} 回逐次（リクエスト間 2 秒スリープ）、`format="wav"`'
  f'（API 出力そのまま、変換なし）。{gen["num_texts_succeeded"]}/{gen["num_texts_requested"]} 成功')
w("- 話者類似度: resemblyzer `VoiceEncoder`（256 次元 utterance embedding）のコサイン類似度")
w("- F0: librosa `pyin`（fmin=C2, fmax=C6）の有声フレーム平均・中央値")
w("")
w("## 生成テキスト")
w("")
for t in gen["texts"]:
    w(f'- text{t["text_id"]}（{t["text_chars"]} 字）: 「{t["text"]}」')
w("")
w("## 生成結果（レイテンシ・尺）")
w("")
w("| text | latency (s) | duration (s) | samplerate |")
w("|------|-------------|--------------|------------|")
for t in gen["texts"]:
    w(f'| {t["text_id"]} | {t["latency_sec"]:.2f} | {t["duration_sec"]:.3f} | {t["samplerate"]} |')
lat = [t["latency_sec"] for t in gen["texts"]]
ds = res["duration_stats"]
w("")
w(f"- latency: mean {sum(lat) / len(lat):.2f}s（min {min(lat):.2f}s / max {max(lat):.2f}s）")
w(f'- duration: mean {ds["mean"]}s / std {ds["std"]}s / min {ds["min"]}s / max {ds["max"]}s'
  "（テキストが異なるため尺のばらつきは内容差由来が主）")
w("")
w("## 忠実度: ref vs 各 text のコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["ref_vs_text_similarity"].items():
    w(f"| ref–{k} | {v:.4f} |")
s = res["ref_vs_text_stats"]
b = base["ref_vs_trial_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w(f'（第 1 弾 ref–trial: mean {b["mean"]} / std {b["std"]} / min {b["min"]} / max {b["max"]}）')
w("")
w("## 一貫性: text 間全 10 ペアのコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["inter_text_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["inter_text_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## クロスセット: text 5 本 × 第 1 弾 trial 5 本の 25 ペア")
w("")
w("| | trial1 | trial2 | trial3 | trial4 | trial5 |")
w("|---|---|---|---|---|---|")
for t in range(1, 6):
    row = [res["cross_set_similarity"][f"text{t}-trial{r}"] for r in range(1, 6)]
    w(f"| text{t} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
s = res["cross_set_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## 4 群の比較（第 1 弾ベースラインとの並置）")
w("")
w("| 群 | 条件 | n | mean | std | min | max |")
w("|----|------|---|------|-----|-----|-----|")
bt = base["inter_trial_stats"]
rv = res["ref_vs_text_stats"]
it = res["inter_text_stats"]
cs = res["cross_set_stats"]
w(f'| 第 1 弾 trial 間 | 同一テキスト同士 | 10 | {bt["mean"]} | {bt["std"]} | {bt["min"]} | {bt["max"]} |')
w(f'| 第 1 弾 ref–trial | 異テキスト（ref は独自文章） | 5 | {b["mean"]} | {b["std"]} | {b["min"]} | {b["max"]} |')
w(f'| ref–text | 異テキスト（ref は独自文章） | 5 | {rv["mean"]} | {rv["std"]} | {rv["min"]} | {rv["max"]} |')
w(f'| text 間 | 異テキスト同士 | 10 | {it["mean"]} | {it["std"]} | {it["min"]} | {it["max"]} |')
w(f'| クロスセット text×trial | 異テキスト同士 | 25 | {cs["mean"]} | {cs["std"]} | {cs["min"]} | {cs["max"]} |')
w("")
w("## F0（librosa.pyin、有声フレームのみ）")
w("")
w("| text | F0 mean (Hz) | F0 median (Hz) | voiced frames |")
w("|------|--------------|----------------|---------------|")
for i in range(1, 6):
    t = res["per_text"][f"text{i}"]
    w(f'| {i} | {t["f0_mean_hz"]:.2f} | {t["f0_median_hz"]:.2f} | {t["voiced_frames"]} |')
f0s = [res["per_text"][f"text{i}"]["f0_mean_hz"] for i in range(1, 6)]
bf0s = [base["per_trial"][f"trial{i}"]["f0_mean_hz"] for i in range(1, 6)]
w("")
w(f"F0 mean の範囲は {min(f0s):.2f}〜{max(f0s):.2f} Hz"
  f"（幅 {max(f0s) - min(f0s):.2f} Hz）。第 1 弾 trial は {min(bf0s):.2f}〜{max(bf0s):.2f} Hz"
  f"（幅 {max(bf0s) - min(bf0s):.2f} Hz）。")
w("")
w("## 類似度行列（11×11）")
w("")
labels = res["similarity_matrix"]["labels"]
w("| | " + " | ".join(labels) + " |")
w("|---" * (len(labels) + 1) + "|")
for label, row in zip(labels, res["similarity_matrix"]["values"]):
    w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
w("")
w("ヒートマップ画像: `varied/similarity_heatmap_11x11.webp`")
w("")
w("## 指標の限界（重要）")
w("")
w("resemblyzer の utterance embedding は話者性を主に捉えるが、音素内容（何を喋っているか）の"
  "影響を完全には除去できない。したがって「文章が違う出力同士の類似度低下」には、"
  "**声質の変化**と**音素内容の差**の両方が混ざっており、この 2 つを本測定だけで分離することは"
  "できない。異テキスト間の類似度が同一テキスト間より低くても、それを直ちに"
  "「文章によって声が変わった」と断定はできない。")
w("")
w("解釈の補助線として、ref はどの生成物とも文章が異なる（ref の書き起こしは生成テキストの"
  "いずれとも別内容）。そのため ref–生成物の類似度は常に「声質差 + 音素内容差」を含んだ値であり、"
  "この値が第 1 弾と第 2 弾で同水準なら、忠実度（reference の声への近さ）は文章に依存して"
  "劣化していないと言える。")
w("")
w("## 所感（数値から言える範囲）")
w("")
w(f'- ref–text 類似度（mean {rv["mean"]} ± {rv["std"]}）は第 1 弾の ref–trial'
  f'（mean {b["mean"]} ± {b["std"]}）と同水準。reference への忠実度は文章が変わっても維持されている')
w(f'- text 間類似度（mean {it["mean"]}）は第 1 弾の同一テキスト trial 間（mean {bt["mean"]}）を'
  "下回っておらず、クロスセット"
  f'（mean {cs["mean"]}）も同水準。異テキスト化による類似度の低下は本測定では観測されていない。'
  "なお異テキストのペアには音素内容差が混入するため、仮に低下が出た場合でも"
  "声質のぶれの上限値として読む必要がある（「指標の限界」参照）")
w(f'- 全 40 ペア（text 間 10 + クロス 25 + ref–text 5）の最小値は '
  f'{min(it["min"], cs["min"], rv["min"])} で、崩壊的な声の変化（別人化）は観測されていない')
w("- 本テストは resemblyzer embedding という単一の客観指標に基づく。聴感上の同一性・韻律の自然さは別途評価が必要")
w("")

print("\n".join(lines))
