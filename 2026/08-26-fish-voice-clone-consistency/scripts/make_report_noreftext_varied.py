"""output/noreftext_varied/generation.json + results.json と、
第 1〜3 弾の results.json から report-noreftext-varied.md を組み立てる。

usage: python scripts/make_report_noreftext_varied.py > output/report-noreftext-varied.md
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
NV = OUT / "noreftext_varied"

gen = json.loads((NV / "generation.json").read_text())
res = json.loads((NV / "results.json").read_text())
base1 = json.loads((OUT / "results.json").read_text())  # 第 1 弾
base2 = json.loads((OUT / "varied" / "results.json").read_text())  # 第 2 弾
base3 = json.loads((OUT / "noreftext" / "results.json").read_text())  # 第 3 弾

lines: list[str] = []
w = lines.append

w("# Fish Audio 日本語 voice clone 書き起こし省略 × テキスト変動テスト 結果レポート（第 4 弾）")
w("")
w("実施日: 2026-08-26")
w("")
w(
    "第 2 弾（書き起こしあり × 異テキスト 5 種、`report-varied.md`）・第 3 弾"
    "（書き起こしなし × 同一テキスト 5 回、`report-noreftext.md`）に続き、"
    "**書き起こしなし × 異テキスト** を測る。生成テキストは第 2 弾と完全同一の 5 種、"
    "reference の扱いは第 3 弾と同一（書き起こしを渡さない）。これで "
    "ref_text 有無 × 同一文/異文の 2×2 実験マトリクスが完成する。"
)
w("")
w("## 手法")
w("")
w(f'- モデル: `{gen["model"]}`（fish-audio-sdk `Session.tts(backend=...)` → `model` ヘッダ）')
w(
    "- クローン方式: inline zero-shot（`references` に reference wav バイナリのみ）。"
    "fish-audio-sdk の `ReferenceAudio.text` はデフォルトなしの必須フィールドのため、"
    "**書き起こしの代わりに空文字列 `\"\"` を渡した**（第 3 弾と同一方式）"
)
w("- 生成テキスト: 第 2 弾と完全同一の日本語 5 種（各 3 文・同程度の長さ・固有名詞なし）を各 1 回")
w("- 実行条件: 5 回逐次・リクエスト間 2 秒・`format=\"wav\"`（第 2・3 弾と同一）。"
  f'{gen["num_texts_succeeded"]}/{gen["num_texts_requested"]} 成功')
w("- 話者類似度: resemblyzer `VoiceEncoder`（256 次元 utterance embedding）のコサイン類似度")
w("- F0: librosa `pyin`（fmin=C2, fmax=C6）の有声フレーム平均・中央値")
w("")
w("## 生成テキスト")
w("")
for t in gen["texts"]:
    w(f'- text{t["text_id"]}（{t["text_chars"]} 字）: 「{t["text"]}」')
w("")
w("## 生成結果（レイテンシ・尺・RMS）")
w("")
w("| text | latency (s) | duration (s) | samplerate | RMS |")
w("|------|-------------|--------------|------------|-----|")
for t in gen["texts"]:
    rms = res["per_nv"][f'nv{t["text_id"]}']["rms"]
    w(
        f'| {t["text_id"]} | {t["latency_sec"]:.2f} | {t["duration_sec"]:.3f} '
        f'| {t["samplerate"]} | {rms:.5f} |'
    )
lat = [t["latency_sec"] for t in gen["texts"]]
ds = res["duration_stats"]
b2ds = base2["duration_stats"]
w("")
w(f"- latency: mean {sum(lat) / len(lat):.2f}s（min {min(lat):.2f}s / max {max(lat):.2f}s）")
w(
    f'- duration: mean {ds["mean"]}s / std {ds["std"]}s / min {ds["min"]}s / max {ds["max"]}s'
    f'（第 2 弾の同一テキスト群: mean {b2ds["mean"]}s / std {b2ds["std"]}s / '
    f'min {b2ds["min"]}s / max {b2ds["max"]}s）'
)
low_rms = [
    (k, v["rms"]) for k, v in res["per_nv"].items() if v["rms"] < 0.09
]
if low_rms:
    w(
        "- RMS: "
        + "、".join(f"{k} は {v:.5f}" for k, v in low_rms)
        + " と基準の 0.09 をわずかに下回った（過去 3 実験のレンジは 0.09〜0.15）。"
        "無音・破綻ではないが音量は小さめに出ている"
    )
else:
    w("- RMS はいずれも 0.09〜0.15 の範囲で、無音・極端な音量異常の trial はない")
w("")
w("## 忠実度: ref vs 各 nv のコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["ref_vs_nv_similarity"].items():
    w(f"| ref–{k} | {v:.4f} |")
s = res["ref_vs_nv_stats"]
b2s = base2["ref_vs_text_stats"]
b3s = base3["ref_vs_noref_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w(
    f'（第 2 弾 ref–text: mean {b2s["mean"]} / std {b2s["std"]}、'
    f'第 3 弾 ref–noref: mean {b3s["mean"]} / std {b3s["std"]}）'
)
w("")
w("## 一貫性: nv 間全 10 ペアのコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["inter_nv_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["inter_nv_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## クロス A: nv 5 本 × 第 2 弾 text 5 本の 25 ペア（ref_text 有無をまたぐ）")
w("")
w("| | text1 | text2 | text3 | text4 | text5 |")
w("|---|---|---|---|---|---|")
for n in range(1, 6):
    row = [res["cross_a_nv_vs_text_similarity"][f"nv{n}-text{t}"] for t in range(1, 6)]
    w(f"| nv{n} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
ca = res["cross_a_stats"]
w("")
w(f'統計: mean {ca["mean"]} / std {ca["std"]} / min {ca["min"]} / max {ca["max"]}')
w("")
w("同一文章同士のペア（nv_i–text_i、書き起こし有無だけが違う）:")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["cross_a_same_text_pairs"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
cas = res["cross_a_same_text_stats"]
w("")
w(f'統計: mean {cas["mean"]} / std {cas["std"]} / min {cas["min"]} / max {cas["max"]}')
w("")
w("## クロス B: nv 5 本 × 第 3 弾 noref 5 本の 25 ペア（ref_text なし同士・文章をまたぐ）")
w("")
w("| | noref1 | noref2 | noref3 | noref4 | noref5 |")
w("|---|---|---|---|---|---|")
for n in range(1, 6):
    row = [res["cross_b_nv_vs_noref_similarity"][f"nv{n}-noref{r}"] for r in range(1, 6)]
    w(f"| nv{n} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
cb = res["cross_b_stats"]
w("")
w(f'統計: mean {cb["mean"]} / std {cb["std"]} / min {cb["min"]} / max {cb["max"]}')
w("")
w("## 群の比較（第 2・3 弾との並置）")
w("")
b2its = base2["inter_text_stats"]
b3its = base3["inter_noref_stats"]
its = res["inter_nv_stats"]
rs = res["ref_vs_nv_stats"]
w("| 群 | 条件 | n | mean | std | min | max |")
w("|----|------|---|------|-----|-----|-----|")
w(
    f'| 第 2 弾 text 間 | あり × 異文同士 | 10 | {b2its["mean"]} | {b2its["std"]} '
    f'| {b2its["min"]} | {b2its["max"]} |'
)
w(
    f'| 第 2 弾 ref–text | あり × 異文 | 5 | {b2s["mean"]} | {b2s["std"]} '
    f'| {b2s["min"]} | {b2s["max"]} |'
)
w(
    f'| 第 3 弾 noref 間 | なし × 同一文同士 | 10 | {b3its["mean"]} | {b3its["std"]} '
    f'| {b3its["min"]} | {b3its["max"]} |'
)
w(
    f'| 第 3 弾 ref–noref | なし × 同一文 | 5 | {b3s["mean"]} | {b3s["std"]} '
    f'| {b3s["min"]} | {b3s["max"]} |'
)
w(f'| ref–nv | なし × 異文 | 5 | {rs["mean"]} | {rs["std"]} | {rs["min"]} | {rs["max"]} |')
w(f'| nv 間 | なし × 異文同士 | 10 | {its["mean"]} | {its["std"]} | {its["min"]} | {its["max"]} |')
w(
    f'| クロス A nv×text | なし × あり（異文） | 25 | {ca["mean"]} | {ca["std"]} '
    f'| {ca["min"]} | {ca["max"]} |'
)
w(
    f'| クロス B nv×noref | なし同士（文章またぎ） | 25 | {cb["mean"]} | {cb["std"]} '
    f'| {cb["min"]} | {cb["max"]} |'
)
w("")
w("## 2×2 実験マトリクス（ref_text 有無 × 同一文/異文）")
w("")
b1its = base1["inter_trial_stats"]
b1rs = base1["ref_vs_trial_stats"]
w("生成物間類似度（mean ± std）と ref–生成物類似度（mean ± std）の俯瞰:")
w("")
w("| 実験 | ref_text | テキスト | 生成物間 | ref–生成物 |")
w("|------|----------|----------|----------|------------|")
w(
    f'| 第 1 弾 | あり | 同一文 ×5 | {b1its["mean"]} ± {b1its["std"]} '
    f'| {b1rs["mean"]} ± {b1rs["std"]} |'
)
w(
    f'| 第 2 弾 | あり | 異文 ×5 | {b2its["mean"]} ± {b2its["std"]} '
    f'| {b2s["mean"]} ± {b2s["std"]} |'
)
w(
    f'| 第 3 弾 | なし | 同一文 ×5 | {b3its["mean"]} ± {b3its["std"]} '
    f'| {b3s["mean"]} ± {b3s["std"]} |'
)
w(
    f'| 第 4 弾 | なし | 異文 ×5 | {its["mean"]} ± {its["std"]} '
    f'| {rs["mean"]} ± {rs["std"]} |'
)
w("")
w("## F0（librosa.pyin、有声フレームのみ）")
w("")
w("| text | F0 mean (Hz) | F0 median (Hz) | voiced frames |")
w("|------|--------------|----------------|---------------|")
for i in range(1, 6):
    t = res["per_nv"][f"nv{i}"]
    w(f'| {i} | {t["f0_mean_hz"]:.2f} | {t["f0_median_hz"]:.2f} | {t["voiced_frames"]} |')
f0s = [res["per_nv"][f"nv{i}"]["f0_mean_hz"] for i in range(1, 6)]
b2f0s = [base2["per_text"][f"text{i}"]["f0_mean_hz"] for i in range(1, 6)]
w("")
w(
    f"F0 mean の範囲は {min(f0s):.2f}〜{max(f0s):.2f} Hz（幅 {max(f0s) - min(f0s):.2f} Hz）。"
    f"第 2 弾 text は {min(b2f0s):.2f}〜{max(b2f0s):.2f} Hz"
    f"（幅 {max(b2f0s) - min(b2f0s):.2f} Hz）。"
)
w("")
w("## 類似度行列（11×11: ref + 第 2 弾 text1..5 + 第 4 弾 nv1..5）")
w("")
labels = res["similarity_matrix"]["labels"]
w("| | " + " | ".join(labels) + " |")
w("|---" * (len(labels) + 1) + "|")
for label, row in zip(labels, res["similarity_matrix"]["values"]):
    w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
w("")
w("ヒートマップ画像: `noreftext_varied/similarity_heatmap_noreftext_varied.webp`")
w("")
w("## 所感（数値から言える範囲）")
w("")
w(
    f'- nv 間類似度（mean {its["mean"]} ± {its["std"]}）は第 2 弾の text 間'
    f'（mean {b2its["mean"]} ± {b2its["std"]}）・第 3 弾の noref 間'
    f'（mean {b3its["mean"]} ± {b3its["std"]}）と同水準。書き起こしなし × 異文でも'
    "生成物間の声の一貫性は保たれている"
)
w(
    f'- ref–nv 類似度（mean {rs["mean"]} ± {rs["std"]}）は第 3 弾の ref–noref'
    f'（mean {b3s["mean"]} ± {b3s["std"]}）と同水準で、第 2 弾の ref–text'
    f'（mean {b2s["mean"]} ± {b2s["std"]}）よりは低い。書き起こしなし条件の 2 実験'
    "（第 3・4 弾）がともに書き起こしあり条件（第 1・2 弾）を下回る並びで、"
    "reference への忠実度は書き起こし有無の側に紐づいて見える"
)
w(
    f'- クロス A（mean {ca["mean"]}）・クロス B（mean {cb["mean"]}）とも各群内の類似度と'
    "同水準で、書き起こし有無・文章の違いをまたいでも別の声にはなっていない。"
    "同一文章同士のペア（nv_i–text_i、書き起こし有無だけが違う 5 ペア）も "
    f'mean {cas["mean"]}（min {cas["min"]} / max {cas["max"]}）で同水準'
)
w(
    f'- 音声尺は mean {ds["mean"]}s / std {ds["std"]}s。同一テキストを使った第 2 弾'
    f'（mean {b2ds["mean"]}s / std {b2ds["std"]}s、レンジ {b2ds["min"]}〜{b2ds["max"]}s）より'
    f'ばらつきが大きく、text4 は {ds["min"]}s で第 2 弾の同テキスト'
    f'（{base2["per_text"]["text4"]["duration_sec"]}s）より約 2.6 秒短い。'
    "第 3 弾でも見られた「書き起こしなしで尺が振れやすい」傾向と整合する"
)
w(
    f"- F0 mean の幅は {max(f0s) - min(f0s):.2f} Hz で、第 2 弾の "
    f"{max(b2f0s) - min(b2f0s):.2f} Hz より大きい。ピッチのぶれも書き起こしなしの方が"
    "大きい傾向（第 3 弾と同様）"
)
if low_rms:
    w(
        "- RMS は "
        + "、".join(f"{k}={v:.5f}" for k, v in low_rms)
        + " の 2 本が過去 3 実験のレンジ下限 0.09 をわずかに下回った。無音ではないが、"
        "音量の振れも書き起こしなし条件でやや大きい可能性がある"
    )
w(
    "- 本テストは resemblyzer embedding という単一の客観指標に基づく。異文ペアには"
    "音素内容差が混入する（`report-varied.md` の「指標の限界」参照）。聴感上の同一性・"
    "発音の正確さは別途評価が必要"
)
w("")

print("\n".join(lines))
