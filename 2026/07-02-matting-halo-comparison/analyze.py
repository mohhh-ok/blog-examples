"""
Quantitative + visual halo analysis of RVM and MatAnyone 2 outputs.
- Reads output/{rvm,matanyone2}_{fgr,alpha}.mp4
- Reports alpha distribution, fgr green burn ratio, halo tint on white composite
- Saves side-by-side webp images used in the blog post
"""
import csv
import subprocess
from pathlib import Path

import cv2
import numpy as np


HERE = Path(__file__).parent
OUT = HERE / "output"
FRAMES = [50, 200, 400, 600, 800]
HERO_FRAME = 480


def read_frame(path: Path, idx: int):
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, f = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"failed to read {path}:{idx}")
    return f  # BGR


def composite(fgr, alpha_1c, bg_bgr):
    a = (alpha_1c.astype(np.float32) / 255.0)[..., None]
    bg = np.full_like(fgr, 0)
    bg[...] = bg_bgr
    return (fgr.astype(np.float32) * a + bg.astype(np.float32) * (1 - a)).astype(np.uint8)


def label(img, txt):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 40), (0, 0, 0), -1)
    cv2.putText(out, txt, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def side_by_side(l, r, ll, rl):
    return np.hstack([label(l, ll), label(r, rl)])


def analyze_frame(fgr, pha_bgr):
    alpha = pha_bgr[..., 0]
    transparent = (alpha < 10).mean() * 100
    opaque = (alpha > 245).mean() * 100
    edge = 100 - transparent - opaque

    r = fgr[..., 2].astype(np.int32)
    g = fgr[..., 1].astype(np.int32)
    b = fgr[..., 0].astype(np.int32)
    green_dominant = (g > r + 20) & (g > b + 20) & (g > 100)
    tp_mask = alpha < 10
    edge_mask = (alpha >= 10) & (alpha <= 245)
    gdom_tp = green_dominant[tp_mask].mean() * 100 if tp_mask.sum() else 0.0
    gdom_edge = green_dominant[edge_mask].mean() * 100 if edge_mask.sum() else 0.0

    comp_white = composite(fgr, alpha, (255, 255, 255))
    op_bin = (alpha > 200).astype(np.uint8) * 255
    dil = cv2.dilate(op_bin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    edge_zone = (dil > 0) & (op_bin == 0)
    rc = comp_white[..., 2].astype(np.int32)
    gc = comp_white[..., 1].astype(np.int32)
    bc = comp_white[..., 0].astype(np.int32)
    tint = ((gc > rc + 10) & (gc > bc + 10))[edge_zone].mean() * 100 if edge_zone.sum() else 0.0
    mR, mG, mB = rc[edge_zone].mean(), gc[edge_zone].mean(), bc[edge_zone].mean()
    delta_g = mG - (mR + mB) / 2

    return {
        "alpha_transparent_pct": round(transparent, 2),
        "alpha_opaque_pct": round(opaque, 2),
        "alpha_edge_pct": round(edge, 2),
        "fgr_green_in_transparent_pct": round(gdom_tp, 2),
        "fgr_green_in_edge_pct": round(gdom_edge, 2),
        "halo_tint_pct": round(tint, 2),
        "halo_mean_R": round(mR, 1),
        "halo_mean_G": round(mG, 1),
        "halo_mean_B": round(mB, 1),
        "halo_delta_G": round(delta_g, 2),
    }


def crop_person(img):
    return img[100:700, 380:900]


def png_to_webp(png_path: Path, webp_path: Path, quality: int = 82):
    subprocess.run(["cwebp", "-q", str(quality), "-quiet", str(png_path), "-o", str(webp_path)], check=True)


def main():
    OUT.mkdir(exist_ok=True)
    input_video = HERE / "input.mp4"
    src_hero = read_frame(input_video, HERO_FRAME)
    src_png = OUT / "_source.png"
    cv2.imwrite(str(src_png), src_hero)
    png_to_webp(src_png, OUT / "source.webp")

    ma_fgr_v = OUT / "matanyone2_fgr.mp4"
    ma_pha_v = OUT / "matanyone2_alpha.mp4"
    rv_fgr_v = OUT / "rvm_fgr.mp4"
    rv_pha_v = OUT / "rvm_alpha.mp4"

    rows = []
    for name, fgr_v, pha_v in [
        ("MatAnyone 2", ma_fgr_v, ma_pha_v),
        ("RVM mobilenetv3", rv_fgr_v, rv_pha_v),
    ]:
        for idx in FRAMES:
            fgr = read_frame(fgr_v, idx)
            pha = read_frame(pha_v, idx)
            m = analyze_frame(fgr, pha)
            m.update({"model": name, "frame": idx})
            rows.append(m)
            print(name, idx, m)

    with open(OUT / "metrics.csv", "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ma_f = read_frame(ma_fgr_v, HERO_FRAME)
    ma_p = read_frame(ma_pha_v, HERO_FRAME)
    rv_f = read_frame(rv_fgr_v, HERO_FRAME)
    rv_p = read_frame(rv_pha_v, HERO_FRAME)

    ma_w = composite(ma_f, ma_p[..., 0], (255, 255, 255))
    rv_w = composite(rv_f, rv_p[..., 0], (255, 255, 255))
    ma_r = composite(ma_f, ma_p[..., 0], (0, 0, 200))
    rv_r = composite(rv_f, rv_p[..., 0], (0, 0, 200))

    images = {
        "side_white": side_by_side(ma_w, rv_w, "MatAnyone 2 (white bg)", "RVM (white bg)"),
        "side_white_crop": side_by_side(crop_person(ma_w), crop_person(rv_w), "MatAnyone 2", "RVM"),
        "side_red": side_by_side(ma_r, rv_r, "MatAnyone 2 (red bg)", "RVM (red bg)"),
        "side_fgr": side_by_side(ma_f, rv_f, "MatAnyone 2 fgr (raw RGB)", "RVM fgr (raw RGB)"),
        "side_alpha": side_by_side(ma_p, rv_p, "MatAnyone 2 alpha", "RVM alpha"),
    }
    for stem, img in images.items():
        png_path = OUT / f"_{stem}.png"
        cv2.imwrite(str(png_path), img)
        png_to_webp(png_path, OUT / f"{stem}.webp")

    # cleanup intermediate PNGs
    for p in OUT.glob("_*.png"):
        p.unlink()

    print(f"done. metrics.csv + *.webp written to {OUT}")


if __name__ == "__main__":
    main()
