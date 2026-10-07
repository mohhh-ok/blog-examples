"""金閣寺 seed 2 の A/B/C/E/F を 0〜2kHz のスペクトログラムで縦に並べた図を作る。
usage: python make_figure.py <wav_dir> <out.webp>
wav_dir には k3-<参照>-s2.wav が入っている前提。"""
import sys
import wave
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from scipy.signal import spectrogram

for f in font_manager.findSystemFonts():
    if "ヒラギノ角ゴシック W3" in f or "Hiragino Sans W3" in f or "HiraginoSans-W3" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]

ROWS = [
    ("A", "r26", "そのまま 25.69 秒"),
    ("B", "r26t15", "先頭 15 秒で切っただけ"),
    ("E", "r26t1287", "先頭 12.87 秒で切っただけ"),
    ("C", "r26pipe", "先頭 15 秒に下処理 (12.87 秒)"),
    ("F", "r26long-pipe", "先頭 18 秒に下処理 (15.54 秒)"),
]
BG = "#f2f0ee"
INK = "#3b2922"
CMAP = LinearSegmentedColormap.from_list("blog", [BG, "#e7b8a4", "#bb5537", "#8a000d", "#19120f"])


def read(p: Path):
    with wave.open(str(p)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768.0
    return x.reshape(-1, ch).mean(axis=1), sr


def main() -> None:
    wav_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    data = [read(wav_dir / f"k3-{ref}-s2.wav") for _, ref, _ in ROWS]
    tmax = max(len(x) / sr for x, sr in data)
    fig, axes = plt.subplots(len(ROWS), 1, figsize=(9, 9.5), sharex=True, facecolor=BG)
    for ax, (cond, _, label), (x, sr) in zip(axes, ROWS, data):
        f, t, s = spectrogram(x, fs=sr, nperseg=2048, noverlap=1792, window="hann", scaling="spectrum")
        keep = f <= 2000
        sdb = 10 * np.log10(s[keep] + 1e-12)
        sdb -= 10 * np.log10(np.max(s) + 1e-12)
        ax.pcolormesh(t, f[keep], sdb, cmap=CMAP, vmin=-90, vmax=0, shading="auto", rasterized=True)
        ax.set_facecolor(BG)
        ax.set_xlim(0, tmax)
        ax.set_ylim(0, 2000)
        ax.set_yticks([0, 1000, 2000])
        ax.set_ylabel("Hz", color=INK, fontsize=9)
        ax.tick_params(colors=INK, labelsize=9)
        for sp in ax.spines.values():
            sp.set_color("#c9c2bc")
        ax.set_title(f"{cond}: {label}", loc="left", color=INK, fontsize=11)
    axes[-1].set_xlabel("秒", color=INK)
    fig.suptitle("「金閣寺」seed 2 のスペクトログラム (0〜2kHz、濃いほど強い)", color=INK, fontsize=13, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    png = out.with_suffix(".png")
    fig.savefig(png, dpi=130, facecolor=BG)
    from PIL import Image
    Image.open(png).save(out, "WEBP", quality=88)


if __name__ == "__main__":
    main()
