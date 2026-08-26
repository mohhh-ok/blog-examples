"""Fish Audio voice clone text-variation test — measurement step (第 2 弾).

- resemblyzer VoiceEncoder で ref + trial1..5 (第 1 弾) + text1..5 (第 2 弾) の
  話者 embedding を取り、以下のコサイン類似度群を算出:
  1. ref vs 各 text (5 個) — 忠実度
  2. text 間全 10 ペア — 異テキスト間の声の一貫性
  3. クロスセット: text 各 5 本 x trial 各 5 本の 25 ペア
- librosa.pyin で text ごとの F0 mean / median
- 11x11 類似度行列のヒートマップを webp で保存

usage: python scripts/measure_varied.py
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
VARIED = OUT / "varied"
TRIALS = [OUT / f"trial{i}.wav" for i in range(1, 6)]
TEXTS = [VARIED / f"text{i}.wav" for i in range(1, 6)]
LABELS = ["ref"] + [f"trial{i}" for i in range(1, 6)] + [f"text{i}" for i in range(1, 6)]
N = len(LABELS)  # 11
# matrix index: 0 = ref, 1..5 = trial1..5, 6..10 = text1..5
TRIAL_IDX = range(1, 6)
TEXT_IDX = range(6, 11)


def stats(values: list[float]) -> dict:
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main() -> None:
    files = [REF_WAV] + TRIALS + TEXTS
    for f in files:
        if not f.exists():
            raise FileNotFoundError(f)

    # --- speaker embeddings ---
    encoder = VoiceEncoder()
    embeds = []
    for f in files:
        wav = preprocess_wav(f)
        embeds.append(encoder.embed_utterance(wav))
    embeds = np.stack(embeds)  # (11, 256), already L2-normalized
    sim = embeds @ embeds.T  # cosine similarity matrix

    ref_vs_text = {f"text{i - 5}": round(float(sim[0, i]), 4) for i in TEXT_IDX}
    text_pair_sims = {}
    for a, b in itertools.combinations(TEXT_IDX, 2):
        text_pair_sims[f"text{a - 5}-text{b - 5}"] = round(float(sim[a, b]), 4)
    cross_sims = {}
    for t in TEXT_IDX:
        for r in TRIAL_IDX:
            cross_sims[f"text{t - 5}-trial{r}"] = round(float(sim[t, r]), 4)

    # --- duration + F0 (text1..5) ---
    per_text = {}
    for i, f in enumerate(TEXTS, start=1):
        y, sr = librosa.load(f, sr=None, mono=True)
        duration = len(y) / sr
        f0, _, _ = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C6")),
        )
        voiced = f0[~np.isnan(f0)]
        per_text[f"text{i}"] = {
            "duration_sec": round(duration, 3),
            "samplerate": int(sr),
            "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
            "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
            "voiced_frames": int(voiced.size),
        }

    durations = [per_text[f"text{i}"]["duration_sec"] for i in range(1, 6)]

    results = {
        "ref_vs_text_similarity": ref_vs_text,
        "ref_vs_text_stats": stats(list(ref_vs_text.values())),
        "inter_text_similarity": text_pair_sims,
        "inter_text_stats": stats(list(text_pair_sims.values())),
        "cross_set_similarity": cross_sims,
        "cross_set_stats": stats(list(cross_sims.values())),
        "durations_sec": durations,
        "duration_stats": stats(durations),
        "per_text": per_text,
        "similarity_matrix": {
            "labels": LABELS,
            "values": [[round(float(v), 4) for v in row] for row in sim],
        },
    }
    (VARIED / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # --- heatmap (png -> webp) ---
    fig, ax = plt.subplots(figsize=(9.6, 8.4), dpi=150)
    im = ax.imshow(sim, vmin=0.7, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(N), LABELS, rotation=45, ha="right")
    ax.set_yticks(range(N), LABELS)
    for r in range(N):
        for c in range(N):
            ax.text(
                c,
                r,
                f"{sim[r, c]:.3f}",
                ha="center",
                va="center",
                color="white" if sim[r, c] < 0.9 else "black",
                fontsize=7,
            )
    ax.set_title("Speaker embedding cosine similarity (resemblyzer) — same vs varied text")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png_path = VARIED / "similarity_heatmap_11x11.png"
    fig.savefig(png_path)
    plt.close(fig)

    webp_path = VARIED / "similarity_heatmap_11x11.webp"
    Image.open(png_path).save(webp_path, "webp", quality=90)
    png_path.unlink()
    print(f"[done] heatmap -> {webp_path}")


if __name__ == "__main__":
    main()
