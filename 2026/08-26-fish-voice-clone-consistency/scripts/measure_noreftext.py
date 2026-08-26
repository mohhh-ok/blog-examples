"""Fish Audio voice clone no-ref-text test — measurement step (第 3 弾).

- resemblyzer VoiceEncoder で ref + trial1..5 (第 1 弾) + noref1..5 (第 3 弾) の
  話者 embedding を取り、以下のコサイン類似度群を算出:
  1. ref vs 各 noref (5 個) — 忠実度
  2. noref 間全 10 ペア — 再現性
  3. クロスセット: noref 各 5 本 x 第 1 弾 trial 各 5 本の 25 ペア
     (ref_text ありの声と同じ声になっているか)
- librosa.pyin で noref ごとの F0 mean / median
- 各 wav の RMS (無音・破綻チェック)
- 11x11 類似度行列のヒートマップを webp で保存

usage: python scripts/measure_noreftext.py
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
NOREF = OUT / "noreftext"
TRIALS = [OUT / f"trial{i}.wav" for i in range(1, 6)]
NOREFS = [NOREF / f"trial{i}.wav" for i in range(1, 6)]
LABELS = ["ref"] + [f"trial{i}" for i in range(1, 6)] + [f"noref{i}" for i in range(1, 6)]
N = len(LABELS)  # 11
# matrix index: 0 = ref, 1..5 = trial1..5 (第 1 弾), 6..10 = noref1..5 (第 3 弾)
TRIAL_IDX = range(1, 6)
NOREF_IDX = range(6, 11)


def stats(values: list[float]) -> dict:
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main() -> None:
    files = [REF_WAV] + TRIALS + NOREFS
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

    ref_vs_noref = {f"noref{i - 5}": round(float(sim[0, i]), 4) for i in NOREF_IDX}
    noref_pair_sims = {}
    for a, b in itertools.combinations(NOREF_IDX, 2):
        noref_pair_sims[f"noref{a - 5}-noref{b - 5}"] = round(float(sim[a, b]), 4)
    cross_sims = {}
    for n in NOREF_IDX:
        for r in TRIAL_IDX:
            cross_sims[f"noref{n - 5}-trial{r}"] = round(float(sim[n, r]), 4)

    # --- duration + F0 + RMS (noref1..5) ---
    per_noref = {}
    for i, f in enumerate(NOREFS, start=1):
        y, sr = librosa.load(f, sr=None, mono=True)
        duration = len(y) / sr
        f0, _, _ = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C6")),
        )
        voiced = f0[~np.isnan(f0)]
        per_noref[f"noref{i}"] = {
            "duration_sec": round(duration, 3),
            "samplerate": int(sr),
            "rms": round(float(np.sqrt(np.mean(y**2))), 5),
            "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
            "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
            "voiced_frames": int(voiced.size),
        }

    durations = [per_noref[f"noref{i}"]["duration_sec"] for i in range(1, 6)]

    results = {
        "ref_vs_noref_similarity": ref_vs_noref,
        "ref_vs_noref_stats": stats(list(ref_vs_noref.values())),
        "inter_noref_similarity": noref_pair_sims,
        "inter_noref_stats": stats(list(noref_pair_sims.values())),
        "cross_set_similarity": cross_sims,
        "cross_set_stats": stats(list(cross_sims.values())),
        "durations_sec": durations,
        "duration_stats": stats(durations),
        "per_noref": per_noref,
        "similarity_matrix": {
            "labels": LABELS,
            "values": [[round(float(v), 4) for v in row] for row in sim],
        },
    }
    (NOREF / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
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
    ax.set_title("Speaker embedding cosine similarity (resemblyzer) — with vs without ref text")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png_path = NOREF / "similarity_heatmap_noreftext.png"
    fig.savefig(png_path)
    plt.close(fig)

    webp_path = NOREF / "similarity_heatmap_noreftext.webp"
    Image.open(png_path).save(webp_path, "webp", quality=90)
    png_path.unlink()
    print(f"[done] heatmap -> {webp_path}")


if __name__ == "__main__":
    main()
