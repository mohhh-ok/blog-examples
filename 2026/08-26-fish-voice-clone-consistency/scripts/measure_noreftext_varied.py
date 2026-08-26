"""Fish Audio voice clone no-ref-text x text-variation test — measurement step (第 4 弾).

- resemblyzer VoiceEncoder で ref + text1..5 (第 2 弾) + noref1..5 (第 3 弾) +
  nv1..5 (第 4 弾 = 書き起こしなし異テキスト) の話者 embedding を取り、
  以下のコサイン類似度群を算出:
  1. ref vs 各 nv (5 個) — 忠実度
  2. nv 間全 10 ペア — 異文同士・ref_text なしの一貫性
  3. クロス A: nv 各 5 本 x 第 2 弾 text 各 5 本の 25 ペア
     (ref_text 有無で同じ声か。同一文章同士のペア nv_i–text_i 5 個も個別記録)
  4. クロス B: nv 各 5 本 x 第 3 弾 noref 各 5 本の 25 ペア
     (ref_text なし同士で文章をまたいでも同じ声か)
- librosa.pyin で nv ごとの F0 mean / median
- 各 wav の RMS (無音・破綻チェック)
- ref + 第 2 弾 text1..5 + 第 4 弾 nv1..5 の 11x11 類似度行列ヒートマップを webp で保存

usage: python scripts/measure_noreftext_varied.py
"""

import itertools
import json
import statistics
from pathlib import Path

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from resemblyzer import VoiceEncoder, preprocess_wav

ROOT = Path(__file__).resolve().parents[1]
REF_WAV = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output"
NV = OUT / "noreftext_varied"
TEXTS = [OUT / "varied" / f"text{i}.wav" for i in range(1, 6)]  # 第 2 弾
NOREFS = [OUT / "noreftext" / f"trial{i}.wav" for i in range(1, 6)]  # 第 3 弾
NVS = [NV / f"text{i}.wav" for i in range(1, 6)]  # 第 4 弾
# embedding index: 0 = ref, 1..5 = text1..5, 6..10 = noref1..5, 11..15 = nv1..5
TEXT_IDX = range(1, 6)
NOREF_IDX = range(6, 11)
NV_IDX = range(11, 16)
# heatmap は ref + text1..5 + nv1..5 の 11x11 (noref は含めない)
HEAT_IDX = [0, *TEXT_IDX, *NV_IDX]
HEAT_LABELS = ["ref"] + [f"text{i}" for i in range(1, 6)] + [f"nv{i}" for i in range(1, 6)]


def stats(values: list[float]) -> dict:
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main() -> None:
    files = [REF_WAV] + TEXTS + NOREFS + NVS
    for f in files:
        if not f.exists():
            raise FileNotFoundError(f)

    # --- speaker embeddings ---
    encoder = VoiceEncoder()
    embeds = []
    for f in files:
        wav = preprocess_wav(f)
        embeds.append(encoder.embed_utterance(wav))
    embeds = np.stack(embeds)  # (16, 256), already L2-normalized
    sim = embeds @ embeds.T  # cosine similarity matrix

    ref_vs_nv = {f"nv{i - 10}": round(float(sim[0, i]), 4) for i in NV_IDX}
    nv_pair_sims = {}
    for a, b in itertools.combinations(NV_IDX, 2):
        nv_pair_sims[f"nv{a - 10}-nv{b - 10}"] = round(float(sim[a, b]), 4)
    cross_a_sims = {}
    for n in NV_IDX:
        for t in TEXT_IDX:
            cross_a_sims[f"nv{n - 10}-text{t}"] = round(float(sim[n, t]), 4)
    same_text_pairs = {f"nv{i}-text{i}": cross_a_sims[f"nv{i}-text{i}"] for i in range(1, 6)}
    cross_b_sims = {}
    for n in NV_IDX:
        for r in NOREF_IDX:
            cross_b_sims[f"nv{n - 10}-noref{r - 5}"] = round(float(sim[n, r]), 4)

    # --- duration + F0 + RMS (nv1..5) ---
    per_nv = {}
    for i, f in enumerate(NVS, start=1):
        y, sr = librosa.load(f, sr=None, mono=True)
        duration = len(y) / sr
        f0, _, _ = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C6")),
        )
        voiced = f0[~np.isnan(f0)]
        per_nv[f"nv{i}"] = {
            "duration_sec": round(duration, 3),
            "samplerate": int(sr),
            "rms": round(float(np.sqrt(np.mean(y**2))), 5),
            "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
            "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
            "voiced_frames": int(voiced.size),
        }

    durations = [per_nv[f"nv{i}"]["duration_sec"] for i in range(1, 6)]

    heat = sim[np.ix_(HEAT_IDX, HEAT_IDX)]
    results = {
        "ref_vs_nv_similarity": ref_vs_nv,
        "ref_vs_nv_stats": stats(list(ref_vs_nv.values())),
        "inter_nv_similarity": nv_pair_sims,
        "inter_nv_stats": stats(list(nv_pair_sims.values())),
        "cross_a_nv_vs_text_similarity": cross_a_sims,
        "cross_a_stats": stats(list(cross_a_sims.values())),
        "cross_a_same_text_pairs": same_text_pairs,
        "cross_a_same_text_stats": stats(list(same_text_pairs.values())),
        "cross_b_nv_vs_noref_similarity": cross_b_sims,
        "cross_b_stats": stats(list(cross_b_sims.values())),
        "durations_sec": durations,
        "duration_stats": stats(durations),
        "per_nv": per_nv,
        "similarity_matrix": {
            "labels": HEAT_LABELS,
            "values": [[round(float(v), 4) for v in row] for row in heat],
        },
    }
    (NV / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # --- heatmap (png -> webp) ---
    n = len(HEAT_LABELS)
    fig, ax = plt.subplots(figsize=(9.6, 8.4), dpi=150)
    im = ax.imshow(heat, vmin=0.7, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(n), HEAT_LABELS, rotation=45, ha="right")
    ax.set_yticks(range(n), HEAT_LABELS)
    for r in range(n):
        for c in range(n):
            ax.text(
                c,
                r,
                f"{heat[r, c]:.3f}",
                ha="center",
                va="center",
                color="white" if heat[r, c] < 0.9 else "black",
                fontsize=7,
            )
    ax.set_title(
        "Speaker embedding cosine similarity (resemblyzer) — varied text, with vs without ref text"
    )
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png_path = NV / "similarity_heatmap_noreftext_varied.png"
    fig.savefig(png_path)
    plt.close(fig)

    webp_path = NV / "similarity_heatmap_noreftext_varied.webp"
    Image.open(png_path).save(webp_path, "webp", quality=90)
    png_path.unlink()
    print(f"[done] heatmap -> {webp_path}")


if __name__ == "__main__":
    main()
