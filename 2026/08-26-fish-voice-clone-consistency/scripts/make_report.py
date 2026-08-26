"""output/generation.json + output/results.json から report.md を組み立てる。

usage: python scripts/make_report.py > output/report.md
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

gen = json.loads((OUT / "generation.json").read_text())
res = json.loads((OUT / "results.json").read_text())

lines: list[str] = []
w = lines.append

w("# Fish Audio 日本語 voice clone 再現性テスト 結果レポート")
w("")
w("実施日: 2026-08-26")
w("")
w("## 手法")
w("")
w(f'- モデル: `{gen["model"]}`（fish-audio-sdk `Session.tts(backend=...)` → `model` ヘッダ）')
w("- クローン方式: inline zero-shot（`references` に reference wav バイナリ + 書き起こしテキストを渡す。事前 voice 登録なし）")
w("- reference audio: 約 10.16 秒・24kHz mono・日本語話者。書き起こし:")
w(f'  「{gen["ref_text"]}」')
w("- 生成テキスト（5 回とも完全に同一・固有名詞なし）:")
w(f'  「{gen["gen_text"]}」')
w(
    f'- 実行: {gen["num_trials_requested"]} 回逐次（リクエスト間 2 秒スリープ）、`format="wav"`'
    f'（API 出力そのまま、変換なし）。{gen["num_trials_succeeded"]}/{gen["num_trials_requested"]} 成功'
)
w("- 話者類似度: resemblyzer `VoiceEncoder`（256 次元 utterance embedding）のコサイン類似度")
w("- F0: librosa `pyin`（fmin=C2, fmax=C6）の有声フレーム平均・中央値")
w("")
w("## 生成結果（レイテンシ・尺）")
w("")
w("| trial | latency (s) | duration (s) | samplerate |")
w("|-------|-------------|--------------|------------|")
for t in gen["trials"]:
    w(f'| {t["trial"]} | {t["latency_sec"]:.2f} | {t["duration_sec"]:.3f} | {t["samplerate"]} |')
lat = [t["latency_sec"] for t in gen["trials"]]
ds = res["duration_stats"]
w("")
w(f"- latency: mean {sum(lat) / len(lat):.2f}s（min {min(lat):.2f}s / max {max(lat):.2f}s）")
w(
    f'- duration: mean {ds["mean"]}s / std {ds["std"]}s / min {ds["min"]}s / max {ds["max"]}s'
    f'（変動係数 約 {ds["std"] / ds["mean"] * 100:.1f}%）'
)
w("")
w("## 忠実度: ref vs 各 trial のコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["ref_vs_trial_similarity"].items():
    w(f"| ref–{k} | {v:.4f} |")
s = res["ref_vs_trial_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## 再現性: trial 間全 10 ペアのコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["inter_trial_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["inter_trial_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## F0（librosa.pyin、有声フレームのみ）")
w("")
w("| trial | F0 mean (Hz) | F0 median (Hz) | voiced frames |")
w("|-------|--------------|----------------|---------------|")
for i in range(1, 6):
    t = res["per_trial"][f"trial{i}"]
    w(f'| {i} | {t["f0_mean_hz"]:.2f} | {t["f0_median_hz"]:.2f} | {t["voiced_frames"]} |')
f0s = [res["per_trial"][f"trial{i}"]["f0_mean_hz"] for i in range(1, 6)]
w("")
w(
    f"F0 mean の範囲は {min(f0s):.2f}〜{max(f0s):.2f} Hz"
    f"（幅 {max(f0s) - min(f0s):.2f} Hz、平均比 約 {(max(f0s) - min(f0s)) / (sum(f0s) / len(f0s)) * 100:.1f}%）。"
)
w("")
w("## 類似度行列（6x6）")
w("")
labels = res["similarity_matrix"]["labels"]
w("| | " + " | ".join(labels) + " |")
w("|---" * (len(labels) + 1) + "|")
for label, row in zip(labels, res["similarity_matrix"]["values"]):
    w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
w("")
w("ヒートマップ画像: `similarity_heatmap.webp`")
w("")
w("## 所感（数値から言える範囲）")
w("")
rs = res["ref_vs_trial_stats"]
its = res["inter_trial_stats"]
w(
    f'- trial 間類似度（mean {its["mean"]}）は ref–trial 類似度（mean {rs["mean"]}）より一貫して高い。'
    "5 試行は互いに近い声にまとまっており、reference との差（zero-shot clone による声質のずれ）の方が試行間のぶれより大きい"
)
w(f'- ref–trial 類似度の std は {rs["std"]} と小さく、忠実度は試行によって大きく上下しない')
w(
    f'- 音声尺の std は {ds["std"]}s（mean {ds["mean"]}s）で、同一テキストでも尺は毎回わずかに変わる'
    "（サンプリング生成の非決定性）"
)
w(f"- F0 mean の試行間差は {max(f0s) - min(f0s):.2f} Hz に収まっており、ピッチ帯は安定している")
w(
    f'- trial 間の最小ペア（{its["min"]}）は ref–trial の最小（{rs["min"]}）に近く、'
    "試行間にも一定の声質のぶれは存在する"
)
w("- 本テストは resemblyzer embedding という単一の客観指標に基づく。聴感上の同一性・韻律の自然さは別途評価が必要")
w("")

print("\n".join(lines))
