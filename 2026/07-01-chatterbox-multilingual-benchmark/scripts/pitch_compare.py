"""reference/ref.wav と output/<model>/*.wav の F0 中央値を比較して声質保持を測る。

成人男性の平均 F0: 85-180Hz / 女性: 165-255Hz。
本ベンチの ref は男性 (F0 ~105Hz)、女性 refaudio の再現性は本記事のスコープ外。
"""

import json
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output"
RESULTS = ROOT / "results"


def median_f0(path: Path) -> float | None:
    y, sr = librosa.load(str(path), sr=None)
    f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    voiced = f0[vflag]
    voiced = voiced[~np.isnan(voiced)]
    if voiced.size == 0:
        return None
    return float(np.median(voiced))


def main() -> None:
    ref_f0 = median_f0(REF)
    print(f"[ref.wav] median F0 = {ref_f0:.1f}Hz\n", flush=True)

    all_rows: dict[str, dict[str, dict]] = {}
    for model_dir in sorted(p for p in OUT.iterdir() if p.is_dir()):
        rows: dict[str, dict] = {}
        for lang in PROMPTS:
            f = model_dir / f"{lang}.wav"
            if not f.exists():
                continue
            f0 = median_f0(f)
            if f0 is None:
                print(f"[{model_dir.name}/{lang}] no voiced frames")
                continue
            diff = f0 - ref_f0
            marker = " ★" if abs(diff) <= 10 else " (差 大)" if abs(diff) > 50 else ""
            rows[lang] = {"f0": round(f0, 1), "diff": round(diff, 1)}
            print(f"[{model_dir.name}/{lang}] F0 = {f0:6.1f}Hz  diff {diff:+6.1f}Hz{marker}")
        if rows:
            all_rows[model_dir.name] = rows

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "pitch.json"
    out.write_text(json.dumps({"ref_f0": round(ref_f0, 1), "models": all_rows}, ensure_ascii=False, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
