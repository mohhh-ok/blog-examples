"""輪郭帯のうち「色が生成背景色とほぼ区別できない画素」を透明にする最小実装。

前提: 単色背景で生成した動画を AI マッティングで抜いた RGBA 画像。輪郭の半透明画素や、
被写体の隙間（うちわと頬のあいだのような狭い領域）に、背景色のまま不透明で残る画素が
出ることがあります。これを alpha=0 にします。

安全弁が 2 つ入っています。

  1. 深さ 3px 以上の不透明画素（inner）は絶対に触らない。ここは意匠そのものなので、
     色が背景色に近くても消してはいけない。
  2. 参照色 F_ref による意匠保護。inner の色を外側へ伝播させたものを F_ref とし、
     F_ref 自体が背景色に近い画素は処理対象から外す。被写体が背景と同系色の布を
     着ている場合に、その布ごと消すのを防ぐ。

透明にした画素の RGB は最近傍の前景色で埋めます。4:2:0 のクロマサブサンプリングで
書き出すと、透明画素の RGB が隣の不透明画素へにじむためです。

使い方:

    python bg_alpha_cut.py --in frame.png --out fixed.png --bg 808080 --threshold 90

しきい値は素材ごとに実測して決めます。欠陥画素と意匠色の背景色からの距離を
ヒストグラムで見て、そのあいだに置きます。既定値は仕様ではなく、ある 1 本の現在値です。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def parse_hex(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float64)


def erode_once(mask: np.ndarray) -> np.ndarray:
    img = Image.fromarray((mask * 255).astype(np.uint8))
    return np.array(img.filter(ImageFilter.MinFilter(3))) > 127


def _shift(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """ゼロ埋めシフト。np.roll のラップアラウンドを潰す。"""
    out = np.roll(arr, shift=(dy, dx), axis=(0, 1))
    if dy > 0:
        out[:dy] = 0
    elif dy < 0:
        out[dy:] = 0
    if dx > 0:
        out[:, :dx] = 0
    elif dx < 0:
        out[:, dx:] = 0
    return out


def propagate(values: np.ndarray, known: np.ndarray, iterations: int):
    """既知領域の色を 8 近傍平均で 1px ずつ外側へ広げる（最近傍伝播の近似）。"""
    values = values.astype(np.float64).copy()
    known = known.copy()
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(values)
        cnt = np.zeros(known.shape, dtype=np.float64)
        for dy, dx in NEIGHBORS:
            k = _shift(known.astype(np.uint8), dy, dx).astype(bool)
            v = _shift(values, dy, dx)
            acc += np.where(k[..., None], v, 0.0)
            cnt += k
        newly = (~known) & (cnt > 0)
        if not newly.any():
            break
        avg = acc / np.where(cnt > 0, cnt, 1.0)[..., None]
        values = np.where(newly[..., None], avg, values)
        known |= newly
    return values, known


def bg_alpha_cut(
    rgba: np.ndarray,
    bg: np.ndarray,
    threshold: float,
    protect_threshold: float = 60.0,
    iterations: int = 16,
    include_opaque_ring: bool = True,
) -> tuple[np.ndarray, dict]:
    """背景色とほぼ同色の輪郭帯画素を alpha=0 にする。inner は不変。"""
    rgb = rgba[..., :3].astype(np.float64)
    alpha = rgba[..., 3]

    opaque = alpha == 255
    e1 = erode_once(opaque)
    e2 = erode_once(e1)
    inner = e2  # 深さ 3px 以上。参照色の供給源であり、絶対に触らない
    semi = (alpha > 0) & (alpha < 255)
    candidate = semi | ((opaque & ~e2) if include_opaque_ring else np.zeros_like(semi))

    stats = {"candidate": int(candidate.sum()), "protected": 0, "cut": 0}
    if stats["candidate"] == 0:
        return rgba.copy(), stats

    f_ref, _ = propagate(rgb, inner, iterations)
    protect = candidate & (dist(f_ref, bg) < protect_threshold)
    stats["protected"] = int(protect.sum())

    cut = candidate & ~protect & (dist(rgb, bg) <= threshold)
    stats["cut"] = int(cut.sum())

    out = rgba.copy()
    out[..., 3] = np.where(cut, 0, alpha)

    # 透明にした画素の RGB を最近傍の前景色で埋める（4:2:0 のにじみ対策）
    filled, _ = propagate(rgb, out[..., 3] > 0, iterations)
    out[..., :3] = np.where(cut[..., None], np.clip(filled, 0, 255).astype(np.uint8), out[..., :3])
    return out, stats


def dist(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    d = rgb - bg.reshape((1,) * (rgb.ndim - 1) + (3,))
    return np.sqrt((d * d).sum(axis=-1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True, type=Path)
    ap.add_argument("--out", dest="dst", required=True, type=Path)
    ap.add_argument("--bg", required=True, help="生成時の背景色 hex")
    ap.add_argument("--threshold", type=float, default=90.0, help="この距離以下なら透明にする")
    ap.add_argument("--protect-threshold", type=float, default=60.0)
    ap.add_argument("--iterations", type=int, default=16)
    args = ap.parse_args()

    rgba = np.array(Image.open(args.src).convert("RGBA"))
    out, stats = bg_alpha_cut(
        rgba, parse_hex(args.bg), args.threshold, args.protect_threshold, args.iterations
    )

    # 意匠を触っていないことを毎回確認する
    inner = erode_once(erode_once(rgba[..., 3] == 255))
    assert np.array_equal(rgba[inner], out[inner]), "inner が変化している"

    Image.fromarray(out).save(args.dst)
    print(stats)


if __name__ == "__main__":
    main()
