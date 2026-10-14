"""ElevenLabs IVC (eleven_v4) の生成物を測る。

- resemblyzer VoiceEncoder の utterance embedding のコサイン類似度 (08-26 measure*.py と同一の計算)
    same   : ref vs trial (5) / trial 間 (10)
    varied : ref vs text (5) / text 間 (10) / trial x text (25)
    ml     : ref vs 言語 (7) / 言語間 (21) / ja vs 他言語 (6)
    baseline_other_speaker : ref vs 別人の声 (ライブラリ音声 Shohei、baseline_other_speaker.py の出力)
- librosa.pyin の F0 mean / median、尺、RMS (08-26 と同一の fmin/fmax)
- F0 の別推定: librosa.yin で、RMS が中央値以上 (音量の大きい半分) のフレームの F0 中央値
- faster-whisper (small, CPU, int8) で多言語ファイルの言語判定 + 書き起こし
- 図: 11x11 (ref + trial + text) と 8x8 (ref + 7 言語) のヒートマップ、要約の棒グラフ (webp)

usage: python scripts/measure.py
"""

import itertools
import json
import statistics
import sys

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
from PIL import Image
from resemblyzer import VoiceEncoder, preprocess_wav

from common import LANGS, MODEL, OUT, REF_WAV

FIG = OUT / "figures"


def condition_files() -> dict:
    d = OUT / MODEL
    return {
        "same": [d / "same" / f"trial{i}.wav" for i in range(1, 6)],
        "varied": [d / "varied" / f"text{i}.wav" for i in range(1, 6)],
        "ml": [d / "multilingual" / f"{lang}.wav" for lang in LANGS],
    }


def stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return round(float(a @ b), 4)  # embeddings are L2-normalized


def prosody(path) -> dict:
    y, sr = librosa.load(path, sr=None, mono=True)
    f0, _, _ = librosa.pyin(
        y, sr=sr, fmin=float(librosa.note_to_hz("C2")), fmax=float(librosa.note_to_hz("C6"))
    )
    voiced = f0[~np.isnan(f0)]
    return {
        "duration_sec": round(len(y) / sr, 3),
        "samplerate": int(sr),
        "rms": round(float(np.sqrt(np.mean(y**2))), 5),
        "f0_mean_hz": round(float(np.mean(voiced)), 2) if voiced.size else None,
        "f0_median_hz": round(float(np.median(voiced)), 2) if voiced.size else None,
    }


def f0_yin_loud_half(path) -> float:
    y, sr = librosa.load(path, sr=None, mono=True)
    fmin, fmax = float(librosa.note_to_hz("C2")), float(librosa.note_to_hz("C6"))
    f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr)
    rms = librosa.feature.rms(y=y)[0][: len(f0)]
    return round(float(np.median(f0[rms >= np.median(rms)])), 2)


def verify_languages(files: list) -> list:
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="cpu", compute_type="int8")
    out = []
    for lang, wav in zip(LANGS, files):
        segments, info = model.transcribe(str(wav), beam_size=5)
        out.append(
            {
                "lang": lang,
                "detected_language": info.language,
                "language_probability": round(float(info.language_probability), 4),
                "matches_target": info.language == lang,
                "transcript": "".join(s.text for s in segments).strip(),
            }
        )
    return out


def heatmap(sim: np.ndarray, labels: list[str], title: str, path) -> None:
    n = len(labels)
    fig, ax = plt.subplots(figsize=(0.75 * n + 2.4, 0.68 * n + 1.6), dpi=150)
    im = ax.imshow(sim, vmin=0.7, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(n), labels, rotation=45, ha="right")
    ax.set_yticks(range(n), labels)
    for r in range(n):
        for c in range(n):
            ax.text(c, r, f"{sim[r, c]:.3f}", ha="center", va="center",
                    color="white" if sim[r, c] < 0.9 else "black", fontsize=7)
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    png = path.with_suffix(".png")
    fig.savefig(png)
    plt.close(fig)
    Image.open(png).save(path, "webp", quality=90)
    png.unlink()


def main() -> None:
    c = condition_files()
    baseline_wav = OUT / "baseline" / f"{MODEL}.wav"
    missing = [str(f) for fs in c.values() for f in fs if not f.exists()]
    missing += [str(f) for f in (REF_WAV, baseline_wav) if not f.exists()]
    if missing:
        print("missing files:", missing, file=sys.stderr)
        sys.exit(1)
    FIG.mkdir(parents=True, exist_ok=True)

    encoder = VoiceEncoder()
    emb = lambda p: encoder.embed_utterance(preprocess_wav(p))  # noqa: E731
    ref = emb(REF_WAV)
    e = {k: [emb(f) for f in fs] for k, fs in c.items()}

    r = {"model": MODEL, "ref": {"file": REF_WAV.name, **prosody(REF_WAV)}}
    r["same_ref"] = [cos(ref, x) for x in e["same"]]
    r["same_inter"] = {f"trial{a+1}-trial{b+1}": cos(e["same"][a], e["same"][b])
                       for a, b in itertools.combinations(range(5), 2)}
    r["varied_ref"] = [cos(ref, x) for x in e["varied"]]
    r["varied_inter"] = {f"text{a+1}-text{b+1}": cos(e["varied"][a], e["varied"][b])
                         for a, b in itertools.combinations(range(5), 2)}
    r["same_x_varied"] = [cos(a, b) for a in e["same"] for b in e["varied"]]
    r["ml_ref"] = {LANGS[i]: cos(ref, x) for i, x in enumerate(e["ml"])}
    r["ml_inter"] = {f"{LANGS[a]}-{LANGS[b]}": cos(e["ml"][a], e["ml"][b])
                     for a, b in itertools.combinations(range(len(LANGS)), 2)}
    r["ml_ja_vs_other"] = {k: v for k, v in r["ml_inter"].items() if k.startswith("ja-")}
    r["baseline_other_speaker"] = {
        "voice": "Shohei (ElevenLabs library, Japanese male)",
        "file": str(baseline_wav.relative_to(OUT)),
        "ref_similarity": cos(ref, emb(baseline_wav)),
    }
    r["stats"] = {
        "same_ref": stats(r["same_ref"]),
        "same_inter": stats(list(r["same_inter"].values())),
        "varied_ref": stats(r["varied_ref"]),
        "varied_inter": stats(list(r["varied_inter"].values())),
        "same_x_varied": stats(r["same_x_varied"]),
        "ml_ref": stats(list(r["ml_ref"].values())),
        "ml_inter": stats(list(r["ml_inter"].values())),
        "ml_ja_vs_other": stats(list(r["ml_ja_vs_other"].values())),
    }
    r["prosody"] = {k: [{"file": f.name, **prosody(f)} for f in fs] for k, fs in c.items()}
    for k in ("same", "varied", "ml"):
        durs = [p["duration_sec"] for p in r["prosody"][k]]
        f0s = [p["f0_mean_hz"] for p in r["prosody"][k] if p["f0_mean_hz"]]
        r["stats"][f"{k}_duration"] = stats(durs)
        r["stats"][f"{k}_f0_mean"] = stats(f0s)
    r["f0_yin_loud_half"] = {"ref": f0_yin_loud_half(REF_WAV), "same/trial1": f0_yin_loud_half(c["same"][0])}
    r["language_verification"] = verify_languages(c["ml"])
    (OUT / "results.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))

    vecs = [ref] + e["same"] + e["varied"]
    labels = ["ref"] + [f"trial{i}" for i in range(1, 6)] + [f"text{i}" for i in range(1, 6)]
    heatmap(np.stack(vecs) @ np.stack(vecs).T, labels,
            f"{MODEL}: ref + same x5 + varied x5", FIG / f"heatmap_{MODEL}_11x11.webp")
    vecs = [ref] + e["ml"]
    heatmap(np.stack(vecs) @ np.stack(vecs).T, ["ref"] + LANGS,
            f"{MODEL}: ref + 7 languages", FIG / f"heatmap_{MODEL}_multilingual.webp")

    # summary bars: 生成物同士 と ref–生成物 の mean ± std、別人の声の ref 類似度を破線で
    groups = [("same_inter", "same text\ntrial–trial"), ("same_ref", "same text\nref–trial"),
              ("varied_inter", "varied text\ntext–text"), ("varied_ref", "varied text\nref–text"),
              ("ml_inter", "7 languages\nlang–lang"), ("ml_ref", "7 languages\nref–lang")]
    s = r["stats"]
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    x = np.arange(len(groups))
    colors = ["#dd8452" if g.endswith("_ref") else "#4c72b0" for g, _ in groups]
    ax.bar(x, [s[g]["mean"] for g, _ in groups], 0.6,
           yerr=[s[g]["std"] for g, _ in groups], capsize=4, color=colors)
    for xi, (g, _) in zip(x, groups):
        ax.text(xi, s[g]["mean"] + s[g]["std"] + 0.01, f"{s[g]['mean']:.3f}", ha="center", fontsize=8)
    base = r["baseline_other_speaker"]["ref_similarity"]
    base_line = ax.axhline(base, color="gray", linestyle="--", linewidth=1)
    ax.legend([Patch(color="#4c72b0"), Patch(color="#dd8452"), base_line],
              ["generated – generated", "ref – generated",
               f"other speaker (Shohei) – ref: {base:.3f}"], fontsize=8, loc="upper right")
    ax.set_xticks(x, [lbl for _, lbl in groups], fontsize=8)
    ax.set_ylim(0.4, 1.05)
    ax.set_ylabel("cosine similarity (resemblyzer)")
    ax.set_title(f"{MODEL}: mean ± std", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    png = FIG / "summary_bars.png"
    fig.savefig(png)
    plt.close(fig)
    Image.open(png).save(FIG / "summary_bars.webp", "webp", quality=90)
    png.unlink()
    print("[done] results.json + figures", flush=True)


if __name__ == "__main__":
    main()
