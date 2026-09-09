"""単色背景で生成した動画を AI マッティングで抜いたあと、輪郭に背景色が残っているかを測る。

指標は 3 つあります。

  chroma_bias   マゼンタ/緑のような彩度の高い背景向け。半透明画素と不透明の最外周が
                背景色の色相方向へどれだけ寄っているかを 1 つのスカラーで見る。
                マゼンタ背景なら (R+B)/2 - G、緑背景なら G - (R+B)/2。
  near_bg_pct   無彩色グレー背景向け。R=G=B の背景では chroma_bias が常に 0 付近になり
                使えないので、背景色とのユークリッド距離で「背景色とほぼ区別できない
                画素」の割合を数える。
  dropped_pct   取りこぼし。元動画で前景だった画素（背景色から十分離れた色の画素）の
                うち、抜いたあとに透明になってしまった割合。湯気・毛先のような薄い
                半透明が消えていないかを見る。面積の変動係数やループ継ぎ目の差では
                この種の消失は検出できない。

深さ帯の定義: alpha==255 の領域を 3x3 の最小値フィルタで 1 回ずつ収縮し、その差分を
外側から ring1 / ring2 とする。深さ 3px 以上を inner と呼び、キャラ本来の色（意匠）の
参照に使う。後処理で inner が変わっていたら意匠を壊している。

使い方:

    python fringe_metrics.py --cutout cutout.mov --bg FF00FF
    python fringe_metrics.py --cutout cutout.mov --bg 808080 --raw source.mp4

--cutout は alpha を持つ動画（ProRes 4444 / VP9 alpha / HEVC alpha）。--raw を渡すと
取りこぼしも測ります。ffmpeg / ffprobe が PATH に必要です。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


# ---------- 入出力 ----------


def probe(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json", str(path),
        ],
        capture_output=True, check=True,
    ).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def iter_frames(path: Path, width: int, height: int, channels: int):
    """ffmpeg の rawvideo 出力を 1 フレームずつ ndarray で流す。"""
    pix_fmt = "rgba" if channels == 4 else "rgb24"
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-pix_fmt", pix_fmt, "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE,
    )
    size = width * height * channels
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape((height, width, channels))
    finally:
        proc.stdout.close()
        proc.wait()


def parse_hex(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float64)


# ---------- 帯の定義 ----------


def erode_once(mask: np.ndarray) -> np.ndarray:
    img = Image.fromarray((mask * 255).astype(np.uint8))
    return np.array(img.filter(ImageFilter.MinFilter(3))) > 127


def depth_bands(alpha: np.ndarray) -> dict[str, np.ndarray]:
    opaque = alpha == 255
    e1 = erode_once(opaque)
    e2 = erode_once(e1)
    semi = (alpha > 0) & (alpha < 255)
    return {
        "semi": semi,
        "ring1": opaque & ~e1,
        "ring2": e1 & ~e2,
        "inner": e2,
    }


# ---------- 指標 ----------


def chroma_bias(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """背景色の色相方向への寄りを 1 スカラーにする。緑背景なら符号を反転する。"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    magenta_like = (r + b) / 2.0 - g
    greenish_bg = bg[1] >= bg[0] and bg[1] >= bg[2]
    return -magenta_like if greenish_bg else magenta_like


def dist_to_bg(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    d = rgb - bg.reshape((1,) * (rgb.ndim - 1) + (3,))
    return np.sqrt((d * d).sum(axis=-1))


def frame_metrics(rgba: np.ndarray, bg: np.ndarray, near_bg_dist: float = 30.0) -> dict:
    rgb = rgba[..., :3].astype(np.float64)
    alpha = rgba[..., 3]
    band = depth_bands(alpha)
    bias = chroma_bias(rgb, bg)

    row: dict = {}
    for name in ("semi", "ring1", "ring2"):
        m = band[name]
        n = int(m.sum())
        row[name] = {
            "n": n,
            "mean_bias": round(float(bias[m].mean()), 2) if n else None,
            # 「+20 を超える画素の割合」。平均だけだと打ち消し合って見えなくなる
            "over20_pct": round(100.0 * float((bias[m] > 20).sum()) / n, 2) if n else None,
        }

    fringe = band["semi"] | band["ring1"] | band["ring2"]
    fn = int(fringe.sum())
    row["fringe_near_bg_pct"] = (
        round(100.0 * float((dist_to_bg(rgb[fringe], bg) < near_bg_dist).sum()) / fn, 2) if fn else None
    )
    inner = band["inner"]
    row["inner_mean_rgb"] = (
        [round(float(x), 2) for x in rgb[inner].mean(axis=0)] if int(inner.sum()) else None
    )
    return row


def dropped_pct(raw_rgb: np.ndarray, alpha: np.ndarray, bg: np.ndarray,
                dist_threshold: float = 20.0, alpha_threshold: int = 32) -> float:
    """元動画で前景だった画素のうち、抜いたあと透明になった割合。"""
    candidate = dist_to_bg(raw_rgb.astype(np.float64), bg) > dist_threshold
    n = int(candidate.sum())
    if n == 0:
        return 0.0
    return 100.0 * float((candidate & (alpha < alpha_threshold)).sum()) / n


# ---------- CLI ----------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutout", required=True, type=Path, help="alpha 付き動画")
    ap.add_argument("--raw", type=Path, help="切り抜き前の元動画（取りこぼし計測用）")
    ap.add_argument("--bg", required=True, help="生成時の背景色 hex（例 FF00FF / 808080）")
    ap.add_argument("--near-bg-dist", type=float, default=30.0)
    args = ap.parse_args()

    bg = parse_hex(args.bg)
    w, h = probe(args.cutout)
    cut = iter_frames(args.cutout, w, h, 4)
    raw = iter_frames(args.raw, w, h, 3) if args.raw else None

    semi_bias, near_bg, drops = [], [], []
    first = last = None
    for idx, frame in enumerate(cut):
        m = frame_metrics(frame, bg, args.near_bg_dist)
        if m["semi"]["mean_bias"] is not None:
            semi_bias.append(m["semi"]["mean_bias"])
        if m["fringe_near_bg_pct"] is not None:
            near_bg.append(m["fringe_near_bg_pct"])
        if idx == 0:
            first = m
        last = m
        if raw is not None:
            try:
                drops.append(dropped_pct(next(raw), frame[..., 3], bg))
            except StopIteration:
                raw = None

    print(json.dumps({
        "frames": len(near_bg),
        "bg": args.bg,
        "semi_bias_mean": round(float(np.mean(semi_bias)), 2) if semi_bias else None,
        "semi_bias_max": round(float(np.max(semi_bias)), 2) if semi_bias else None,
        "fringe_near_bg_pct_mean": round(float(np.mean(near_bg)), 2) if near_bg else None,
        "fringe_near_bg_pct_max": round(float(np.max(near_bg)), 2) if near_bg else None,
        "dropped_pct_mean": round(float(np.mean(drops)), 2) if drops else None,
        "dropped_pct_max": round(float(np.max(drops)), 2) if drops else None,
        "frame_first": first,
        "frame_last": last,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
