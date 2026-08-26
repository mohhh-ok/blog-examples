"""Fish Audio voice clone multilingual test — measurement step (第 5 弾).

- resemblyzer VoiceEncoder で ref + 7 言語 (第 5 弾) + text1..5 (第 2 弾) の
  話者 embedding を取り、以下のコサイン類似度群を算出:
  1. ref vs 各言語 (7 個) — 忠実度
  2. 言語間全 21 ペア — 言語をまたいだ声の一貫性 (ja–他言語 6 ペアは個別記録)
  3. クロスセット: 7 言語 x 第 2 弾 text 各 5 本の 35 ペア
     (日本語異文ベースラインと同じ声か)
- librosa.pyin で言語ごとの F0 mean / median、RMS (無音・破綻チェック)
- faster-whisper (small, CPU) で各 wav の言語判定 + 書き起こし (言語検証)
- ref + 7 言語の 8x8 類似度行列ヒートマップを webp で保存

usage: python scripts/measure_multilingual.py
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
ML = OUT / "multilingual"
VARIED = OUT / "varied"
LANGS = ["ja", "en", "zh", "ko", "fr", "es", "de"]
LANG_WAVS = [ML / f"{lang}.wav" for lang in LANGS]
TEXTS = [VARIED / f"text{i}.wav" for i in range(1, 6)]
# matrix index: 0 = ref, 1..7 = ja..de (第 5 弾), 8..12 = text1..5 (第 2 弾)
LABELS = ["ref"] + LANGS + [f"text{i}" for i in range(1, 6)]
LANG_IDX = range(1, 8)
TEXT_IDX = range(8, 13)


def stats(values: list[float]) -> dict:
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def verify_languages() -> dict:
    """faster-whisper で各 wav の言語判定 + 書き起こしを取る。失敗時は skipped."""
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("small", device="cpu", compute_type="int8")
        out = {}
        for lang, wav in zip(LANGS, LANG_WAVS):
            segments, info = model.transcribe(str(wav), beam_size=5)
            transcript = "".join(s.text for s in segments).strip()
            out[lang] = {
                "detected_language": info.language,
                "language_probability": round(float(info.language_probability), 4),
                "transcript": transcript,
                "matches_target": info.language == lang,
            }
        return {"status": "done", "model": "faster-whisper small (cpu, int8)", "results": out}
    except Exception as e:  # noqa: BLE001
        return {"status": "skipped", "error": f"{type(e).__name__}: {e}", "results": None}


def main() -> None:
    files = [REF_WAV] + LANG_WAVS + TEXTS
    for f in files:
        if not f.exists():
            raise FileNotFoundError(f)

    # --- speaker embeddings ---
    encoder = VoiceEncoder()
    embeds = []
    for f in files:
        wav = preprocess_wav(f)
        embeds.append(encoder.embed_utterance(wav))
    embeds = np.stack(embeds)  # (13, 256), already L2-normalized
    sim = embeds @ embeds.T  # cosine similarity matrix

    ref_vs_lang = {LANGS[i - 1]: round(float(sim[0, i]), 4) for i in LANG_IDX}
    inter_lang_sims = {}
    for a, b in itertools.combinations(LANG_IDX, 2):
        inter_lang_sims[f"{LANGS[a - 1]}-{LANGS[b - 1]}"] = round(float(sim[a, b]), 4)
    ja_vs_other = {k: v for k, v in inter_lang_sims.items() if k.startswith("ja-")}
    cross_sims = {}
    for li in LANG_IDX:
        for t in TEXT_IDX:
            cross_sims[f"{LANGS[li - 1]}-text{t - 7}"] = round(float(sim[li, t]), 4)

    # --- duration + F0 + RMS (per language) ---
    per_lang = {}
    for lang, f in zip(LANGS, LANG_WAVS):
        y, sr = librosa.load(f, sr=None, mono=True)
        duration = len(y) / sr
        f0, _, _ = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C6")),
        )
        voiced = f0[~np.isnan(f0)]
        per_lang[lang] = {
            "duration_sec": round(duration, 3),
            "samplerate": int(sr),
            "rms": round(float(np.sqrt(np.mean(y**2))), 5),
            "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
            "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
            "voiced_frames": int(voiced.size),
        }

    durations = [per_lang[lang]["duration_sec"] for lang in LANGS]

    # --- language verification (faster-whisper) ---
    verification = verify_languages()

    results = {
        "ref_vs_lang_similarity": ref_vs_lang,
        "ref_vs_lang_stats": stats(list(ref_vs_lang.values())),
        "inter_lang_similarity": inter_lang_sims,
        "inter_lang_stats": stats(list(inter_lang_sims.values())),
        "ja_vs_other_similarity": ja_vs_other,
        "ja_vs_other_stats": stats(list(ja_vs_other.values())),
        "cross_set_similarity": cross_sims,
        "cross_set_stats": stats(list(cross_sims.values())),
        "durations_sec": durations,
        "duration_stats": stats(durations),
        "per_lang": per_lang,
        "language_verification": verification,
        "similarity_matrix": {
            "labels": LABELS,
            "values": [[round(float(v), 4) for v in row] for row in sim],
        },
    }
    (ML / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # --- heatmap: ref + 7 langs (8x8, png -> webp) ---
    n = 1 + len(LANGS)
    sub = sim[:n, :n]
    sub_labels = LABELS[:n]
    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=150)
    im = ax.imshow(sub, vmin=0.7, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(n), sub_labels, rotation=45, ha="right")
    ax.set_yticks(range(n), sub_labels)
    for r in range(n):
        for c in range(n):
            ax.text(
                c,
                r,
                f"{sub[r, c]:.3f}",
                ha="center",
                va="center",
                color="white" if sub[r, c] < 0.9 else "black",
                fontsize=8,
            )
    ax.set_title("Speaker embedding cosine similarity (resemblyzer) — 7 languages")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png_path = ML / "similarity_heatmap_multilingual.png"
    fig.savefig(png_path)
    plt.close(fig)

    webp_path = ML / "similarity_heatmap_multilingual.webp"
    Image.open(png_path).save(webp_path, "webp", quality=90)
    png_path.unlink()
    print(f"[done] heatmap -> {webp_path}")


if __name__ == "__main__":
    main()
