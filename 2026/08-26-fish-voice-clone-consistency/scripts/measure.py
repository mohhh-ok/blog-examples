"""Fish Audio voice clone consistency test — measurement step.

- resemblyzer VoiceEncoder で ref + trial1..5 の話者 embedding を取り、
  ref vs trial / trial 間全ペアのコサイン類似度を算出
- librosa.pyin で trial ごとの F0 mean / median
- 6x6 類似度行列のヒートマップを webp で保存

usage: python scripts/measure.py
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
TRIALS = [OUT / f"trial{i}.wav" for i in range(1, 6)]
LABELS = ["ref"] + [f"trial{i}" for i in range(1, 6)]


def stats(values: list[float]) -> dict:
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main() -> None:
    files = [REF_WAV] + TRIALS
    for f in files:
        if not f.exists():
            raise FileNotFoundError(f)

    # --- speaker embeddings ---
    encoder = VoiceEncoder()
    embeds = []
    for f in files:
        wav = preprocess_wav(f)
        embeds.append(encoder.embed_utterance(wav))
    embeds = np.stack(embeds)  # (6, 256), already L2-normalized
    sim = embeds @ embeds.T  # cosine similarity matrix

    ref_vs_trial = {f"trial{i}": round(float(sim[0, i]), 4) for i in range(1, 6)}
    pair_sims = {}
    for a, b in itertools.combinations(range(1, 6), 2):
        pair_sims[f"trial{a}-trial{b}"] = round(float(sim[a, b]), 4)

    # --- duration + F0 ---
    per_trial = {}
    for i, f in enumerate(TRIALS, start=1):
        y, sr = librosa.load(f, sr=None, mono=True)
        duration = len(y) / sr
        f0, _, _ = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C6")),
        )
        voiced = f0[~np.isnan(f0)]
        per_trial[f"trial{i}"] = {
            "duration_sec": round(duration, 3),
            "samplerate": int(sr),
            "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
            "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
            "voiced_frames": int(voiced.size),
        }

    durations = [per_trial[f"trial{i}"]["duration_sec"] for i in range(1, 6)]

    results = {
        "ref_vs_trial_similarity": ref_vs_trial,
        "ref_vs_trial_stats": stats(list(ref_vs_trial.values())),
        "inter_trial_similarity": pair_sims,
        "inter_trial_stats": stats(list(pair_sims.values())),
        "durations_sec": durations,
        "duration_stats": stats(durations),
        "per_trial": per_trial,
        "similarity_matrix": {
            "labels": LABELS,
            "values": [[round(float(v), 4) for v in row] for row in sim],
        },
    }
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # --- heatmap (png -> webp) ---
    fig, ax = plt.subplots(figsize=(6.4, 5.6), dpi=150)
    im = ax.imshow(sim, vmin=0.7, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(6), LABELS, rotation=45, ha="right")
    ax.set_yticks(range(6), LABELS)
    for r in range(6):
        for c in range(6):
            ax.text(
                c,
                r,
                f"{sim[r, c]:.3f}",
                ha="center",
                va="center",
                color="white" if sim[r, c] < 0.9 else "black",
                fontsize=8,
            )
    ax.set_title("Speaker embedding cosine similarity (resemblyzer)")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png_path = OUT / "similarity_heatmap.png"
    fig.savefig(png_path)
    plt.close(fig)

    webp_path = OUT / "similarity_heatmap.webp"
    Image.open(png_path).save(webp_path, "webp", quality=90)
    png_path.unlink()
    print(f"[done] heatmap -> {webp_path}")


if __name__ == "__main__":
    main()
