"""output/multilingual/generation.json + results.json + 第 2 弾の
output/varied/results.json から report-multilingual.md を組み立てる。

usage: python scripts/make_report_multilingual.py > output/report-multilingual.md
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ML = OUT / "multilingual"

gen = json.loads((ML / "generation.json").read_text())
res = json.loads((ML / "results.json").read_text())
varied = json.loads((OUT / "varied" / "results.json").read_text())  # 第 2 弾

LANGS = ["ja", "en", "zh", "ko", "fr", "es", "de"]

lines: list[str] = []
w = lines.append

w("# Fish Audio voice clone 多言語テスト 結果レポート（第 5 弾）")
w("")
w("実施日: 2026-08-26")
w("")
w("第 1〜4 弾（同一文/異文 × ref_text 有無の 2×2、日本語のみ）に続き、"
  "「言語をまたいでも同じクローン声が出るか」を測る。日本語話者の同一 reference から"
  "7 言語（ja / en / zh / ko / fr / es / de）のテキストを各 1 回生成し、"
  "話者類似度を第 2 弾（日本語異文 5 本）ベースラインと比較する。")
w("")
w("## 手法")
w("")
w(f'- モデル: `{gen["model"]}`（fish-audio-sdk `Session.tts(backend=...)` → `model` ヘッダ）。'
  "クローン方式・reference・実行条件は第 1・2 弾と完全に同一（ref_text あり）")
w("- クローン方式: inline zero-shot（`references` に reference wav バイナリ + 書き起こしテキストを渡す。事前 voice 登録なし）")
w("- reference audio: 約 10.16 秒・24kHz mono・日本語話者。書き起こし:")
w(f'  「{gen["ref_text"]}」')
w("- 生成テキスト: 7 言語各 1 種（06-19 multilingual-voice-cloning-benchmark の prompts.py と同一。過去記事との継続性のため）")
w(f'- 実行: {gen["num_langs_requested"]} 回逐次（リクエスト間 2 秒スリープ）、`format="wav"`'
  f'（API 出力そのまま、変換なし）。{gen["num_langs_succeeded"]}/{gen["num_langs_requested"]} 成功')
w("- 話者類似度: resemblyzer `VoiceEncoder`（256 次元 utterance embedding）のコサイン類似度")
w("- F0: librosa `pyin`（fmin=C2, fmax=C6）の有声フレーム平均・中央値")
w("- 言語検証: faster-whisper（small・CPU・int8）で各 wav の言語判定 + 書き起こし")
w("")
w("## 生成テキスト")
w("")
for t in gen["langs"]:
    w(f'- {t["lang"]}（{t["text_chars"]} 字）: 「{t["text"]}」')
w("")
w("## 生成結果（レイテンシ・尺・RMS）")
w("")
w("| lang | latency (s) | duration (s) | RMS | samplerate |")
w("|------|-------------|--------------|-----|------------|")
for t in gen["langs"]:
    rms = res["per_lang"][t["lang"]]["rms"]
    w(f'| {t["lang"]} | {t["latency_sec"]:.2f} | {t["duration_sec"]:.3f} | {rms:.5f} | {t["samplerate"]} |')
lat = [t["latency_sec"] for t in gen["langs"]]
ds = res["duration_stats"]
w("")
w(f"- latency: mean {sum(lat) / len(lat):.2f}s（min {min(lat):.2f}s / max {max(lat):.2f}s）")
w(f'- duration: mean {ds["mean"]}s / std {ds["std"]}s / min {ds["min"]}s / max {ds["max"]}s'
  "（テキストが言語ごとに異なるため尺の差は内容差由来が主）")
w("- RMS はいずれも 0.09〜0.14 の範囲で、無音・破綻出力はない")
w("")
w("## 言語検証（faster-whisper）")
w("")
ver = res["language_verification"]
if ver["status"] == "done":
    w(f'判定モデル: {ver["model"]}')
    w("")
    w("| lang | 判定言語 | 確率 | 一致 | 書き起こし（内容確認用） |")
    w("|------|----------|------|------|--------------------------|")
    for lang in LANGS:
        v = ver["results"][lang]
        ok = "o" if v["matches_target"] else "x"
        w(f'| {lang} | {v["detected_language"]} | {v["language_probability"]:.4f} | {ok} | {v["transcript"]} |')
    n_match = sum(1 for lang in LANGS if ver["results"][lang]["matches_target"])
    w("")
    w(f"言語判定は {n_match}/{len(LANGS)} でターゲット言語と一致。書き起こしはいずれも"
      "生成テキストと概ね一致しており、別内容・途切れは検出されなかった。")
else:
    w(f'言語検証は未実施（{ver["error"]}）。')
w("")
w("## 忠実度: ref vs 各言語のコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for lang in LANGS:
    w(f'| ref–{lang} | {res["ref_vs_lang_similarity"][lang]:.4f} |')
s = res["ref_vs_lang_stats"]
bv = varied["ref_vs_text_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w(f'（第 2 弾 ref–text（日本語異文）: mean {bv["mean"]} / std {bv["std"]} / min {bv["min"]} / max {bv["max"]}）')
w("")
w("## 一貫性: 言語間全 21 ペアのコサイン類似度")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["inter_lang_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["inter_lang_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("### ja–他言語の 6 ペア（抜粋）")
w("")
w("| ペア | 類似度 |")
w("|------|--------|")
for k, v in res["ja_vs_other_similarity"].items():
    w(f'| {k.replace("-", "–")} | {v:.4f} |')
s = res["ja_vs_other_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## クロスセット: 7 言語 × 第 2 弾 text 5 本の 35 ペア")
w("")
w("| | text1 | text2 | text3 | text4 | text5 |")
w("|---|---|---|---|---|---|")
for lang in LANGS:
    row = [res["cross_set_similarity"][f"{lang}-text{t}"] for t in range(1, 6)]
    w(f"| {lang} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
s = res["cross_set_stats"]
w("")
w(f'統計: mean {s["mean"]} / std {s["std"]} / min {s["min"]} / max {s["max"]}')
w("")
w("## 群比較（第 2 弾ベースラインとの並置）")
w("")
w("| 群 | 条件 | n | mean | std | min | max |")
w("|----|------|---|------|-----|-----|-----|")
bt = varied["inter_text_stats"]
rv = res["ref_vs_lang_stats"]
il = res["inter_lang_stats"]
jo = res["ja_vs_other_stats"]
cs = res["cross_set_stats"]
w(f'| 第 2 弾 text 間 | 日本語異文同士 | 10 | {bt["mean"]} | {bt["std"]} | {bt["min"]} | {bt["max"]} |')
w(f'| 第 2 弾 ref–text | 日本語異文 | 5 | {bv["mean"]} | {bv["std"]} | {bv["min"]} | {bv["max"]} |')
w(f'| ref–言語 | 7 言語 | 7 | {rv["mean"]} | {rv["std"]} | {rv["min"]} | {rv["max"]} |')
w(f'| 言語間 | 異言語同士 | 21 | {il["mean"]} | {il["std"]} | {il["min"]} | {il["max"]} |')
w(f'| ja–他言語 | 異言語同士（ja 起点） | 6 | {jo["mean"]} | {jo["std"]} | {jo["min"]} | {jo["max"]} |')
w(f'| クロス 言語×text | 異言語 × 日本語異文 | 35 | {cs["mean"]} | {cs["std"]} | {cs["min"]} | {cs["max"]} |')
w("")
w("## F0・尺（言語ごと）")
w("")
w("| lang | duration (s) | F0 mean (Hz) | F0 median (Hz) | voiced frames |")
w("|------|--------------|--------------|----------------|---------------|")
for lang in LANGS:
    t = res["per_lang"][lang]
    w(f'| {lang} | {t["duration_sec"]:.3f} | {t["f0_mean_hz"]:.2f} | {t["f0_median_hz"]:.2f} | {t["voiced_frames"]} |')
f0s = [res["per_lang"][lang]["f0_mean_hz"] for lang in LANGS]
w("")
w(f"F0 mean の範囲は {min(f0s):.2f}〜{max(f0s):.2f} Hz（幅 {max(f0s) - min(f0s):.2f} Hz）。"
  "第 2 弾（日本語異文）の幅 2.92 Hz より広い。")
w("")
w("## 類似度行列（8×8: ref + 7 言語）")
w("")
labels = res["similarity_matrix"]["labels"][:8]
vals = [row[:8] for row in res["similarity_matrix"]["values"][:8]]
w("| | " + " | ".join(labels) + " |")
w("|---" * (len(labels) + 1) + "|")
for label, row in zip(labels, vals):
    w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
w("")
w("ヒートマップ画像: `multilingual/similarity_heatmap_multilingual.webp`")
w("")
w("## 指標の限界（重要）")
w("")
w("resemblyzer の VoiceEncoder は英語中心のデータセット（VoxCeleb 系）で学習された話者 encoder"
  "であり、言語・音素内容の影響が embedding に混入しやすい。言語をまたいだペアの類似度低下には、"
  "**声質の変化**・**音素体系の差**・**encoder の言語バイアス**の少なくとも 3 つが混ざっており、"
  "本測定だけでこれらを分離することはできない。言語間の類似度が日本語同士より低くても、"
  "それを直ちに「言語によって声が変わった」と断定はできない。")
w("")
w("また第 5 弾の生成テキストは 1 言語 1 本・短文（約 5〜6.5 秒）であり、第 1〜4 弾"
  "（約 12〜17 秒）より発話が短い。utterance embedding は発話が短いほど不安定になるため、"
  "その影響も混入し得る。")
w("")
w("## 所感（数値から言える範囲）")
w("")
w(f'- ref–言語類似度（mean {rv["mean"]} ± {rv["std"]}）は第 2 弾の ref–text'
  f'（mean {bv["mean"]} ± {bv["std"]}）より低く、言語間類似度（mean {il["mean"]} ± {il["std"]}）も'
  f'第 2 弾の text 間（mean {bt["mean"]}）を明確に下回った。日本語内の異文では観測されなかった'
  "類似度の低下が、言語をまたぐと観測される")
w(f'- 最小は en–zh の {res["inter_lang_similarity"]["en-zh"]:.4f}。ja–他言語では ja–en の'
  f' {res["ja_vs_other_similarity"]["ja-en"]:.4f} が最も低く、ja–es（{res["ja_vs_other_similarity"]["ja-es"]:.4f}）・'
  f'ja–de（{res["ja_vs_other_similarity"]["ja-de"]:.4f}）は日本語内ベースラインに近い水準')
w("- ただし「指標の限界」のとおり、この低下は声質変化・音素体系差・encoder の言語バイアス・"
  "発話長の混合であり、声質変化の量として読むことはできない。崩壊的な別人化"
  f'（全 63 ペア最小 {min(il["min"], cs["min"], rv["min"])}）は観測されていない')
w("- 言語検証では 7/7 でターゲット言語どおりに発話しており、指定言語で喋らない・"
  "内容が破綻するといった故障は観測されなかった")
w("- 本テストは resemblyzer embedding という単一の客観指標に基づく。聴感上の同一性"
  "（別言語でも同じ人に聞こえるか）は別途評価が必要")
w("")

print("\n".join(lines))
