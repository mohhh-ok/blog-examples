"""声ごとに 3 方式の ref 比の平均 (clean、2.5 秒窓) を横に並べた図を作る。ローカルで実行する。

使い方:
  uv run --with matplotlib --with pillow python -I make_figure.py <out.webp>
読むもの: results/windows.json (measure_windows.py の出力)、results/refs.json (性別)
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in font_manager.findSystemFonts():
    if "ヒラギノ角ゴシック W3" in f or "Hiragino Sans W3" in f or "HiraginoSans-W3" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]

HERE = Path(__file__).parent
BG = "#f2f0ee"
INK = "#19120f"
MUTED = "#6b5a52"
GRID = "#d9d3ce"
QUALITY = "clean"
# (方式, 凡例, 色, マーカー)。色は dataviz の validate_palette.js で #f2f0ee 上の全チェックを通した組
MODES = [
    ("per-line-random", "1 行ずつ・seed ランダム", "#bb5537", "o"),
    ("per-line-fixed", "1 行ずつ・seed 固定", "#2f7bb0", "s"),
    ("run", "5 行ずつ 1 回で合成", "#a8860a", "^"),
]


def main() -> None:
    out = Path(sys.argv[1])
    win = json.loads((HERE / "results/windows.json").read_text())
    gender = {r["id"]: r.get("gender") for r in json.loads((HERE / "results/refs.json").read_text())}
    voices = sorted({v["voice"] for v in win.values()}, key=lambda v: win[f"{v}|{QUALITY}|per-line-random"]["ref_mean"])

    fig, ax = plt.subplots(figsize=(8, 6.2), facecolor=BG)
    ax.set_facecolor(BG)
    for y, v in enumerate(voices):
        vals = [win[f"{v}|{QUALITY}|{m}"]["ref_mean"] for m, *_ in MODES]
        ax.plot([min(vals), max(vals)], [y, y], color=GRID, lw=6, solid_capstyle="round", zorder=1)
        for (m, _, color, marker), x in zip(MODES, vals):
            ax.scatter(x, y, s=64, color=color, marker=marker, edgecolors=BG, linewidths=1.5, zorder=3)

    labels = []
    for v in voices:
        g = gender.get(v)
        labels.append(f"{v} ({'女性' if g == 'F' else '男性'})" if g else f"{v} (男性・筆者)")
    ax.set_yticks(range(len(voices)), labels, color=INK, fontsize=10)
    ax.set_xlim(0.74, 0.88)
    ax.set_xlabel("参照音声との似方 (2.5 秒ごとの話者類似度の平均。1 に近いほど似ている)", color=INK, fontsize=10)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)

    handles = [
        plt.Line2D([], [], ls="", marker=marker, color=color, markersize=8, label=label) for _, label, color, marker in MODES
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5, labelcolor=INK)
    fig.suptitle("声ごとの 3 方式の似方 (参照 clean、台本 10 行)", color=INK, fontsize=13, x=0.02, y=0.985, ha="left")
    fig.text(0.02, 0.92, "灰色の帯は同じ声の 3 方式の幅。印が重なっている声は 2 方式がほぼ同じ値", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    png = out.with_suffix(".png")
    fig.savefig(png, dpi=130, facecolor=BG)
    from PIL import Image

    Image.open(png).save(out, "WEBP", quality=88)
    png.unlink()


if __name__ == "__main__":
    main()
