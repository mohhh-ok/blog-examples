"""全角と半角の F0 を上下に並べた図を作る。

uv run --with praat-parselmouth --with matplotlib python3 -I scripts/plot_f0.py <出力 png>
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from f0_rise import last_rise, voiced_runs  # noqa: E402

matplotlib.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]
OUT = Path(__file__).parent.parent / "output"
ROWS = [
    ("ashita-hima-fullwidth.wav", "「あした ひま？」(全角)", "#3b2922"),
    ("ashita-hima-halfwidth.wav", "「あした ひま?」(半角)", "#bb5537"),
]

fig, axes = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True, sharey=True, facecolor="#f2f0ee")
for ax, (name, title, color) in zip(axes, ROWS):
    wav = OUT / name
    ax.set_facecolor("#ffffff")
    for run in voiced_runs(wav):
        ax.plot([t for t, _ in run], [f for _, f in run], color=color, lw=2.5)
    r = last_rise(wav)
    ax.set_title(f"{title}  文末の上がり {r['rise_st']:+.1f} 半音", loc="left", fontsize=12, color="#19120f")
    ax.set_ylabel("F0 (Hz)")
    ax.grid(alpha=0.3)
axes[-1].set_xlabel("時間 (秒)")
axes[0].set_ylim(100, 500)
fig.tight_layout()
fig.savefig(sys.argv[1], dpi=150, facecolor=fig.get_facecolor())
