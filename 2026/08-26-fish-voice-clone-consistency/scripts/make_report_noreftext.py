"""output/noreftext/generation.json + results.json + 第 1 弾 output/results.json から
report-noreftext.md を組み立てる。

usage: python scripts/make_report_noreftext.py > output/report-noreftext.md
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
NOREF = OUT / "noreftext"

gen = json.loads((NOREF / "generation.json").read_text())
res = json.loads((NOREF / "results.json").read_text())
base = json.loads((OUT / "results.json").read_text())  # 第 1 弾ベースライン

lines: list[str] = []
w = lines.append

w("# Fish Audio 日本語 voice clone 書き起こし省略テスト 結果レポート（第 3 弾）")
w("")
w("実施日: 2026-08-26")
w("")
w(
    "第 1 弾（同一 reference + 同一テキスト 5 回、`report.md`）は reference の書き起こしテキストを"
    "渡していた。第 3 弾は **書き起こしを渡さない** 以外を第 1 弾と完全同一条件にし、"
    "ref_text の有無がクローンの忠実度・再現性に効くかを測る。"
)
w("")
w("## 手法")
w("")
w(f'- モデル: `{gen["model"]}`（fish-audio-sdk `Session.tts(backend=...)` → `model` ヘッダ）')
w(
    "- クローン方式: inline zero-shot（`references` に reference wav バイナリのみ）。"
    "fish-audio-sdk の `ReferenceAudio.text` はデフォルトなしの必須フィールドのため、"
    "**書き起こしの代わりに空文字列 `\"\"` を渡した**（フィールド省略は SDK 上不可）"
)
w("- reference audio・生成テキスト・実行条件（5 回逐次・間隔 2 秒・`format=\"wav\"`）は第 1 弾と完全に同一")
w(f'  生成テキスト: 「{gen["gen_text"]}」')
w(
    f'- 実行: {gen["num_trials_requested"]} 回逐次。'
    f'{gen["num_trials_succeeded"]}/{gen["num_trials_requested"]} 成功'
)
w("- 話者類似度: resemblyzer `VoiceEncoder`（256 次元 utterance embedding）のコサイン類似度")
w("- F0: librosa `pyin`（fmin=C2, fmax=C6）の有声フレーム平均・中央値")
w("")
w("## 生成結果（レイテンシ・尺・RMS）")
w("")
w("| trial | latency (s) | duration (s) | samplerate | RMS |")
w("|-------|-------------|--------------|------------|-----|")
for t in gen["trials"]:
    rms = res["per_noref"][f'noref{t["trial"]}']["rms"]
    w(
        f'| {t["trial"]} | {t["latency_sec"]:.2f} | {t["duration_sec"]:.3f} '
        f'| {t["samplerate"]} | {rms:.5f} |'
    )
lat = [t["latency_sec"] for t in gen["trials"]]
ds = res["duration_stats"]
bds = base["duration_stats"]
w("")
w(f"- latency: mean {sum(lat) / len(lat):.2f}s（min {min(lat):.2f}s / max {max(lat):.2f}s）")
w(
    f'- duration: mean {ds["mean"]}s / std {ds["std"]}s / min {ds["min"]}s / max {ds["max"]}s'
    f'（第 1 弾: mean {bds["mean"]}s / std {bds["std"]}s / min {bds["min"]}s / max {bds["max"]}s）'
)
w(
    "- RMS はいずれも 0.09〜0.15 の範囲で、無音・極端な音量異常の trial はない"
)
w("")
w("## 忠実度: ref vs 各 noref のコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["ref_vs_noref_similarity"].items():
    w(f"| ref–{k} | {v:.4f} |")
s = res["ref_vs_noref_stats"]
bs = base["ref_vs_trial_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w(f'（第 1 弾 ref–trial: mean {bs["mean"]} / std {bs["std"]} / min {bs["min"]} / max {bs["max"]}）')
w("")
w("## 再現性: noref 間全 10 ペアのコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["inter_noref_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["inter_noref_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## クロスセット: noref 5 本 × 第 1 弾 trial 5 本の 25 ペア")
w("")
w("| | trial1 | trial2 | trial3 | trial4 | trial5 |")
w("|---|---|---|---|---|---|")
for n in range(1, 6):
    row = [res["cross_set_similarity"][f"noref{n}-trial{r}"] for r in range(1, 6)]
    w(f"| noref{n} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
cs = res["cross_set_stats"]
w("")
w(f'統計: mean {cs["mean"]} / std {cs["std"]} / min {cs["min"]} / max {cs["max"]}')
w("")
w("## 4 群の比較（第 1 弾ベースラインとの並置）")
w("")
bits = base["inter_trial_stats"]
its = res["inter_noref_stats"]
rs = res["ref_vs_noref_stats"]
w("| 群 | 条件 | n | mean | std | min | max |")
w("|----|------|---|------|-----|-----|-----|")
w(
    f'| 第 1 弾 trial 間 | ref_text あり同士 | 10 | {bits["mean"]} | {bits["std"]} '
    f'| {bits["min"]} | {bits["max"]} |'
)
w(
    f'| 第 1 弾 ref–trial | ref_text あり | 5 | {bs["mean"]} | {bs["std"]} '
    f'| {bs["min"]} | {bs["max"]} |'
)
w(f'| ref–noref | ref_text なし | 5 | {rs["mean"]} | {rs["std"]} | {rs["min"]} | {rs["max"]} |')
w(f'| noref 間 | ref_text なし同士 | 10 | {its["mean"]} | {its["std"]} | {its["min"]} | {its["max"]} |')
w(
    f'| クロスセット noref×trial | なし × あり | 25 | {cs["mean"]} | {cs["std"]} '
    f'| {cs["min"]} | {cs["max"]} |'
)
w("")
w("## F0（librosa.pyin、有声フレームのみ）")
w("")
w("| trial | F0 mean (Hz) | F0 median (Hz) | voiced frames |")
w("|-------|--------------|----------------|---------------|")
for i in range(1, 6):
    t = res["per_noref"][f"noref{i}"]
    w(f'| {i} | {t["f0_mean_hz"]:.2f} | {t["f0_median_hz"]:.2f} | {t["voiced_frames"]} |')
f0s = [res["per_noref"][f"noref{i}"]["f0_mean_hz"] for i in range(1, 6)]
w("")
w(
    f"F0 mean の範囲は {min(f0s):.2f}〜{max(f0s):.2f} Hz（幅 {max(f0s) - min(f0s):.2f} Hz）。"
    "第 1 弾 trial は 100.27〜102.62 Hz（幅 2.35 Hz）。"
)
w("")
w("## 類似度行列（11×11）")
w("")
labels = res["similarity_matrix"]["labels"]
w("| | " + " | ".join(labels) + " |")
w("|---" * (len(labels) + 1) + "|")
for label, row in zip(labels, res["similarity_matrix"]["values"]):
    w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
w("")
w("ヒートマップ画像: `noreftext/similarity_heatmap_noreftext.webp`")
w("")
w("## 所感（数値から言える範囲）")
w("")
w(
    f'- ref–noref 類似度（mean {rs["mean"]} ± {rs["std"]}）は第 1 弾の ref–trial'
    f'（mean {bs["mean"]} ± {bs["std"]}）よりわずかに低いが、差は mean で '
    f'{bs["mean"] - rs["mean"]:.4f} と小さく、std を考えると忠実度の明確な劣化とまでは言えない'
)
w(
    f'- noref 間類似度（mean {its["mean"]} ± {its["std"]}）は第 1 弾の trial 間'
    f'（mean {bits["mean"]} ± {bits["std"]}）と同水準。書き起こしを省略しても再現性は変わらない'
)
w(
    f'- クロスセット（mean {cs["mean"]}）も noref 間・第 1 弾 trial 間と同水準で、'
    "書き起こしの有無で別の声になるわけではない（同じクローン声が出ている）"
)
w(
    f'- 音声尺は mean {ds["mean"]}s / std {ds["std"]}s で、第 1 弾（mean {bds["mean"]}s / '
    f'std {bds["std"]}s、レンジ {bds["min"]}〜{bds["max"]}s）よりやや短め・ばらつき大きめ。'
    f'特に trial4 は {ds["min"]}s で第 1 弾の最短 {bds["min"]}s を約 1.4 秒下回る。'
    "話速・間の取り方が振れやすくなっている可能性はあるが、5 本とも RMS は正常で"
    "無音・破綻・極端な尺の逸脱はない"
)
w(
    f"- F0 mean の試行間幅は {max(f0s) - min(f0s):.2f} Hz で、第 1 弾の 2.35 Hz より大きい。"
    "ピッチのぶれも書き起こしなしの方がやや大きい"
)
w("- 本テストは resemblyzer embedding という単一の客観指標に基づく。聴感上の同一性・発音の正確さ（誤読の有無）は別途評価が必要")
w("")

print("\n".join(lines))
